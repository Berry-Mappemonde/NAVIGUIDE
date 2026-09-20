import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

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
});
