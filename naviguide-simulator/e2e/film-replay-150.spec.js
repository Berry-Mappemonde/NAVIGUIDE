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
  let significantTimestampRegressions = 0;
  const positionDeltasKm = [];
  const boundaryPositionDeltasKm = [];
  const modeTransitionJumps = [];
  const unexpectedBoundaryJumps = [];
  const actorVehicleChanges = [];
  const mainBoatAirDriftsKm = [];
  const sideBoatRates = [];
  const phasesSeen = new Set();
  const actorsByName = new Map();
  let previousPosition = null;
  let previousPositionChapter = null;
  let previousVehicle = null;
  let previousPhase = null;

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
      const numberOrNull = (value) => value == null || value === ""
        ? null
        : (Number.isFinite(Number(value)) ? Number(value) : null);
      const subtitle = String(film.subtitle || document.querySelector('[data-testid="film-subtitle"]')?.textContent || "").trim();
      return {
        active: Boolean(document.querySelector('[data-testid="replay-stop"]')),
        elapsed: numberOrNull(film.elapsed),
        chapterIdx: numberOrNull(film.chapterIdx),
        chapterCount: numberOrNull(film.chapterCount),
        charIdx: numberOrNull(film.charIdx),
        tMs: numberOrNull(film.tMs),
        lat: numberOrNull(film.lat),
        lon: numberOrNull(film.lon),
        vehicle: film.vehicle == null ? null : String(film.vehicle),
        phase: film.phase == null ? null : String(film.phase),
        actors: film.actors && typeof film.actors === "object" ? {
          main: film.actors.main || null,
          side: film.actors.side || null,
          plane: film.actors.plane || null,
        } : null,
        filmNm: numberOrNull(film.filmNm),
        subtitle,
        bubbleId: film.bubbleId == null ? null : String(film.bubbleId),
        bubbleKind: film.bubbleKind == null ? null : String(film.bubbleKind),
        fromName: String(film.fromName || ""),
        toName: String(film.toName || ""),
        budgetSeconds: numberOrNull(film.budgetSeconds),
        chapterText: String(film.chapterText || ""),
      };
    });

    if (sample.active) sawActive = true;
    samples.push({ wallElapsed: (Date.now() - wallStart) / 1000, ...sample });
    if (sample.elapsed != null) maxElapsed = Math.max(maxElapsed, sample.elapsed);
    if (sample.chapterIdx != null) distinctChapters.add(sample.chapterIdx);
    if (sample.bubbleId) distinctBubbles.add(sample.bubbleId);
    if (sample.active && sample.tMs != null) {
      if (previousT != null && sample.tMs < previousT - 1) timeRegressions += 1;
      if (previousT != null && sample.tMs < previousT - 1000) significantTimestampRegressions += 1;
      previousT = sample.tMs;
    }
    if (sample.active && sample.phase) phasesSeen.add(sample.phase);
    if (sample.active && sample.vehicle) {
      if (previousVehicle && sample.vehicle !== previousVehicle) {
        const airPhases = new Set(["air-out", "air-return", "air"]);
        const declaredTransition = airPhases.has(previousPhase) || airPhases.has(sample.phase);
        const transition = {
          fromVehicle: previousVehicle,
          toVehicle: sample.vehicle,
          fromPhase: previousPhase,
          toPhase: sample.phase,
          fromChapter: previousPositionChapter,
          toChapter: sample.chapterIdx,
          wallElapsed: Number(((Date.now() - wallStart) / 1000).toFixed(2)),
          declared: declaredTransition,
        };
        actorVehicleChanges.push(transition);
        if (!declaredTransition) unexpectedBoundaryJumps.push({ ...transition, reason: "actor-change-without-declared-air-phase" });
      }
      previousVehicle = sample.vehicle;
      previousPhase = sample.phase;
    }
    if (sample.active && sample.actors && sample.filmNm != null) {
      for (const actorName of ["main", "side", "plane"]) {
        const actor = sample.actors[actorName];
        if (!actor || !actor.visible || actor.lat == null || actor.lon == null) continue;
        const prior = actorsByName.get(actorName);
        const current = { lat: actor.lat, lon: actor.lon, filmNm: sample.filmNm, phase: sample.phase };
        if (prior) {
          const stepKm = distanceKm(prior, current);
          const filmDeltaNm = Math.abs(Number(current.filmNm) - Number(prior.filmNm));
          const expectedKm = filmDeltaNm * 1.852;
          if (actorName === "main" && ["air-out", "side-sail", "air-return"].includes(sample.phase)) {
            mainBoatAirDriftsKm.push(stepKm);
          }
          if (actorName === "side" && sample.phase === "side-sail" && prior.phase === "side-sail") {
            sideBoatRates.push({
              distanceKm: Number(stepKm.toFixed(3)),
              expectedKm: Number(expectedKm.toFixed(3)),
              ratio: expectedKm > 1 ? Number((stepKm / expectedKm).toFixed(3)) : null,
            });
          }
          if (actorName !== "plane" && prior.phase === sample.phase && stepKm > Math.max(25, expectedKm * 2 + 10)) {
            unexpectedBoundaryJumps.push({
              actor: actorName,
              distanceKm: Number(stepKm.toFixed(3)),
              expectedKm: Number(expectedKm.toFixed(3)),
              fromPhase: prior.phase,
              toPhase: current.phase,
              fromFilmNm: prior.filmNm,
              toFilmNm: current.filmNm,
              reason: "boat-displacement-exceeds-film-progress",
            });
          }
        }
        actorsByName.set(actorName, current);
      }
    }
    if (sample.active && sample.lat != null && sample.lon != null) {
      const current = { lat: sample.lat, lon: sample.lon };
      if (previousPosition) {
        const stepKm = distanceKm(previousPosition, current);
        if (sample.chapterIdx === previousPositionChapter) {
          positionDeltasKm.push(stepKm);
        } else {
          boundaryPositionDeltasKm.push(stepKm);
          const previousChapter = rawFilm.chapters[previousPositionChapter] || {};
          const nextChapter = rawFilm.chapters[sample.chapterIdx] || {};
          const isAirLeg = (chapter) => {
            const from = String(chapter.fromName || "").toLowerCase();
            const to = String(chapter.toName || "").toLowerCase();
            return (from.includes("cayenne") && to.includes("halifax"))
              || (from.includes("halifax") && to.includes("cayenne"));
          };
          const transition = {
            distanceKm: Number(stepKm.toFixed(3)),
            fromChapter: previousPositionChapter,
            toChapter: sample.chapterIdx,
            from: String(previousChapter.fromName || ""),
            via: String(previousChapter.toName || ""),
            nextFrom: String(nextChapter.fromName || ""),
            nextTo: String(nextChapter.toName || ""),
          };
          if (stepKm > 1000) {
            if (isAirLeg(previousChapter) || isAirLeg(nextChapter)) {
              modeTransitionJumps.push(transition);
            } else {
              unexpectedBoundaryJumps.push(transition);
            }
          }
        }
      }
      previousPosition = current;
      previousPositionChapter = sample.chapterIdx;
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
    significantTimestampRegressions,
    maxStepDistanceKmWithinChapter: positionDeltasKm.length ? Number(Math.max(...positionDeltasKm).toFixed(3)) : null,
    meanStepDistanceKmWithinChapter: positionDeltasKm.length
      ? Number((positionDeltasKm.reduce((a, b) => a + b, 0) / positionDeltasKm.length).toFixed(3))
      : null,
    maxBoundaryStepDistanceKm: boundaryPositionDeltasKm.length
      ? Number(Math.max(...boundaryPositionDeltasKm).toFixed(3))
      : null,
    modeTransitionJumps,
    unexpectedBoundaryJumps,
    actorVehicleChanges,
    phasesSeen: Array.from(phasesSeen).sort(),
    maxMainBoatDriftDuringAirOrSideKm: mainBoatAirDriftsKm.length ? Number(Math.max(...mainBoatAirDriftsKm).toFixed(3)) : null,
    maxSideBoatRateRatio: sideBoatRates.filter((x) => x.ratio != null).length
      ? Number(Math.max(...sideBoatRates.filter((x) => x.ratio != null).map((x) => x.ratio)).toFixed(3))
      : null,
    sideBoatRateSamples: sideBoatRates,
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
  expect(significantTimestampRegressions, "l'horloge du film ne doit pas reculer de plus d'une seconde").toBe(0);
  expect(
    positionDeltasKm.length ? Math.max(...positionDeltasKm) : Infinity,
    "la position du bateau ne doit pas sauter de plusieurs milliers de kilomètres au sein d'un même chapitre",
  ).toBeLessThan(1000);
  expect(
    unexpectedBoundaryJumps,
    "un bateau ne doit pas se téléporter et tout changement d'acteur doit passer par une phase aérienne déclarée",
  ).toEqual([]);
  expect(
    mainBoatAirDriftsKm.length ? Math.max(...mainBoatAirDriftsKm) : 0,
    "le bateau A reste à quai pendant les vols et la navigation du bateau B",
  ).toBeLessThan(1);
  expect(
    sideBoatRates.filter((x) => x.ratio != null && x.ratio > 2).length,
    "le bateau B ne peut avancer plus de deux fois le progrès maritime du film",
  ).toBe(0);
  expect(pageErrors, "erreurs JavaScript de page: " + pageErrors.join(" | ")).toEqual([]);
});
