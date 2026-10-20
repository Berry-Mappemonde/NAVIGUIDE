// Film 2:30 : quand le panneau indique la destination Saint-Pierre-et-Miquelon,
// l'infobulle d'arrivée ne dit plus Halifax.
// Sans API, Revoir reste grisé ; les assertions du film sont sautées.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema, showLeftPanel } from "../helpers.js";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/sv1");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.webp`),
  type: "webp",
  quality: 85,
  fullPage: false,
});

const SAINT_PIERRE_RE = /saint-pierre/i;

test("film 2:30 : plus d'arrivée Halifax face à Saint-Pierre-et-Miquelon", async ({ page }) => {
  test.setTimeout(90_000);
  await page.addInitScript(() => localStorage.setItem("naviguide_lang_v4", "en"));
  // Les requêtes de point ne portent pas l'assertion : les laisser occuper
  // toutes les connexions empêche le film 2:30 de répondre.
  await page.route(/\/ici\?|\/bi\/|\/grib|\/weather|\/wind|\/wave|\/current/, (route) => route.abort());

  const official = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  const apiUp = Boolean(official && official.ok());
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions du film sautées",
    });
  }

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);
  await page.getByTestId("view-suivre").click();
  await showLeftPanel(page);

  const start = page.getByTestId("replay-start");
  await expect(start).toBeVisible({ timeout: 15_000 });

  if (!apiUp) {
    await expect(start).toBeDisabled();
    await shot(page, "01-revoir-grise");
    return;
  }

  const pill = page.getByTestId("film-duration").locator("[data-seconds='150']");
  await expect(pill).toBeVisible({ timeout: 20_000 });
  if (await pill.getAttribute("aria-pressed") !== "true") {
    await pill.click();
    await expect(pill).toHaveAttribute("aria-pressed", "true", { timeout: 20_000 });
  }
  await expect(start).toBeEnabled({ timeout: 20_000 });

  const listen = page.getByTestId("listen");
  if (await listen.isVisible().catch(() => false)) {
    if (await listen.getAttribute("aria-pressed") === "true") await listen.click();
  }
  await start.click();
  await expect(page.getByTestId("film-subtitle")).toBeVisible({ timeout: 8_000 });

  const chapters = await page.evaluate(() => window.__naviguideFilm?.chapters || []);
  const spmIdx = chapters.findIndex((c) => SAINT_PIERRE_RE.test(c?.toName || ""));
  expect(spmIdx, "chapitre dont la destination est Saint-Pierre-et-Miquelon").toBeGreaterThanOrEqual(0);

  const text = String(chapters[spmIdx].text || "");
  const atHalifax = text.search(/Halifax/i);
  const atArrival = text.search(/Arrival at Saint-Pierre|Arrivée à Saint-Pierre/i);
  const leg = page.getByTestId("ici-leg-line");
  const filmLeg = page.getByTestId("film-leg");
  const arrivalCard = page.getByTestId("moment-now");
  const bubble = page.getByTestId("event-bubble");

  const destinationText = async () => {
    const to = (await filmLeg.getAttribute("data-to")) || "";
    const panel = (await leg.textContent()) || "";
    return `${to}\n${panel}`;
  };

  const points = [...new Set([atArrival, atHalifax].filter((n) => n >= 0))];
  if (!points.length) points.push(Math.max(1, Math.floor(text.length / 2)));
  for (const charIdx of points) {
    await page.evaluate(({ idx, at }) => window.__naviguideFilm.seekChapter(idx, at), {
      idx: spmIdx,
      at: charIdx,
    });
    await expect.poll(destinationText, { timeout: 8_000 }).toMatch(SAINT_PIERRE_RE);
    await expect(arrivalCard).toBeVisible({ timeout: 8_000 });
    await expect(arrivalCard).toContainText(SAINT_PIERRE_RE);
    await expect(arrivalCard).not.toContainText(/Halifax/);
    if (await bubble.isVisible().catch(() => false)) {
      await expect(bubble).not.toContainText(/Halifax/);
    } else {
      await expect(bubble).toBeHidden();
    }
  }

  await shot(page, "01-vol-sans-arrivee-halifax");
});
