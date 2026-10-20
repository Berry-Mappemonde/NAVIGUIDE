// Film 2:30 : loin de Mata-Utu, le pays entre parenthèses n'est plus écrit
// à côté du bateau, et la phrase de départ ne le pose pas sur un autre pays.
// Sans API : GET /voyage/official sondé ; s'il ne répond pas, annotation
// et retour — Revoir grisé et la barre restent exigés.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema, showLeftPanel } from "../helpers.js";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/sv2");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.webp`),
  type: "webp",
  quality: 85,
  fullPage: false,
});

const WALLIS = /Wallis/;
const MATA = /Mata-Utu/i;
const DEPARTURE = /départ vers|departure for/i;

function nearMataUtu(lat, lon) {
  if (![lat, lon].every(Number.isFinite)) return false;
  return Math.hypot(lat - (-13.27), lon - (-176.2)) < 1.5;
}

function onSamoaLabel(lat, lon) {
  if (![lat, lon].every(Number.isFinite)) return false;
  return lat >= -16 && lat <= -12 && lon >= -176 && lon <= -166;
}

test("film 2:30 : Mata-Utu sans le pays tant que le bateau n'y est pas", async ({ page }) => {
  test.setTimeout(90_000);
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
    await shot(page, "01-mata-utu");
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
  const destIdx = chapters.findIndex((c) => MATA.test(c?.toName || ""));
  const saidIdx = chapters.findIndex((c) => MATA.test(c?.text || ""));
  const idx = destIdx >= 0 ? destIdx : saidIdx;
  expect(idx, "chapitre qui nomme Mata-Utu").toBeGreaterThanOrEqual(0);

  const chapter = chapters[idx];
  const text = String(chapter.text || "");
  const depAt = text.search(DEPARTURE);
  const mataAt = text.search(MATA);
  const points = [...new Set([depAt >= 0 ? depAt + 4 : -1, mataAt].filter((n) => n >= 0))];
  expect(points.length, "un endroit du chapitre où Mata-Utu ou le départ est écrit").toBeGreaterThan(0);

  const filmLeg = page.getByTestId("film-leg");
  const subtitle = page.getByTestId("film-subtitle");
  const legLine = page.getByTestId("ici-leg-line");
  const bubble = page.getByTestId("event-bubble");
  const snap = () => page.evaluate(() => {
    const f = window.__naviguideFilm || {};
    return { lat: f.lat, lon: f.lon, subtitle: f.subtitle || "" };
  });

  for (const charIdx of points) {
    await page.evaluate(({ chapterIdx, at }) => {
      window.__naviguideFilm.seekChapter(chapterIdx, at);
    }, { chapterIdx: idx, at: charIdx });
    await expect(filmLeg).toBeVisible({ timeout: 8_000 });
    await expect.poll(async () => (await snap()).subtitle, { timeout: 8_000 }).not.toBe("");

    const pos = await snap();
    const legText = await filmLeg.innerText();
    const sub = pos.subtitle || "";
    expect(legText, "pays entre parenthèses à côté du bateau").not.toMatch(WALLIS);
    expect(sub).not.toMatch(WALLIS);
    await expect(legLine).toBeVisible();
    expect(await legLine.innerText()).not.toMatch(WALLIS);
    if (await bubble.isVisible().catch(() => false)) {
      expect(await bubble.innerText()).not.toMatch(WALLIS);
    } else {
      await expect(bubble).toBeHidden();
    }

    const namesMata = MATA.test(chapter.toName || "") || (DEPARTURE.test(sub) && MATA.test(sub));
    if (namesMata) {
      expect(legText).toMatch(MATA);
      expect(legText).not.toMatch(WALLIS);
    }
    if (DEPARTURE.test(sub) && (namesMata || MATA.test(text))) {
      expect(onSamoaLabel(pos.lat, pos.lon), `bateau ${pos.lat},${pos.lon} sous la phrase de départ`).toBe(false);
      if (MATA.test(chapter.toName || "") || (DEPARTURE.test(sub) && MATA.test(sub))) {
        expect(nearMataUtu(pos.lat, pos.lon), "la phrase de départ ne pose pas le bateau à Mata-Utu").toBe(false);
      }
    }
  }

  await shot(page, "01-mata-utu");
});
