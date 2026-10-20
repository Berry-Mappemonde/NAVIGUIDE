// Film 2:30 : à l'instant du vol Halifax → Cayenne, l'infobulle d'arrivée
// ne dit plus Halifax pendant que la barre annonce Saint-Pierre-et-Miquelon.
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

const FLIGHT_RE = /flies from Halifax to Cayenne|s'envole de Halifax pour Cayenne/i;

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
  const flightIdx = chapters.findIndex((c) => FLIGHT_RE.test(c?.text || ""));
  expect(flightIdx, "chapitre du vol Halifax → Cayenne").toBeGreaterThanOrEqual(0);
  let arrivalIdx = -1;
  for (let i = 0; i < flightIdx; i += 1) {
    const text = chapters[i]?.text || "";
    if (/halifax/i.test(chapters[i]?.toName || "") && /arriv/i.test(text)) arrivalIdx = i;
  }
  expect(arrivalIdx, "chapitre d'arrivée à Halifax").toBeGreaterThanOrEqual(0);

  const arrivalChars = String(chapters[arrivalIdx].text || "").length;
  await page.evaluate(({ idx, charIdx }) => window.__naviguideFilm.seekChapter(idx, charIdx), {
    idx: arrivalIdx,
    charIdx: Math.max(1, arrivalChars),
  });
  const arrivalCard = page.getByTestId("moment-now");
  await expect(arrivalCard).toBeVisible({ timeout: 8_000 });
  await expect(arrivalCard).toContainText(/Halifax/);

  await page.evaluate((idx) => window.__naviguideFilm.seekChapter(idx, 0), flightIdx);
  const subtitle = page.getByTestId("film-subtitle");
  await expect(subtitle).toContainText(FLIGHT_RE, { timeout: 8_000 });
  await expect(page.getByTestId("film-bar")).not.toContainText("Saint-Pierre-et-Miquelon");
  await expect(arrivalCard).toBeHidden();
  await expect(page.getByTestId("event-bubble")).toBeHidden();
  await shot(page, "01-vol-sans-arrivee-halifax");
});
