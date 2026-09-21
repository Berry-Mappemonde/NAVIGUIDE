import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { applyFilmCamera, filmChapterZoom } from "./filmCamera.js";

const here = dirname(fileURLToPath(import.meta.url));
const controller = readFileSync(join(here, "MapSceneController.js"), "utf8");

describe("filmCamera lot R3 — premier mouvement = chapitre 1", () => {
  it("cadre la première jambe (Saint-Maur → La Rochelle), zoom [3 ; 7], sans flyTo", () => {
    const calls = [];
    const map = {
      flyTo(center, zoom) { calls.push({ action: "flyTo", center, zoom }); },
      setView(center, zoom, opts) { calls.push({ action: "setView", center, zoom, opts }); },
      getBoundsZoom() { return 6; },
      getSize() { return { x: 1280, y: 800 }; },
      getBounds() {
        return {
          getNorth: () => 20,
          getSouth: () => -40,
          getEast: () => 180,
          getWest: () => 120,
        };
      },
    };
    const leg = { fromLat: 46.8075, fromLon: 1.6358, toLat: 46.1541, toLon: -1.167 };
    const zoom = filmChapterZoom(map, leg);
    assert.ok(zoom >= 3 && zoom <= 7, `zoom chapitre 1 = ${zoom}`);

    const first = applyFilmCamera(map, {
      chapterIdx: 0,
      lastChapterIdx: null,
      lat: 46.8075,
      lon: 1.6358,
      heading: 260,
      zoom,
      now: 1000,
    });
    assert.equal(first.action, "setView");
    assert.equal(calls.length, 1);
    assert.equal(calls[0].action, "setView");
    assert.deepEqual(calls[0].center, [46.8075, 1.6358], "pas d'offset vers l'Asie");
    assert.equal(calls[0].zoom, zoom);
    assert.equal(calls[0].opts?.animate, false);
    assert.equal(calls.filter((c) => c.action === "flyTo").length, 0);

    const next = applyFilmCamera(map, {
      chapterIdx: 1,
      lastChapterIdx: first.lastChapterIdx,
      lat: 46.1541,
      lon: -1.167,
      heading: 140,
      zoom,
      now: 3000,
      lastSetViewAt: first.lastSetViewAt,
      flyingUntil: first.flyingUntil,
    });
    assert.equal(next.action, "flyTo");
    assert.equal(calls.filter((c) => c.action === "flyTo").length, 1);
  });

  it("MapSceneController : pas de flyTo / fitBounds sur la route entière au lancement ni au retour live", () => {
    assert.match(controller, /if \(!previous\.filmActive && this\.config\.filmActive\)/);
    assert.match(controller, /if \(previous\.filmActive && !this\.config\.filmActive\)/);
    assert.match(controller, /this\.camera\.recapture = this\.config\.cinemaRecapture/);
    assert.match(controller, /this\.map\.setView\(\s*\[\s*live\.lat,\s*lonCam\s*\]/);
    assert.doesNotMatch(controller, /filmActive[\s\S]{0,80}fitBounds/);
    assert.doesNotMatch(controller, /filmActive[\s\S]{0,200}zoomForRemaining/);
  });
});
