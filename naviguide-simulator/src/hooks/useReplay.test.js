import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { advanceReplayTime, filmPlan, positionAt } from "../engine/replay.js";
import { applyReplayStop, approachStopEvent, canStartOfficialReplay, closingSubtitle, FILM_ESTIMATE_CPS, FILM_VISIBILITY_CATCHUP_MS, FILM_VOICE_STALL_MS, filmBarSubtitle, filmEstimatedSeconds, filmHasRg6Rg7Fingerprint, filmQueryKeepsReady, filmSpeakSeconds, filmSubtitleAt, filmSubtitleHighlight, filmSubtitleShowsAir, filmTextHasT0Year, followClockLineFromT0, followEtaFromClock, formatFilmEstimateClock, isRe7OfficialFilm, linearFilmAt, officialFilmStatus, pickFilmChapters, pickFilmEstimateSeconds, resolveFilmTargetSeconds, shouldHoldFilmForBudget, shouldReturnToLive, splitFilmSentences, stepAlongPlan, toggleFilmDuration, visibilityCatchupStep, visibleFilmSubtitle, voiceLeadPolicy, wallClockSpeakSeconds } from "./useReplay.js";
import { DEFAULT_T0_ISO, simulationT0Iso } from "../engine/voyageClock.js";

const here = dirname(fileURLToPath(import.meta.url));
const hook = readFileSync(join(here, "useReplay.js"), "utf8");
const app = readFileSync(join(here, "..", "App.jsx"), "utf8");
const bar = readFileSync(join(here, "..", "components", "SimulationFilmBar.jsx"), "utf8");

