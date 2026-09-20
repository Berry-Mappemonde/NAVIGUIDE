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
  it("replays on the official clock only, never fetches, and hands back to live at the end or on Stop", () => {
    assert.match(hook, /replayWindow\(clock, Date\.now\(\)\)/);
    assert.match(hook, /requestAnimationFrame\(tick\)/);
    assert.match(hook, /if \(done\)/);
    assert.match(hook, /const stop = useCallback/);
    assert.doesNotMatch(hook, /fetch\(|Nemotron|Tavily|Nebius/i);
  });

  it("App swaps the live boat for the replayed one in Suivre, jumps the playhead each frame, reads each new leg aloud", () => {
    assert.match(app, /replay\.active && replay\.live \? replay\.live : official\.live/);
    assert.match(app, /jump: Boolean\(live\.replay\)/);
    assert.match(app, /speak\(last, lang\)/);
    assert.match(app, /momentNow=\{replay\.active \? replay\.card/);
    assert.match(app, /storyReplay=\{replay\.active\}/);
  });

  it("the film bar offers Revoir / Retour au live and a voice switch", () => {
    assert.match(bar, /data-testid="replay-start"/);
    assert.match(bar, /data-testid="replay-stop"/);
    assert.match(bar, /data-testid="replay-voice"/);
  });
});
