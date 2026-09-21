import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { applyFilmCamera, clampFilmPan, filmChapterZoom, FILM_ZOOM_ARCHIPELAGO_MAX } from "./filmCamera.js";

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

describe("filmCamera lot R4 — pan borné, un flyTo par chapitre", () => {
  function fakeMap(center = { lat: 46, lng: -1 }) {
    const calls = [];
    let here = { ...center };
    const map = {
      flyTo(c, zoom) { calls.push({ action: "flyTo", center: c, zoom }); here = { lat: c[0], lng: c[1] }; },
      setView(c, zoom, opts) { calls.push({ action: "setView", center: c, zoom, opts }); here = { lat: c[0], lng: c[1] }; },
      getSize() { return { x: 1000, y: 800 }; },
      getCenter() { return here; },
      latLngToContainerPoint(ll) {
        const lat = Array.isArray(ll) ? ll[0] : ll.lat;
        const lng = Array.isArray(ll) ? ll[1] : ll.lng;
        return { x: lng * 10, y: lat * 10 };
      },
      containerPointToLatLng(p) { return { lat: p.y / 10, lng: p.x / 10 }; },
      getBoundsZoom() { return 5; },
      getBounds() {
        return {
          getNorth: () => 50,
          getSouth: () => 40,
          getEast: () => 10,
          getWest: () => -10,
        };
      },
    };
    return { map, calls };
  }

  it("borne le déplacement par frame à 2 % de la largeur d'écran", () => {
    const { map } = fakeMap({ lat: 46, lng: -1 });
    const clamped = clampFilmPan([46, -1], [46, 9], map);
    const movedPx = Math.abs((clamped[1] - (-1)) * 10);
    assert.ok(movedPx <= 20 + 1e-6, `déplacement ${movedPx} px > 20 px (2 % de 1000)`);

    const first = applyFilmCamera(map, {
      chapterIdx: 0,
      lastChapterIdx: 0,
      lat: 46,
      lon: 9,
      heading: 90,
      zoom: 5,
      now: 50,
      lastCenter: [46, -1],
    });
    assert.equal(first.action, "setView");
    const step = Math.abs(first.lastCenter[1] - (-1));
    assert.ok(step <= 2 + 1e-6, `lon ${step}° > 2°`);
  });

  it("un seul flyTo par changement de chapitre", () => {
    const { map, calls } = fakeMap();
    const a = applyFilmCamera(map, {
      chapterIdx: 0, lastChapterIdx: null, lat: 46, lon: -1, heading: 0, zoom: 5, now: 0,
    });
    const b = applyFilmCamera(map, {
      chapterIdx: 1, lastChapterIdx: a.lastChapterIdx, lat: 40, lon: 8, heading: 0, zoom: 5,
      now: 100, lastSetViewAt: a.lastSetViewAt, flyingUntil: a.flyingUntil, lastCenter: a.lastCenter,
    });
    assert.equal(b.action, "flyTo");
    for (let i = 0; i < 8; i++) {
      const wait = applyFilmCamera(map, {
        chapterIdx: 1, lastChapterIdx: b.lastChapterIdx, lat: 40, lon: 8, heading: 0, zoom: 5,
        now: 200 + i * 50, lastSetViewAt: b.lastSetViewAt, flyingUntil: b.flyingUntil, lastCenter: b.lastCenter,
      });
      assert.equal(wait.action, "fly-wait");
    }
    assert.equal(calls.filter((c) => c.action === "flyTo").length, 1);
  });
});

describe("filmCamera lot RA3 — dézoom archipels, tuiles gardées", () => {
  it("plafonne le zoom pour une jambe à sauts courts", () => {
    const map = {
      getBoundsZoom() { return 8; },
      getSize() { return { x: 1280, y: 800 }; },
    };
    const hop = { fromLat: 14.6, fromLon: -61.07, toLat: 16.25, toLon: -61.53 };
    const z = filmChapterZoom(map, hop);
    assert.ok(z <= FILM_ZOOM_ARCHIPELAGO_MAX, `zoom archipel ${z} > ${FILM_ZOOM_ARCHIPELAGO_MAX}`);
    assert.ok(z >= 3);

    const ocean = { fromLat: 41.92, fromLon: 8.74, toLat: 14.6, toLon: -61.07 };
    const zOcean = filmChapterZoom(map, ocean);
    assert.ok(zOcean <= 7);
    assert.ok(z < zOcean || z <= FILM_ZOOM_ARCHIPELAGO_MAX);
  });

  it("pas de switch de base layer pendant filmActive", () => {
    assert.match(controller, /switchBaseLayer\(/);
    assert.match(controller, /if \(this\.config\.filmActive\)/);
    assert.match(controller, /if \(!this\.baseLayer\) this\.switchBaseLayer\(url\)/);
    assert.match(controller, /next\.addTo\(this\.map\)/);
    assert.match(controller, /if \(prev && prev !== next\) prev\.remove\(\)/);
    assert.match(controller, /exitHoldZoom/);
    assert.doesNotMatch(controller, /filmActive[\s\S]{0,80}fitBounds/);
    assert.doesNotMatch(controller, /filmActive[\s\S]{0,200}zoomForRemaining/);
  });
});
