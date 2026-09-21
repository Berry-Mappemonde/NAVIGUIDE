import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { applyFilmCamera } from "./filmCamera.js";

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

describe("MapSceneController — caméra film (lot F1)", () => {
  it("aucun flyTo hors changement de chapitre (faux map)", () => {
    const calls = { flyTo: 0, setView: 0 };
    const map = {
      flyTo() { calls.flyTo += 1; },
      setView() { calls.setView += 1; },
      getBounds() {
        return { getNorth: () => 10, getSouth: () => 0, getEast: () => 10, getWest: () => 0 };
      },
    };
    let st = { lastChapterIdx: null, lastSetViewAt: 0, flyingUntil: 0 };
    const step = (chapterIdx, now, lat = 46, lon = -1) => {
      const next = applyFilmCamera(map, {
        chapterIdx,
        lastChapterIdx: st.lastChapterIdx,
        lat,
        lon,
        heading: 240,
        zoom: 5,
        now,
        lastSetViewAt: st.lastSetViewAt,
        flyingUntil: st.flyingUntil,
      });
      st = { lastChapterIdx: next.lastChapterIdx, lastSetViewAt: next.lastSetViewAt, flyingUntil: next.flyingUntil };
      return next;
    };
    assert.equal(step(0, 1000).action, "flyTo");
    assert.equal(calls.flyTo, 1);
    assert.equal(step(0, 1100).action, "fly-wait");
    assert.equal(calls.flyTo, 1, "même chapitre pendant le flyTo : pas de second flyTo");
    assert.equal(step(0, 2300).action, "setView");
    assert.equal(calls.flyTo, 1);
    assert.equal(calls.setView, 1);
    assert.equal(step(0, 2320).action, "skip");
    assert.equal(calls.flyTo, 1);
    assert.equal(step(1, 5000).action, "flyTo");
    assert.equal(calls.flyTo, 2);
    assert.match(src, /if \(cfg\.filmActive\)/);
    assert.match(src, /syncFilmCamera/);
    assert.doesNotMatch(src, /filmActive[\s\S]{0,200}zoomForRemaining/);
  });
});

describe("MapSceneController — zoom (lot U)", () => {
  it("n'orchestre pas un recalcul d'offsets pendant zoomanim ; attend zoomend + 250 ms", () => {
    assert.match(src, /map\.on\("zoomanim"/);
    assert.match(src, /map\.on\("zoomend"/);
    assert.match(src, /reason: "zoom"/);
    const animStart = src.indexOf("this.onZoomAnim = ");
    const animEnd = src.indexOf("this.onZoomEnd = ");
    assert.ok(animStart > 0 && animEnd > animStart);
    const anim = src.slice(animStart, animEnd);
    assert.doesNotMatch(anim, /syncWaypoints\(/);
    assert.doesNotMatch(anim, /scheduleWaypoints\(/);
    const zoomEnd = src.slice(src.indexOf("this.onZoomEnd = "), src.indexOf("this.onMoveEnd = "));
    assert.match(zoomEnd, /scheduleWaypoints\(\{ reason: "zoom" \}\)/);
    assert.match(src, /preferCanvas:\s*true/);
    assert.match(src, /divIconCache/);
    assert.match(src, /flagWorldLngsForView/);
  });

  it("onMoveEnd ne relance ni /ici ni le récit", () => {
    const start = src.indexOf("this.onMoveEnd = ");
    const end = src.indexOf("this.onUserNavigation = ");
    const block = src.slice(start, end);
    assert.doesNotMatch(block, /\/ici|narrateIci|enqueueStory|fetch\(/);
  });
});
