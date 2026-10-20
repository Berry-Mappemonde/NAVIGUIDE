// Film 2:30 : loin du port, le pays entre parenthèses n'est plus écrit
// à côté du bateau. Le stock figé ne raconte pas Mata-Utu : on lit
// les départs qu'il joue. Si une phrase nomme Mata-Utu, le bateau
// ne se pose ni là ni sous le label Samoa.
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
// Même seuil que l'écran : au-delà, le pays entre parenthèses n'est plus écrit.
const COUNTRY_NEAR_NM = 80;

function nearMataUtu(lat, lon) {
  if (![lat, lon].every(Number.isFinite)) return false;
  return Math.hypot(lat - (-13.27), lon - (-176.2)) < 1.5;
}

function onSamoaLabel(lat, lon) {
  if (![lat, lon].every(Number.isFinite)) return false;
  return lat >= -16 && lat <= -12 && lon >= -176 && lon <= -166;
}

function readRemainingNm(label) {
  const raw = String(label || "").replace(/[\u202f\u00a0]/g, " ");
  const match = raw.match(/(\d[\d\s]*)\s*nm/i);
  if (!match) return null;
  const n = Number(match[1].replace(/\s/g, ""));
  return Number.isFinite(n) ? n : null;
}

function destinationSide(line) {
  const parts = String(line || "").split("→");
  if (parts.length < 2) return "";
  return parts[parts.length - 1].split("·")[0].trim();
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
  const points = [];
  for (let i = 0; i < chapters.length; i += 1) {
    const text = String(chapters[i]?.text || "");
    const depAt = text.search(DEPARTURE);
    const mataAt = text.search(MATA);
    if (depAt >= 0) points.push({ chapterIdx: i, at: depAt + 4 });
    if (mataAt >= 0) points.push({ chapterIdx: i, at: mataAt });
  }
  expect(points.length, "une phrase de départ du film 2:30").toBeGreaterThan(0);

  const filmLeg = page.getByTestId("film-leg");
  const subtitle = page.getByTestId("film-subtitle");
  const legLine = page.getByTestId("ici-leg-line");
  const bubble = page.getByTestId("event-bubble");
  const port = page.getByTestId("nm-to-destination-port");
  const snap = () => page.evaluate(() => {
    const f = window.__naviguideFilm || {};
    return { lat: f.lat, lon: f.lon, subtitle: f.subtitle || "" };
  });

  let farSeen = 0;
  for (const point of points) {
    const chapter = chapters[point.chapterIdx];
    const text = String(chapter?.text || "");
    await page.evaluate(({ chapterIdx, at }) => {
      window.__naviguideFilm.seekChapter(chapterIdx, at);
    }, point);
    await expect(filmLeg).toBeVisible({ timeout: 8_000 });
    await expect.poll(async () => (await snap()).subtitle, { timeout: 8_000 }).not.toBe("");

    const pos = await snap();
    const legText = await filmLeg.innerText();
    const sub = pos.subtitle || "";
    const dest = destinationSide(legText);
    expect(legText, "pays entre parenthèses à côté du bateau").not.toMatch(WALLIS);
    expect(sub).not.toMatch(WALLIS);
    await expect(legLine).toBeVisible();
    const lineText = await legLine.innerText();
    expect(lineText).not.toMatch(WALLIS);
    if (await bubble.isVisible().catch(() => false)) {
      expect(await bubble.innerText()).not.toMatch(WALLIS);
    } else {
      await expect(bubble).toBeHidden();
    }

    const remaining = readRemainingNm(await port.innerText({ timeout: 8_000 }).catch(() => ""));
    if (dest && remaining != null && remaining > COUNTRY_NEAR_NM) {
      farSeen += 1;
      expect(dest, "pays entre parenthèses à côté du bateau").not.toMatch(/\([^)]+\)/);
      expect(destinationSide(lineText), "pays entre parenthèses dans le panneau").not.toMatch(/\([^)]+\)/);
    }

    const namesMata = MATA.test(chapter?.toName || "") || (DEPARTURE.test(sub) && MATA.test(sub));
    if (namesMata) {
      expect(legText).toMatch(MATA);
      expect(legText).not.toMatch(WALLIS);
    }
    if (DEPARTURE.test(sub) && (namesMata || MATA.test(text))) {
      expect(onSamoaLabel(pos.lat, pos.lon), `bateau ${pos.lat},${pos.lon} sous la phrase de départ`).toBe(false);
      if (MATA.test(chapter?.toName || "") || (DEPARTURE.test(sub) && MATA.test(sub))) {
        expect(nearMataUtu(pos.lat, pos.lon), "la phrase de départ ne pose pas le bateau à Mata-Utu").toBe(false);
      }
    }
  }
  expect(farSeen, "une destination encore loin, sans le pays").toBeGreaterThan(0);

  await shot(page, "01-mata-utu");
});
