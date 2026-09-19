import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "MapSceneController.js"), "utf8");

describe("MapSceneController — boats (lot I)", () => {
  it("our `visible` decision is never overridden by the actor's own flag (spread first)", () => {
    for (const role of ["simulation", "ghost", "side", "plane", "drawing"]) {
      const idx = src.indexOf(`this.syncMarker("${role}", {`);
      assert.ok(idx > 0, role);
      const block = src.slice(idx, idx + 260);
      const spread = block.indexOf("...");
      const visible = block.indexOf("visible:");
      assert.ok(spread > 0 && visible > spread, `${role}: spread must come before visible`);
    }
  });

  it("entering or leaving the drawing mode re-syncs the boats even while paused; flags stay put while the camera follows", () => {
    assert.match(src, /previous\.drawingMode !== this\.config\.drawingMode[\s\S]{0,120}this\.syncMarkers\(this\.currentCast, this\.currentPlayback\)/);
    assert.match(src, /if \(reason === "follow"\) return;/);
    assert.match(src, /isCameraFollowing\(\)/);
  });
});