describe("useReplay contract (lot E)", () => {
  it("replays on the official clock, consumes the film plan, and hands back to live at the end or on Stop", () => {
    assert.match(hook, /replayWindow\(clockToUse, Date\.now\(\)\)/);
    assert.match(hook, /requestAnimationFrame\(tick\)/);
    assert.match(hook, /if \(done\)/);
    assert.match(hook, /const stop = useCallback/);
    assert.match(hook, /\/voyage\/official\/film/);
    assert.match(hook, /t0=\$\{encodeURIComponent\(t0\)\}/);
    assert.match(hook, /t0 = DEFAULT_T0_ISO/);
    assert.match(hook, /buildFilmScript/);
    assert.match(hook, /FILM_UI_MS/);
    assert.match(hook, /if \(uiDue\) setTMs\(next\)/);
    assert.doesNotMatch(hook, /Tavily|Nebius/i);
  });

  it("App swaps the live boat for the replayed one in Suivre, jumps the playhead each frame, reads each new leg aloud", () => {
    assert.match(app, /replay\.active && replay\.live \? replay\.live : official\.live/);
    assert.match(app, /jump: Boolean\(live\.replay\)/);
    // The voice lives in hooks/useReplayVoice.js since lot J; App mounts it.
    assert.match(app, /useReplayVoice\(\{/);
    assert.match(app, /chapterText: replay\.chapterText/);
    assert.match(readFileSync(join(here, "useReplayVoice.js"), "utf8"), /speakSentence|speak\(/);
    assert.match(readFileSync(join(here, "useReplayVoice.js"), "utf8"), /isVoiceHeld/);
    assert.match(app, /onSentenceEnd: replay\.onSentenceEnd/);
    assert.match(app, /momentNow=\{replay\.active \? replay\.card/);
    assert.match(app, /storyReplay=\{replay\.active\}/);
  });

  it("the film bar offers Revoir / Stop ; voice follows Écouter (no 🔊)", () => {
    assert.match(bar, /data-testid="replay-start"/);
    assert.match(bar, /data-testid="replay-stop"/);
    assert.doesNotMatch(bar, /data-testid="replay-voice"/);
    assert.match(bar, /testId="listen"/);
    assert.match(bar, /onListening=\{replay\?\.onVoice\}/);
    assert.match(bar, /deferSpeak=\{Boolean\(replay\?\.active\)\}/);
    assert.match(hook, /voice is piloted by the film-bar/);
  });

  it("App feeds the current paragraph to speech while a replay is active", () => {
    assert.match(app, /const speechText = replay\.active/);
    assert.match(app, /replay\.chapterText/);
  });

  it("le film est chapitré : filmPlan, onboundary, durée cible, sous-titre", () => {
    assert.match(hook, /filmPlan\(/);
    assert.match(hook, /onVoiceBoundary/);
    // 27 sept. / RG12 : le pas de temps mené par la voix passe par stepFilmTime
    // (prédiction, gouverneur) ; la voix n'est plus recalibrée (débit constant).
    assert.match(hook, /stepFilmTime\(/);
    assert.match(hook, /voiceHoldRef/);
    assert.doesNotMatch(hook, /calibrateRate/);
    assert.match(hook, /targetSeconds/);
    assert.match(hook, /if \(done\)/);
    assert.match(bar, /data-testid="film-subtitle"/);
    assert.match(bar, /data-testid="film-duration"/);
    assert.match(hook, /useState\(0\)/);
    assert.match(bar, /=== sec \? 0 : sec/);
  });

  it("lot RD7 — durées décochables, budget tenu, temps naturel sans case", () => {
    assert.equal(toggleFilmDuration(0, 150), 150);
    assert.equal(toggleFilmDuration(150, 150), 0);
    assert.equal(toggleFilmDuration(150, 180), 180);
    assert.equal(toggleFilmDuration(180, 180), 0);
    const chapters = [{ text: "x".repeat(320) }];
    assert.equal(resolveFilmTargetSeconds(150, chapters), 150);
    assert.equal(resolveFilmTargetSeconds(0, chapters), filmSpeakSeconds(chapters));
    assert.equal(shouldHoldFilmForBudget({ userBudget: 150, wallElapsed: 121, lastChapter: true }), true);
    assert.equal(shouldHoldFilmForBudget({ userBudget: 150, wallElapsed: 150, lastChapter: true }), false);
    assert.equal(shouldHoldFilmForBudget({ userBudget: 0, wallElapsed: 80, lastChapter: true }), false);
    assert.match(hook, /shouldHoldFilmForBudget/);
    assert.match(hook, /budgetSeconds/);
    assert.match(hook, /resolveFilmTargetSeconds/);
    assert.match(hook, /userBudget > 0 \? userBudget : FILM_TARGET_SECONDS/);
  });

  it("lot RG8 — durée estimée = caractères ÷ 15, sans recalibrer la voix", () => {
    assert.equal(filmEstimatedSeconds(2250), 150);
    assert.equal(filmEstimatedSeconds(2700), 180);
    assert.equal(filmEstimatedSeconds(0), 0);
    assert.equal(formatFilmEstimateClock(160), "2:40");
    assert.equal(formatFilmEstimateClock(0), "");
    assert.equal(pickFilmEstimateSeconds(150, { 150: { estimatedSeconds: 160 } }, 0), 160);
    assert.equal(pickFilmEstimateSeconds(0, { 0: { estimatedSeconds: 240 } }, 99), 240);
    assert.equal(pickFilmEstimateSeconds(180, null, 195), 195);
    const q0 = "lang=fr&seconds=0&style=raw&t0=2026-05-15T08%3A00%3A00.000Z";
    const q150 = "lang=fr&seconds=150&style=raw&t0=2026-05-15T08%3A00%3A00.000Z";
    assert.equal(filmQueryKeepsReady(q0, q150), true);
    assert.equal(filmQueryKeepsReady(q150, "lang=en&seconds=150&style=raw&t0=2026-05-15T08%3A00%3A00.000Z"), false);
    assert.match(hook, /filmQueryKeepsReady/);
    assert.doesNotMatch(hook, /calibrateRate/);
    assert.match(hook, /estimatedSeconds/);
    assert.match(app, /estimatedSeconds: replay\.estimatedSeconds/);
  });

  it("lot F4 : les événements du chapitre ouvrent la bulle (même texte que la carte NOW)", () => {
    assert.match(hook, /pickFilmEvent/);
    assert.match(hook, /publishEventBubble/);
    assert.match(hook, /filmBubbleRef/);
    assert.match(hook, /FilmEventScoreGate/);
    assert.match(hook, /filmEventCard/);
    assert.match(app, /momentNow=\{replay\.active \? replay\.card/);
  });
});

describe("useReplay lot R3 — onend immédiat sans boundary", () => {
  const t0 = Date.parse("2026-05-15T08:00:00Z");
  const chapters = [
    { tA: t0, tB: t0 + 86400000, text: "A".repeat(80), fromLat: 48.8, fromLon: 2.4, toLat: 46.1, toLon: -1.1 },
    { tA: t0 + 86400000, tB: t0 + 2 * 86400000, text: "B".repeat(80), fromLat: 46.1, fromLon: -1.1, toLat: 41.9, toLon: 8.7 },
    { tA: t0 + 2 * 86400000, tB: t0 + 3 * 86400000, text: "C".repeat(80), fromLat: 41.9, fromLon: 8.7, toLat: 14.6, toLon: -61.0 },
    { tA: t0 + 3 * 86400000, tB: t0 + 4 * 86400000, text: "D".repeat(80), fromLat: 14.6, fromLon: -61.0, toLat: 4.9, toLon: -52.3 },
  ];

  it("relance une fois, puis linéaire : film non terminé, dernier chapitre à la durée cible", () => {
    const retry = voiceLeadPolicy({
      hadBoundary: false, elapsedMs: 80, alreadyRetried: false, chapterIdx: 0, chapterCount: 4,
    });
    assert.equal(retry.mode, "retry");
    assert.equal(retry.finish, false);
    assert.equal(retry.chapterIdx, 0);

    const linear = voiceLeadPolicy({
      hadBoundary: false, elapsedMs: 80, alreadyRetried: true, chapterIdx: 0, chapterCount: 4,
    });
    assert.equal(linear.mode, "linear");
    assert.equal(linear.finish, false, "le film ne se termine pas sur l'échec voix");
    assert.equal(linear.chapterIdx, 0);

    const plan = filmPlan({ chapters, targetSeconds: 150 });
    const mid = linearFilmAt(5, plan);
    assert.equal(mid.finish, false);
    assert.equal(mid.lastReached, false);

    const end = linearFilmAt(150, plan);
    assert.equal(end.finish, true);
    assert.equal(end.lastReached, true);
    assert.equal(end.chapterIdx, plan.chapters.length - 1);

    assert.match(hook, /voiceFailedRef/);
    assert.match(hook, /waitForVoices/);
    assert.match(hook, /onVoiceLeadFailed/);
    assert.match(hook, /pickFilmChapters/);
    assert.match(hook, /AbortError/);
    assert.doesNotMatch(hook, /targetSeconds \+ 20/);

    const lastOk = voiceLeadPolicy({
      hadBoundary: true, elapsedMs: 800, alreadyRetried: false, chapterIdx: 3, chapterCount: 4,
    });
    assert.equal(lastOk.mode, "advance");
    assert.equal(lastOk.finish, true);

    const lastIncident = voiceLeadPolicy({
      hadBoundary: false, elapsedMs: 80, alreadyRetried: true, chapterIdx: 3, chapterCount: 4,
    });
    assert.equal(lastIncident.mode, "linear");
    assert.equal(lastIncident.finish, false, "un incident de voix ne met pas finish");

    const midCut = voiceLeadPolicy({
      hadBoundary: false, elapsedMs: 80, alreadyRetried: false,
      chapterIdx: 3, chapterCount: 4, hasMoreChunks: true,
    });
    assert.equal(midCut.mode, "advance");
    assert.equal(midCut.finish, false);

    assert.equal(shouldReturnToLive({ voiceIncident: true }), false);
    assert.equal(shouldReturnToLive({ filmFinished: true }), true);
    assert.equal(shouldReturnToLive({ userStopped: true }), true);
    assert.equal(shouldReturnToLive({ voiceIncident: true, filmFinished: true }), true);
  });

  it("script API sans emprise : texte serveur + coords locales (id / from+to)", () => {
    const remote = {
      chapters: [{
        id: "leg-0",
        text: "Arrivée à La Rochelle",
        fromName: "Saint-Maur",
        toName: "La Rochelle",
        fromLat: null,
        fromLon: null,
        toLat: null,
        toLon: null,
      }],
      source: "rules",
    };
    const local = {
      chapters: [{
        id: "leg-0",
        text: "quitté Saint-Maur vers La Rochelle. Aujourd'hui, le bateau est à 19 260 milles nautiques du départ",
        fromName: "Saint-Maur",
        toName: "La Rochelle",
        fromLat: 48.8,
        fromLon: 2.4,
        toLat: 46.1,
        toLon: -1.1,
      }],
      source: "rules",
    };
    const picked = pickFilmChapters(remote, local, []);
    assert.equal(picked.remote, true);
    assert.match(picked.chapters[0].text, /Arrivée à La Rochelle/);
    assert.doesNotMatch(picked.chapters[0].text, /Aujourd'hui, le bateau est à/);
    assert.equal(picked.chapters[0].fromLat, 48.8);
    assert.equal(picked.chapters[0].toLat, 46.1);
    assert.ok(chapterHasFirstLeg(picked.chapters[0]));
  });

  it("lot RD5 : un script distant qui ignore t0 n'est pas retenu", () => {
    const ch2026 = [{ text: "L’expédition a quitté Saint-Maur le 15 mai 2026." }];
    assert.equal(filmTextHasT0Year(ch2026, "2026-05-15T08:00:00.000Z"), true);
    assert.equal(filmTextHasT0Year(ch2026, "2025-05-15T08:00:00.000Z"), false);
    assert.match(hook, /filmTextHasT0Year\(remoteToUse\.chapters, t0\)/);
  });
});

describe("lot RE4 — ligne d'état pilotée par le t0 de la barre", () => {
  const sample = {
    sailNm: 14220,
    seaHours: 112 * 24,
    iso: "2026-09-26T09:14:00.000Z",
  };
  const t0_2025 = "2025-05-15T08:00:00.000Z";

  it("changer le t0 change l'année et garde le jour de voyage dérivé des heures de mer", () => {
    const live = followClockLineFromT0({ ...sample, t0: DEFAULT_T0_ISO, lang: "fr" });
    const shifted = followClockLineFromT0({ ...sample, t0: t0_2025, lang: "fr" });
    assert.match(live, /2026/);
    assert.match(live, /j112/);
    assert.match(shifted, /2025/);
    assert.match(shifted, /j112/);
    assert.notEqual(live, shifted);
    assert.match(shifted, /26 sept\. 2025 · 09:14 UTC/);
  });

  it("remettre le t0 par défaut restaure la ligne d'origine", () => {
    const live = followClockLineFromT0({ ...sample, t0: DEFAULT_T0_ISO, lang: "fr" });
    const shifted = followClockLineFromT0({ ...sample, t0: t0_2025, lang: "fr" });
    const restored = followClockLineFromT0({ ...sample, t0: DEFAULT_T0_ISO, lang: "fr" });
    assert.notEqual(shifted, live);
    assert.equal(restored, live);
  });

  it("restants et ETA viennent des durées de jambes, pas du t0 Simulation", () => {
    const clock = {
      t0: DEFAULT_T0_ISO,
      vertices: [
        { filmNm: 0, tHours: 0, iso: DEFAULT_T0_ISO, seaHours: 0, sailNm: 0 },
        { filmNm: 83, tHours: 10, iso: "2026-05-15T18:00:00.000Z", seaHours: 10, sailNm: 83 },
      ],
    };
    const eta = followEtaFromClock(clock, 0, 83);
    const shiftedClock = { ...clock, t0: t0_2025 };
    assert.equal(followEtaFromClock(shiftedClock, 0, 83), eta);
    assert.equal(eta, 10);
    const simT0 = simulationT0Iso(new Date("2026-09-26T12:00:00.000Z"));
    assert.notEqual(simT0, DEFAULT_T0_ISO);
    assert.notEqual(simT0, t0_2025);
  });

  it("App décale la ligne dès le champ date, sans toucher au t0 Simulation", () => {
    assert.match(app, /followClockLineFromT0/);
    assert.match(app, /t0: isSuivre \? replayT0/);
    assert.doesNotMatch(app, /iso: isSuivre && replay\.active/);
    assert.match(app, /onDepartureT0=\{voyage\.setT0\}/);
    assert.match(app, /onT0: setReplayT0/);
    assert.doesNotMatch(app, /voyage\.setT0\(replayT0\)/);
    assert.doesNotMatch(app, /voyage\.setT0\(DEFAULT_T0_ISO\)/);
  });
});

function chapterHasFirstLeg(ch) {
  return Number.isFinite(ch.fromLat) && Number.isFinite(ch.toLat);
}

describe("lot RC10 — film officiel, pas la Simulation", () => {
  it("empreinte RE7 : pas Bay of Biscay, pas milles nautiques du départ ; court sans jargon ready", () => {
    assert.equal(isRe7OfficialFilm({
      chapters: [{ text: "Départ de Saint-Maur. golfe de Gascogne. Aujourd’hui, le bateau est à Nouméa." }],
    }), true);
    assert.equal(isRe7OfficialFilm({ chapters: [{ text: "Bay of Biscay ".repeat(10) }] }), false);
    assert.equal(isRe7OfficialFilm({
      chapters: [{ text: "Aujourd'hui, le bateau est à 19 260 milles nautiques du départ." }],
    }), false);
    assert.equal(isRe7OfficialFilm({ chapters: [{ text: `${"mot ".repeat(801)}` }] }), false);
    assert.equal(isRe7OfficialFilm({ chapters: [{ text: `${"mot ".repeat(2501)}` }] }), false);
    assert.equal(isRe7OfficialFilm({ chapters: [] }), false);
  });

  it("lot RC21 — 801 mots : gabarit RG6 ready, Bay of Biscay stale, remplissage stale", () => {
    const pad = (prefix) => `${prefix} ${"mot ".repeat(801)}`;
    const rg6 = pad("Le 15 mai, Berry-Mappemonde quitte La Rochelle pour Ajaccio. 432 milles, 9 jours de mer.");
    assert.equal(filmHasRg6Rg7Fingerprint(rg6), true);
    assert.equal(isRe7OfficialFilm({ chapters: [{ text: rg6 }] }), true);
    assert.equal(officialFilmStatus({ chapters: [{ text: rg6 }] }), "ready");
    const biscay = pad("Bay of Biscay");
    assert.equal(isRe7OfficialFilm({ chapters: [{ text: biscay }] }), false);
    assert.equal(officialFilmStatus({ chapters: [{ text: biscay }] }), "stale");
    const filler = `${"mot ".repeat(801)}`;
    assert.equal(filmHasRg6Rg7Fingerprint(filler), false);
    assert.equal(isRe7OfficialFilm({ chapters: [{ text: filler }] }), false);
    assert.equal(officialFilmStatus({ chapters: [{ text: filler }] }), "stale");
    assert.equal(isRe7OfficialFilm({
      chapters: [{ text: "Départ de Saint-Maur. golfe de Gascogne. Cap au sud-ouest." }],
    }), true);
  });

  it("officialFilmStatus : absent si fetch échoue, stale si empreinte manquante", () => {
    assert.equal(officialFilmStatus(null, { fetchFailed: true }), "absent");
    assert.equal(officialFilmStatus(null), "pending");
    assert.equal(officialFilmStatus({
      chapters: [{ text: "Saint-Maur golfe de Gascogne Gibraltar. Aujourd’hui, le bateau est à Nouméa." }],
    }), "ready");
    assert.equal(officialFilmStatus({
      chapters: [{ text: "Bay of Biscay and milles nautiques du départ" }],
    }), "stale");
  });

  it("Revoir attend l'horloge officielle + /film RE7 ; absent + requireOfficialFilm → false", () => {
    assert.equal(canStartOfficialReplay({ officialClock: { t0: "x" }, remoteStatus: "ready" }), true);
    assert.equal(canStartOfficialReplay({ officialClock: null, remoteStatus: "ready" }), false);
    assert.equal(canStartOfficialReplay({
      requireOfficialFilm: true,
      officialClock: { t0: "x" },
      fallbackClock: { t0: "y" },
      remoteStatus: "absent",
    }), false);
    assert.equal(canStartOfficialReplay({
      officialClock: null, fallbackClock: { t0: "y" }, remoteStatus: "absent",
    }), false);
    assert.equal(canStartOfficialReplay({ officialClock: { t0: "x" }, remoteStatus: "pending" }), false);
    assert.equal(canStartOfficialReplay({ officialClock: { t0: "x" }, remoteStatus: "stale" }), false);
    assert.equal(canStartOfficialReplay({
      requireOfficialFilm: false, fallbackClock: { t0: "y" }, remoteStatus: "absent",
    }), true);
  });

  it("App : replayControls dès officialClock, canStart passé à la barre", () => {
    assert.match(app, /const filmClock = isSuivre \? official\.clock : voyage\.clock/);
    assert.match(app, /clock: filmClock/);
    assert.match(app, /fallbackClock: voyage\.clock/);
    assert.match(app, /requireOfficialFilm: isSuivre/);
    assert.match(app, /isSuivre && officialClock \?/);
    assert.doesNotMatch(app, /officialClock && replay\.canStart/);
    assert.match(app, /canStart: replay\.canStart/);
    assert.match(hook, /keepReady/);
    assert.match(hook, /remoteStatusRef\.current === "ready"/);
    assert.match(hook, /isRe7OfficialFilm/);
    assert.match(hook, /seekChapter/);
    assert.match(hook, /pinnedIdxRef/);
    const replayCall = app.slice(app.indexOf("const replay = useReplay"), app.indexOf("const live = isSuivre"));
    assert.match(replayCall, /clock: filmClock/);
    assert.doesNotMatch(replayCall, /clock: officialClock/);
    const startFn = hook.slice(hook.indexOf("const start = useCallback"), hook.indexOf("const onVoiceBoundary"));
    assert.match(startFn, /status === "ready" && isRe7OfficialFilm/);
    assert.doesNotMatch(startFn, /fallbackClock \|\| clock/);
    assert.doesNotMatch(startFn, /status === "absent"/);
  });
});

describe("useReplay lot R4 — temps continu entre deux boundaries", () => {
  it("60 frames entre deux boundaries : 60 positions croissantes, pas < 1/30 de la jambe", () => {
    const t0 = Date.parse("2026-05-15T08:00:00Z");
    const clock = {
      t0: "2026-05-15T08:00:00.000Z",
      vertices: [
        { tHours: 0, filmNm: 0, sailNm: 0, lat: 46.8, lon: 1.7, bearing: 260 },
        { tHours: 4, filmNm: 122, sailNm: 122, lat: 46.15, lon: -1.16, bearing: 260 },
      ],
    };
    const plan = filmPlan({
      chapters: [{
        tA: t0,
        tB: t0 + 4 * 3600000,
        text: "x".repeat(200),
        fromLat: 46.8,
        fromLon: 1.7,
        toLat: 46.15,
        toLon: -1.16,
      }],
      targetSeconds: 150,
    });
    const ch = plan.chapters[0];
    const startPos = positionAt(clock, ch.tA);
    const endPos = positionAt(clock, ch.tB);
    const jambe = Math.hypot(endPos.lat - startPos.lat, endPos.lon - startPos.lon);
    const progress = (p) => {
      const ux = endPos.lon - startPos.lon;
      const uy = endPos.lat - startPos.lat;
      return ((p.lon - startPos.lon) * ux + (p.lat - startPos.lat) * uy) / (jambe * jambe);
    };

    let t = plan.timeAt(0, 10);
    let recale = 0;
    const target = t;
    const positions = [];
    const dt = 1 / 60;
    for (let i = 0; i < 60; i++) {
      const stepped = advanceReplayTime({
        t, dt, chapter: ch, targetT: target, recaleRemainMs: recale,
      });
      t = stepped.t;
      recale = stepped.recaleRemainMs;
      positions.push(positionAt(clock, t));
    }

    assert.equal(positions.length, 60);
    for (let i = 1; i < 60; i++) {
      assert.ok(
        progress(positions[i]) > progress(positions[i - 1]),
        `frame ${i} ne progresse pas le long de la jambe`,
      );
      const step = Math.hypot(
        positions[i].lat - positions[i - 1].lat,
        positions[i].lon - positions[i - 1].lon,
      );
      assert.ok(step < jambe / 30, `écart frame ${i} = ${step} ≥ jambe/30`);
    }

    const behind = t + 60_000;
    const slowed = advanceReplayTime({
      t: behind, dt, chapter: ch, targetT: t, recaleRemainMs: 300,
    });
    assert.ok(slowed.t >= behind, "pas de saut arrière si la cible est derrière");
    assert.match(hook, /FILM_RECALE_MS/);
    assert.match(hook, /voiceTargetRef/);
  });
});

describe("useReplay lot RA3 — interpolation jusqu'au dernier chapitre", () => {
  const t0 = Date.parse("2026-05-15T08:00:00Z");
  const hour = 3600000;
  const clock = {
    t0: "2026-05-15T08:00:00.000Z",
    vertices: [
      { tHours: 0, filmNm: 0, sailNm: 0, lat: 46.8, lon: 1.7, bearing: 260 },
      { tHours: 4, filmNm: 122, sailNm: 122, lat: 46.15, lon: -1.16, bearing: 260 },
      { tHours: 8, filmNm: 400, sailNm: 400, lat: 41.9, lon: 8.7, bearing: 140 },
      { tHours: 12, filmNm: 900, sailNm: 900, lat: 14.6, lon: -61.0, bearing: 250 },
    ],
  };
  const chapters = [
    { tA: t0, tB: t0 + 4 * hour, text: "A".repeat(80), fromLat: 46.8, fromLon: 1.7, toLat: 46.15, toLon: -1.16, toName: "La Rochelle" },
    { tA: t0 + 4 * hour, tB: t0 + 8 * hour, text: "B".repeat(80), fromLat: 46.15, fromLon: -1.16, toLat: 41.9, toLon: 8.7, toName: "Ajaccio (Corse)" },
    { tA: t0 + 8 * hour, tB: t0 + 12 * hour, text: "C".repeat(80), fromLat: 41.9, fromLon: 8.7, toLat: 14.6, toLon: -61.0, toName: "Fort-de-France" },
  ];

  it("60 frames entre deux boundaries : positions monotones le long du trait jusqu'au dernier chapitre", () => {
    const plan = filmPlan({ chapters, targetSeconds: 150 });
    const lastIdx = plan.chapters.length - 1;
    const midA = plan.timeAt(0, 10);
    const midB = plan.timeAt(0, 40);
    let t = midA;
    let recale = 0;
    const positions = [];
    const dt = 1 / 60;
    for (let i = 0; i < 60; i++) {
      const ch = plan.chapters[0];
      const stepped = advanceReplayTime({
        t, dt, chapter: ch, targetT: midB, recaleRemainMs: recale,
      });
      t = stepped.t;
      recale = stepped.recaleRemainMs;
      positions.push(positionAt(clock, t));
    }
    for (let i = 1; i < positions.length; i++) {
      assert.ok(
        positions[i].filmNm > positions[i - 1].filmNm,
        `frame ${i} ne progresse pas le long du trait`,
      );
    }

    const along = stepAlongPlan({
      plan,
      clock,
      frames: 60,
      dt: plan.targetSeconds / 60,
      elapsed0: 0,
    });
    assert.equal(along.length, 60);
    assert.equal(along[along.length - 1].chapterIdx, lastIdx);
    assert.equal(along[along.length - 1].lastReached, true);
    for (let i = 1; i < along.length; i++) {
      assert.ok(
        along[i].filmNm >= along[i - 1].filmNm - 1e-9,
        `chapitre ${along[i].chapterIdx} frame ${i} recule (filmNm)`,
      );
    }
    assert.ok(along[along.length - 1].filmNm > along[0].filmNm);
    assert.match(hook, /stepAlongPlan|positionAt\(clockRef/);
    assert.match(hook, /approachStopEvent/);
    assert.match(hook, /lastReached/);
  });

  it("bulle d'approche : une escale proche, rien trop tôt", () => {
    const late = approachStopEvent(chapters[1], { frac: 0.9 });
    assert.equal(late.kind, "stop");
    assert.match(late.card.title, /Ajaccio/);
    assert.equal(approachStopEvent(chapters[1], { frac: 0.2 }), null);
    assert.equal(approachStopEvent({ idx: 0, toName: "", text: "" }, { frac: 0.99 }), null);
  });
});

describe("useReplay lot RA5 — Stop coupe voix, animation, caméra", () => {
  it("stop() met active=false, coupe la voix, libère la caméra", () => {
    const calls = { voice: 0, camera: 0, raf: 0 };
    const next = applyReplayStop({
      cancelRaf: () => { calls.raf += 1; },
      stopVoice: () => { calls.voice += 1; },
      releaseCamera: () => { calls.camera += 1; },
    });
    assert.equal(next.active, false);
    assert.equal(next.tMs, null);
    assert.equal(next.card, null);
    assert.equal(next.progress, 0);
    assert.equal(next.chapterText, "");
    assert.equal(calls.voice, 1);
    assert.equal(calls.camera, 1);
    assert.equal(calls.raf, 1);
    assert.match(hook, /applyReplayStop\(/);
    assert.match(hook, /stopSpeaking/);
    assert.match(hook, /publishFilmEnd/);
    assert.match(app, /onStop: \(\) => \{/);
    assert.match(app, /replay\.stop\(\)/);
    assert.match(app, /VIEW_SUIVRE/);
  });

  it("passer en Suivre/Revoir met escaleStop à null", () => {
    assert.match(app, /shouldCloseEscaleSheet/);
    assert.match(app, /closeEscaleSheet\(\)/);
    assert.match(app, /replayStarting: true/);
    assert.match(app, /nextView: next/);
    assert.match(app, /stop=\{replay\.active \? null : escaleStop\}/);
    assert.match(app, /filmActive: replay\.active/);
    assert.match(app, /clearToken: escaleClear/);
    assert.match(app, /setEscaleClear/);
    assert.match(bar, /data-testid="replay-stop"/);
    assert.match(bar, /data-testid="stop-auto"/);
    assert.match(bar, /testId="listen"/);
    assert.doesNotMatch(bar, /disabled=\{Boolean\(replay\.active\)\}[\s\S]{0,80}replay-stop/);
  });
});

describe("useReplay lot RB6 — voix sans coupure, Stop total, pas de live sur incident", () => {
  it("stop() pendant la lecture coupe voix + animation + caméra au premier geste", () => {
    const order = [];
    const next = applyReplayStop({
      stopVoice: () => { order.push("voice"); },
      releaseCamera: () => { order.push("camera"); },
      cancelRaf: () => { order.push("raf"); },
    });
    assert.deepEqual(order, ["voice", "camera", "raf"]);
    assert.equal(next.active, false);
    assert.equal(next.tMs, null);
    assert.equal(next.progress, 0);

    const stopFn = hook.slice(hook.indexOf("const stop = useCallback"));
    assert.match(stopFn, /stoppingRef\.current = true/);
    assert.ok(
      stopFn.indexOf("stoppingRef.current = true") < stopFn.indexOf("applyReplayStop("),
      "Stop pose le garde-fou avant cancel (onend de Chrome ne relance pas)",
    );
    assert.ok(
      stopFn.indexOf("finishedRef.current = true") < stopFn.indexOf("applyReplayStop("),
      "finish est bloqué avant l'arrêt de la voix",
    );
    assert.match(hook, /shouldReturnToLive/);
    assert.match(hook, /stoppingRef\.current \|\| finishedRef\.current/);
  });
});

describe("useReplay lot RF5 — fin du film : sous-titre de clôture conservé", () => {
  it("applyReplayStop garde le dernier sous-titre si keepChapterText", () => {
    const close = "Aujourd’hui, le bateau est à Nouméa.";
    const merged = `Départ vers Fort-de-France. ${close}`;
    assert.equal(closingSubtitle(merged), close);
    const kept = applyReplayStop({
      keepChapterText: true,
      chapterText: merged,
    });
    assert.equal(kept.active, false);
    assert.equal(kept.chapterText, close);
    assert.equal(kept.progress, 1);
    const cleared = applyReplayStop({});
    assert.equal(cleared.chapterText, "");
    assert.equal(cleared.progress, 0);
  });

  it("finish() arrête sans effacer le sous-titre ; Stop utilisateur l'efface", () => {
    assert.match(hook, /keepSubtitle: true/);
    assert.match(hook, /keepChapterText: keep/);
    assert.match(hook, /chapterTextRef/);
    assert.match(bar, /replay\?\.active \|\| replay\?\.subtitle/);
  });
});

describe("useReplay lot RC16 — sous-titre visible : phrases avion RF5", () => {
  it("choisit les phrases avion déjà dans le chapitre, sans inventer", () => {
    const long = [
      "Puis, le 18 août, départ vers Saint-Pierre-et-Miquelon, escale prévue.",
      "Puis, le 18 août, l'équipage prend l'avion pour Halifax.",
      "Ensuite, le 22 août, retour en avion vers Cayenne.",
    ].join(" ");
    const shown = visibleFilmSubtitle(long);
    assert.match(shown, /prend l'avion pour Halifax/);
    assert.match(shown, /retour en avion vers Cayenne/);
    assert.doesNotMatch(shown, /départ vers Saint-Pierre/);
    assert.equal(filmSubtitleShowsAir(shown), true);
    const plain = "Départ de Saint-Maur vers La Rochelle.";
    assert.equal(visibleFilmSubtitle(plain), plain);
    assert.equal(filmSubtitleShowsAir(plain), false);
    const en = "Then, on 18 August, the crew flies to Halifax. Later, return flight to Cayenne.";
    assert.match(visibleFilmSubtitle(en), /the crew flies to Halifax/);
    assert.match(visibleFilmSubtitle(en), /return flight to Cayenne/);
    assert.equal(visibleFilmSubtitle(""), "");
  });

  it("App passe le sous-titre choisi ; la barre ne tronque pas l'avion", () => {
    assert.match(app, /visibleFilmSubtitle\(replay\.subtitle \|\| replay\.chapterText\)/);
    assert.match(bar, /visibleFilmSubtitle/);
    assert.match(bar, /filmSubtitleHighlight/);
    assert.match(bar, /data-testid="film-subtitle-place"/);
    assert.match(bar, /filmSubtitleShowsAir/);
    assert.match(bar, /filmSubtitleAir \? "whitespace-normal" : "truncate"/);
    assert.doesNotMatch(bar, /data-testid="film-subtitle" className="[^"]*truncate/);
  });
});

describe("useReplay lot RG9 — client robuste (E2, E3, E4)", () => {
  const t0 = Date.parse("2026-05-15T08:00:00Z");
  const hour = 3600000;

  function longChapters(n = 7, chars = 200) {
    return Array.from({ length: n }, (_, i) => ({
      tA: t0 + i * 4 * hour,
      tB: t0 + (i + 1) * 4 * hour,
      text: `${"Phrase une du chapitre. ".padEnd(80)}Phrase deux vers le lieu ${i}. `.padEnd(chars, "x"),
      fromLat: 46 - i,
      fromLon: -1 - i,
      toLat: 45 - i,
      toLon: -2 - i,
      fromName: "La Rochelle",
      toName: "Ajaccio",
    }));
  }

  it("sans voix : durée ≥ 90 % de l'estimée, ended seulement à la dernière phrase", () => {
    assert.equal(FILM_VOICE_STALL_MS, 2000);
    assert.equal(FILM_VISIBILITY_CATCHUP_MS, 2000);
    const chapters = longChapters(7, 200);
    const plan = filmPlan({ chapters, targetSeconds: 150 });
    const speakSec = wallClockSpeakSeconds(plan, FILM_ESTIMATE_CPS);
    assert.ok(speakSec >= 90, `estimée trop courte: ${speakSec}`);
    const early = linearFilmAt(53, plan);
    assert.equal(early.finish, false, "53 s ne termine pas un film de 7 chapitres");
    assert.ok(early.chapterIdx < plan.chapters.length - 1);
    assert.equal(linearFilmAt(speakSec * 0.89, plan).finish, false);

    let ended = false;
    let elapsed = 0;
    const dt = 0.5;
    let finishAt = null;
    while (elapsed <= speakSec + 2) {
      const at = linearFilmAt(elapsed, plan);
      if (at.finish) {
        ended = true;
        finishAt = elapsed;
        assert.equal(at.lastReached, true);
        assert.equal(at.chapterIdx, plan.chapters.length - 1);
        break;
      }
      elapsed += dt;
    }
    assert.equal(ended, true);
    assert.ok(finishAt >= speakSec * 0.9, `fini à ${finishAt} s < 90 % de ${speakSec}`);
    assert.match(hook, /visibilitychange/);
    assert.match(hook, /voiceBoundaryAtRef\.current === 0/);
    assert.match(hook, /voiceCharRef\.current > 0/);
    assert.match(hook, /filmBarSubtitle/);
    assert.match(hook, /filmSubtitleAt/);
    assert.match(readFileSync(join(here, "useReplayVoice.js"), "utf8"), /onLeadFailedRef\.current/);
  });

  it("sous-titre : une phrase à la fois, lieu mis en avant quand il est dit", () => {
    const text = "Départ vers La Rochelle. Ensuite cap sur Ajaccio. Arrivée à Fort-de-France.";
    const starts = splitFilmSentences(text).map((s) => s.start);
    assert.ok(starts.length >= 3);
    const first = filmSubtitleAt(text, text.indexOf("La Rochelle") + 1, {
      toName: "La Rochelle", sentenceStarts: starts,
    });
    const second = filmSubtitleAt(text, text.indexOf("Ajaccio") + 1, {
      toName: "Ajaccio", sentenceStarts: starts,
    });
    const third = filmSubtitleAt(text, text.indexOf("Fort-de-France") + 1, {
      toName: "Fort-de-France", sentenceStarts: starts,
    });
    assert.notEqual(first.sentence, second.sentence);
    assert.notEqual(second.sentence, third.sentence);
    assert.match(first.sentence, /La Rochelle/);
    assert.doesNotMatch(first.sentence, /Ajaccio/);
    assert.equal(first.place, "La Rochelle");
    assert.equal(second.place, "Ajaccio");
    assert.equal(third.place, "Fort-de-France");
    const beforeName = filmSubtitleAt(text, text.indexOf("Fort-de-France") - 1, {
      toName: "Fort-de-France", sentenceStarts: starts,
    });
    assert.equal(beforeName.place, "");
    const hi = filmSubtitleHighlight(third.sentence, third.place);
    assert.equal(hi.place, "Fort-de-France");
    assert.ok(hi.before.includes("Arrivée"));
  });

  it("barre : chapitre entier au départ et au seek, phrase ensuite", () => {
    const text = "L’expédition a quitté Saint-Maur. Puis La Rochelle. Ensuite l’avion pour Halifax.";
    const starts = splitFilmSentences(text).map((s) => s.start);
    const atStart = filmBarSubtitle({ chapterText: text, charIdx: 0, sentenceStarts: starts });
    assert.match(atStart.text, /La Rochelle/);
    assert.match(atStart.text, /avion/);
    assert.equal(atStart.sentenceMode, false);
    const later = filmBarSubtitle({
      chapterText: text,
      charIdx: text.indexOf("La Rochelle"),
      sentenceStarts: starts,
      toName: "La Rochelle",
    });
    assert.equal(later.sentenceMode, true);
    assert.match(later.text, /La Rochelle/);
    assert.doesNotMatch(later.text, /avion/);
    assert.equal(later.place, "La Rochelle");
    const pinned = filmBarSubtitle({
      chapterText: text,
      charIdx: text.length,
      pinned: true,
      sentenceStarts: starts,
    });
    assert.equal(pinned.sentenceMode, false);
    assert.match(pinned.text, /avion/);
    const air = "Mer calme. L’équipage prend l’avion pour Halifax. Retour en avion vers Cayenne.";
    const airPinned = filmBarSubtitle({ chapterText: air, charIdx: air.length, pinned: true });
    assert.match(airPinned.text, /avion/i);
    assert.ok(airPinned.text.length < air.length || /prend l['’]avion/i.test(airPinned.text));
    const officialCh1 = "L’expédition Berry-Mappemonde a quitté Saint-Maur le 15 mai 2026. Puis, le 15 mai, départ vers La Rochelle.";
    const rb5 = filmBarSubtitle({ chapterText: officialCh1, charIdx: 0 });
    assert.match(rb5.text, /La Rochelle/);
    assert.match(filmSubtitleAt(officialCh1, 0).sentence, /Saint-Maur/);
    assert.doesNotMatch(filmSubtitleAt(officialCh1, 0).sentence, /La Rochelle/);
  });

  it("reprise d'onglet : rampe ≤ 2 s, aucun pas égal au saut", () => {
    const fromT = 1_000;
    const toT = fromT + 20 * 3600 * 1000;
    const gap = toT - fromT;
    const frames = 60;
    let prev = fromT;
    let maxStep = 0;
    for (let i = 1; i <= frames; i += 1) {
      const stepped = visibilityCatchupStep({
        fromT,
        toT,
        elapsedMs: (i / frames) * FILM_VISIBILITY_CATCHUP_MS,
        durationMs: FILM_VISIBILITY_CATCHUP_MS,
      });
      maxStep = Math.max(maxStep, Math.abs(stepped.t - prev));
      prev = stepped.t;
    }
    assert.ok(maxStep < gap / 2, `pas max ${maxStep} trop proche du saut ${gap}`);
    assert.ok(Math.abs(prev - toT) < 1);
    const mid = visibilityCatchupStep({
      fromT, toT, elapsedMs: 1000, durationMs: 2000,
    });
    assert.equal(mid.done, false);
    assert.ok(mid.t > fromT && mid.t < toT);
    const end = visibilityCatchupStep({
      fromT, toT, elapsedMs: 2000, durationMs: 2000,
    });
    assert.equal(end.done, true);
    assert.equal(end.t, toT);
  });
});
