import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { filmPlan } from "../engine/replay.js";
import { linearFilmAt, pickFilmChapters, voiceLeadPolicy } from "./useReplay.js";

const here = dirname(fileURLToPath(import.meta.url));
const hook = readFileSync(join(here, "useReplay.js"), "utf8");
const app = readFileSync(join(here, "..", "App.jsx"), "utf8");
const bar = readFileSync(join(here, "..", "components", "SimulationFilmBar.jsx"), "utf8");

describe("useReplay contract (lot E)", () => {
  it("replays on the official clock, consumes the film plan, and hands back to live at the end or on Stop", () => {
    assert.match(hook, /replayWindow\(clock, Date\.now\(\)\)/);
    assert.match(hook, /requestAnimationFrame\(tick\)/);
    assert.match(hook, /if \(done\)/);
    assert.match(hook, /const stop = useCallback/);
    assert.match(hook, /\/voyage\/official\/film/);
    assert.match(hook, /buildFilmScript/);
    assert.doesNotMatch(hook, /Tavily|Nebius/i);
  });

  it("App swaps the live boat for the replayed one in Suivre, jumps the playhead each frame, reads each new leg aloud", () => {
    assert.match(app, /replay\.active && replay\.live \? replay\.live : official\.live/);
    assert.match(app, /jump: Boolean\(live\.replay\)/);
    // The voice lives in hooks/useReplayVoice.js since lot J; App mounts it.
    assert.match(app, /useReplayVoice\(\{/);
    assert.match(app, /chapterText: replay\.chapterText/);
    assert.match(readFileSync(join(here, "useReplayVoice.js"), "utf8"), /speak\(chapterText, lang/);
    assert.match(app, /momentNow=\{replay\.active \? replay\.card/);
    assert.match(app, /storyReplay=\{replay\.active\}/);
  });

  it("the film bar offers Revoir / Retour au live ; voice follows Écouter (no 🔊)", () => {
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
    assert.match(hook, /targetSeconds/);
    assert.match(hook, /if \(done\)/);
    assert.match(bar, /data-testid="film-subtitle"/);
    assert.match(bar, /data-testid="film-duration"/);
  });

  it("lot F4 : les événements du chapitre ouvrent la bulle (même texte que la carte NOW)", () => {
    assert.match(hook, /pickFilmEvent/);
    assert.match(hook, /publishEventBubble/);
    assert.match(hook, /filmBubbleRef/);
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
    assert.doesNotMatch(hook, /targetSeconds \+ 20/);
  });

  it("script API sans emprise → brut local (première jambe avec coords)", () => {
    const remote = { chapters: [{ id: "leg-0", text: "Ajaccio", fromLat: null, fromLon: null, toLat: null, toLon: null }], source: "rules" };
    const local = { chapters, source: "rules" };
    const picked = pickFilmChapters(remote, local, []);
    assert.equal(picked.remote, false);
    assert.equal(picked.chapters[0].fromLat, 48.8);
    assert.ok(chapterHasFirstLeg(picked.chapters[0]));
  });
});

function chapterHasFirstLeg(ch) {
  return Number.isFinite(ch.fromLat) && Number.isFinite(ch.toLat);
}
