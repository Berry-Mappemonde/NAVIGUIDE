import fs from "node:fs/promises";
import { expect, test } from "@playwright/test";
import { dismissNotForNav } from "./helpers.js";

test.use({ video: "on" });
test.describe.configure({ retries: 0 });

test("production film: complete 150-second browser replay with timing and map samples", async ({ page }, testInfo) => {
  test.setTimeout(245_000);

  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(String(error)));

  // Replay the actual production snapshot after the branch's read-time
  // sanitizer has repaired stale dates and text indices. Only GETs are mocked;
  // this test never selects "Rédigé" and never issues a model-generating POST.
  const rawFilmPath = process.env.NAVIGUIDE_FILM_FIXTURE || "/tmp/naviguide-film-fixed.json";
  const clockPath = process.env.NAVIGUIDE_CLOCK_FIXTURE || "/tmp/naviguide-official-clock.json";
  const rawFilm = JSON.parse(await fs.readFile(rawFilmPath, "utf8"));
  const officialClock = JSON.parse(await fs.readFile(clockPath, "utf8"));
  expect(Array.isArray(rawFilm.chapters) && rawFilm.chapters.length > 0, "le snapshot réel réparé doit contenir des chapitres").toBeTruthy();

  const rawResponse = page.waitForResponse((response) => {
    try {
      const url = new URL(response.url());
      return response.request().method() === "GET"
        && url.pathname.endsWith("/voyage/official/film")
        && url.searchParams.get("style") === "raw"
        && url.searchParams.get("lang") === "fr";
    } catch {
      return false;
    }
  }, { timeout: 45_000 });

  await page.route("**/voyage/official/film**", async (route) => {
    const url = new URL(route.request().url());
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...rawFilm,
        status: "ready",
        hasWritten: false,
        style: url.searchParams.get("style") || "raw",
      }),
    });
  });
  await page.route("**/voyage/official/clock**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(officialClock),
    });
  });

  await page.addInitScript(() => {
    try { localStorage.setItem("naviguide_lang_v4", "fr"); } catch {}
  });

  const target = process.env.NAVIGUIDE_REPLAY_URL || "http://127.0.0.1:5174";
  const navigation = await page.goto(target, { waitUntil: "domcontentloaded", timeout: 35_000 });
  expect(navigation, "le build de branche doit répondre").toBeTruthy();
  expect(navigation.status(), "HTTP du simulateur local").toBeLessThan(400);

  const filmResponse = await rawResponse;
  expect(filmResponse.ok(), "GET local du snapshot brut réparé").toBeTruthy();
  const replayFilm = await filmResponse.json();
  expect(replayFilm.chapters.length).toBe(rawFilm.chapters.length);
  const rawPath = testInfo.outputPath("film-raw-production-repaired.json");
  await fs.writeFile(rawPath, JSON.stringify(replayFilm, null, 2), "utf8");
  await testInfo.attach("film-raw-production-repaired", { path: rawPath, contentType: "application/json" });

  await dismissNotForNav(page, { timeout: 1_500 });
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  const duration150 = page.locator('[data-seconds="150"]');
  await expect(duration150).toBeVisible({ timeout: 30_000 });
  if (await duration150.getAttribute("aria-pressed") !== "true") {
    await duration150.click();
  }

  const start = page.getByTestId("replay-start");
  await expect(start).toBeEnabled({ timeout: 45_000 });
  await page.screenshot({ path: testInfo.outputPath("film-start.png"), fullPage: false });
  await start.click();
  await expect(page.getByTestId("replay-stop")).toBeVisible({ timeout: 15_000 });

  const wallStart = Date.now();
  const samples = [];
  let sawActive = false;
  let completed = false;
  let tookMiddleScreenshot = false;
  let maxElapsed = 0;
  const distinctChapters = new Set();
  const distinctBubbles = new Set();
  let previousT = null;
  let timeRegressions = 0;
  const positionDeltasKm = [];
  let previousPosition = null;

  const distanceKm = (a, b) => {
    const rad = (deg) => deg * Math.PI / 180;
    const dLat = rad(b.lat - a.lat);
    const dLon = rad(b.lon - a.lon);
    const lat1 = rad(a.lat);
    const lat2 = rad(b.lat);
    const h = Math.sin(dLat / 2) ** 2
      + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
    return 6371 * 2 * Math.asin(Math.min(1, Math.sqrt(h)));
  };

  while (Date.now() - wallStart < 205_000) {
    const sample = await page.evaluate(() => {
      const film = window.__naviguideFilm || {};
      const subtitle = String(film.subtitle || document.querySelector('[data-testid="film-subtitle"]')?.textContent || "").trim();
      return {
        active: Boolean(document.querySelector('[data-testid="replay-stop"]')),
        elapsed: Number.isFinite(Number(film.elapsed)) ? Number(film.elapsed) : null,
        chapterIdx: Number.isFinite(Number(film.chapterIdx)) ? Number(film.chapterIdx) : null,
        chapterCount: Number.isFinite(Number(film.chapterCount)) ? Number(film.chapterCount) : null,
        charIdx: Number.isFinite(Number(film.charIdx)) ? Number(film.charIdx) : null,
        tMs: Number.isFinite(Number(film.tMs)) ? Number(film.tMs) : null,
        lat: Number.isFinite(Number(film.lat)) ? Number(film.lat) : null,
        lon: Number.isFinite(Number(film.lon)) ? Number(film.lon) : null,
        subtitle,
        bubbleId: film.bubbleId == null ? null : String(film.bubbleId),
        bubbleKind: film.bubbleKind == null ? null : String(film.bubbleKind),
        fromName: String(film.fromName || ""),
        toName: String(film.toName || ""),
        budgetSeconds: Number.isFinite(Number(film.budgetSeconds)) ? Number(film.budgetSeconds) : null,
        chapterText: String(film.chapterText || ""),
      };
    });

    if (sample.active) sawActive = true;
    samples.push({ wallElapsed: (Date.now() - wallStart) / 1000, ...sample });
    if (sample.elapsed != null) maxElapsed = Math.max(maxElapsed, sample.elapsed);
    if (sample.chapterIdx != null) distinctChapters.add(sample.chapterIdx);
    if (sample.bubbleId) distinctBubbles.add(sample.bubbleId);
    if (sample.tMs != null) {
      if (previousT != null && sample.tMs < previousT - 1) timeRegressions += 1;
      previousT = sample.tMs;
    }
    if (sample.lat != null && sample.lon != null) {
      const current = { lat: sample.lat, lon: sample.lon };
      if (previousPosition) positionDeltasKm.push(distanceKm(previousPosition, current));
      previousPosition = current;
    }

    if (!tookMiddleScreenshot && maxElapsed >= 75) {
      await page.screenshot({ path: testInfo.outputPath("film-midpoint.png"), fullPage: false });
      tookMiddleScreenshot = true;
    }

    if (sawActive && !sample.active && samples.length > 2) {
      completed = true;
      break;
    }
    await page.waitForTimeout(1_000);
  }

  await page.screenshot({ path: testInfo.outputPath("film-end.png"), fullPage: false });
  const wallSeconds = (Date.now() - wallStart) / 1000;
  const validPositions = samples.filter((s) => s.lat != null && s.lon != null).length;
  const subtitleSamples = samples.filter((s) => s.subtitle).length;
  const metrics = {
    url: target,
    capturedAt: new Date().toISOString(),
    rawSource: rawFilm.source ?? null,
    rawHasWritten: rawFilm.hasWritten ?? false,
    rawChapterCount: rawFilm.chapters.length,
    rawChars: rawFilm.chars ?? rawFilm.chapters.reduce((n, c) => n + String(c.text || "").length, 0),
    requestedSeconds: 150,
    elapsedWallSeconds: Number(wallSeconds.toFixed(2)),
    reportedFilmElapsedSeconds: Number(maxElapsed.toFixed(2)),
    completed,
    sampleCount: samples.length,
    chapterCountVisited: distinctChapters.size,
    distinctBubbleIds: distinctBubbles.size,
    validPositionSamples: validPositions,
    positionCoverage: Number((validPositions / Math.max(1, samples.length)).toFixed(3)),
    subtitleCoverage: Number((subtitleSamples / Math.max(1, samples.length)).toFixed(3)),
    timestampRegressions: timeRegressions,
    maxStepDistanceKm: positionDeltasKm.length ? Number(Math.max(...positionDeltasKm).toFixed(3)) : null,
    meanStepDistanceKm: positionDeltasKm.length
      ? Number((positionDeltasKm.reduce((a, b) => a + b, 0) / positionDeltasKm.length).toFixed(3))
      : null,
    pageErrors,
    samples,
  };
  const metricsPath = testInfo.outputPath("film-replay-150-metrics.json");
  await fs.writeFile(metricsPath, JSON.stringify(metrics, null, 2), "utf8");
  await testInfo.attach("film-replay-150-metrics", { path: metricsPath, contentType: "application/json" });

  expect(sawActive, "le rejeu doit réellement démarrer").toBeTruthy();
  expect(completed, "le film doit se terminer sans intervention avant 205 s").toBeTruthy();
  expect(wallSeconds, "le rejeu doit couvrir environ 2 min 30 s").toBeGreaterThanOrEqual(145);
  expect(maxElapsed, "le temps du film doit atteindre 145 s").toBeGreaterThanOrEqual(145);
  expect(distinctChapters.size, "la lecture doit traverser plusieurs chapitres").toBeGreaterThanOrEqual(5);
  expect(validPositions, "la carte doit produire des positions pendant le film").toBeGreaterThan(50);
  expect(subtitleSamples, "le récit doit apparaître pendant le film").toBeGreaterThan(50);
  expect(timeRegressions, "l'horloge du film ne doit pas reculer").toBe(0);
  expect(pageErrors, "erreurs JavaScript de page: " + pageErrors.join(" | ")).toEqual([]);
});
