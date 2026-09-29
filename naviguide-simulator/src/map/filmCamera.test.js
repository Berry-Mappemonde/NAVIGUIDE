import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { FILM_BOAT_KEEP_FRAC, FILM_PAN_MAX_SCREEN } from "../engine/replay.js";
import {
  applyFilmCamera,
  clampFilmPan,
  filmApproachZoom,
  filmChapterZoom,
  FILM_INTERP_DELAY_MS,
  FILM_TILE_SLOW,
  FILM_ZOOM_ARCHIPELAGO_MAX,
  filmPanMaxFrac,
  interpolateFilmSamples,
  keepBoatInFrame,
  preloadFilmTiles,
  pushFilmSample,
  smoothFilmHeading,
  stepFilmCamera,
  tilesAlongLeg,
} from "./filmCamera.js";

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
    assert.equal(next.action, "setView");
    assert.equal(calls.filter((c) => c.action === "flyTo").length, 0);
    assert.equal(calls.filter((c) => c.action === "setView").length, 2);
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

describe("filmCamera lot R4 / RG13 — pan borné, un setView par chapitre", () => {
  function fakeMap(center = { lat: 46, lng: -1 }) {
    const calls = [];
    let here = { ...center };
    const map = {
      flyTo(c, zoom) { calls.push({ action: "flyTo", center: c, zoom }); here = { lat: c[0], lng: c[1] }; },
      setView(c, zoom, opts) { calls.push({ action: "setView", center: c, zoom, opts }); here = { lat: c[0], lng: c[1] }; },
      panBy(offset) {
        calls.push({ action: "panBy", offset });
        const p0 = map.latLngToContainerPoint([here.lat, here.lng]);
        const ll = map.containerPointToLatLng({ x: p0.x + offset[0], y: p0.y + offset[1] });
        here = { lat: ll.lat, lng: ll.lng };
      },
      _rawPanBy(offset) {
        calls.push({ action: "panBy", offset });
        const p0 = map.latLngToContainerPoint([here.lat, here.lng]);
        const ll = map.containerPointToLatLng({ x: p0.x + (offset.x ?? 0), y: p0.y + (offset.y ?? 0) });
        here = { lat: ll.lat, lng: ll.lng };
      },
      getSize() { return { x: 1000, y: 800 }; },
      getCenter() { return here; },
      getZoom() { return 5; },
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

  it("borne le pas par la vitesse, et garde le bateau dans 40 % du centre", () => {
    const { map } = fakeMap({ lat: 46, lng: -1 });
    const clamped = clampFilmPan([46, -1], [46, 9], map, { maxFrac: FILM_PAN_MAX_SCREEN, boat: [46, -0.5] });
    const movedPx = Math.abs((clamped[1] - (-1)) * 10);
    assert.ok(movedPx <= 1000 * FILM_BOAT_KEEP_FRAC + 1e-6, `déplacement ${movedPx} px hors cadre`);

    const first = applyFilmCamera(map, {
      chapterIdx: 0,
      lastChapterIdx: 0,
      lat: 46,
      lon: -0.5,
      heading: 90,
      zoom: 5,
      now: 50,
      lastCenter: [46, -1],
      boatPx: 8,
      framesSinceReset: 0,
    });
    assert.ok(first.action === "panBy" || first.action === "setView" || first.action === "hold");
    const step = Math.abs(first.lastCenter[1] - (-1));
    assert.ok(step <= 4 + 1e-6, `lon ${step}° trop grand pour un pas`);
  });

  it("un seul setView au changement de chapitre, puis translation", () => {
    const { map, calls } = fakeMap();
    const a = applyFilmCamera(map, {
      chapterIdx: 0, lastChapterIdx: null, lat: 46, lon: -1, heading: 0, zoom: 5, now: 0,
    });
    const b = applyFilmCamera(map, {
      chapterIdx: 1, lastChapterIdx: a.lastChapterIdx, lat: 40, lon: 8, heading: 0, zoom: 5,
      now: 100, lastSetViewAt: a.lastSetViewAt, flyingUntil: a.flyingUntil, lastCenter: a.lastCenter,
    });
    assert.equal(b.action, "setView");
    assert.equal(calls.filter((c) => c.action === "flyTo").length, 0);
    let st = b;
    for (let i = 0; i < 8; i++) {
      st = applyFilmCamera(map, {
        chapterIdx: 1, lastChapterIdx: st.lastChapterIdx, lat: 40.01 + i * 0.002, lon: 8.01 + i * 0.002,
        heading: 0, zoom: 5,
        now: 200 + i * 16, lastSetViewAt: st.lastSetViewAt, flyingUntil: 0, lastCenter: st.lastCenter,
        framesSinceReset: st.framesSinceReset, boatPx: 6,
      });
      assert.notEqual(st.action, "flyTo");
      assert.notEqual(st.action, "fly-wait");
    }
    assert.equal(calls.filter((c) => c.action === "flyTo").length, 0);
    assert.ok(calls.filter((c) => c.action === "panBy").length >= 1, "pas de translation après le chapitre");
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

describe("filmCamera lot RF6 — interpolation hors React, zoom figé, tuiles", () => {
  function fakeMap(center = { lat: 46, lng: -1 }) {
    const calls = [];
    let here = { ...center };
    const map = {
      flyTo(c, zoom) { calls.push({ action: "flyTo", center: c, zoom }); here = { lat: c[0], lng: c[1] }; },
      setView(c, zoom, opts) { calls.push({ action: "setView", center: c, zoom, opts }); here = { lat: c[0], lng: c[1] }; },
      panBy(offset) {
        calls.push({ action: "panBy", offset });
        const p0 = map.latLngToContainerPoint([here.lat, here.lng]);
        const ll = map.containerPointToLatLng({ x: p0.x + offset[0], y: p0.y + offset[1] });
        here = { lat: ll.lat, lng: ll.lng };
      },
      _rawPanBy(offset) {
        calls.push({ action: "panBy", offset });
        const p0 = map.latLngToContainerPoint([here.lat, here.lng]);
        const ll = map.containerPointToLatLng({ x: p0.x + (offset.x ?? 0), y: p0.y + (offset.y ?? 0) });
        here = { lat: ll.lat, lng: ll.lng };
      },
      getSize() { return { x: 1000, y: 800 }; },
      getCenter() { return here; },
      getZoom() { return 5; },
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

  it("cadence dégradée : positions caméra monotones, pas au-delà du pas borné", () => {
    const { map } = fakeMap({ lat: 46, lng: -1 });
    const samples = [];
    for (let i = 0; i <= 5; i++) {
      pushFilmSample(samples, {
        t: i * 200,
        lat: 46,
        lon: -1 + i * 2,
        heading: 90,
        chapterIdx: 0,
      });
    }
    let lastChapterIdx = 0;
    let lastCenter = [46, -1];
    let flyingUntil = 0;
    let framesSinceReset = 0;
    let lastBoat = { lat: 46, lon: -1 };
    const centers = [];
    const actions = [];
    const maxPx = 1000 * FILM_BOAT_KEEP_FRAC + 1e-6;
    for (let now = FILM_INTERP_DELAY_MS; now <= 1000; now += 16) {
      const next = stepFilmCamera(map, {
        samples,
        now,
        lastChapterIdx,
        lastCenter,
        flyingUntil,
        zoom: 5,
        tilesReady: true,
        chapterIdx: 0,
        lastBoat,
        framesSinceReset,
      });
      lastChapterIdx = next.lastChapterIdx;
      lastCenter = next.lastCenter;
      flyingUntil = next.flyingUntil;
      framesSinceReset = next.framesSinceReset || 0;
      if (next.pose) lastBoat = { lat: next.pose.lat, lon: next.pose.lon };
      actions.push(next.action);
      if ((next.action === "setView" || next.action === "panBy") && lastCenter) centers.push(lastCenter);
    }
    assert.ok(centers.length >= 8, `pas assez de pas (${centers.length})`);
    assert.ok(actions.filter((a) => a === "panBy").length >= 4, `pas assez de panBy (${actions.join(",")})`);
    for (let i = 1; i < centers.length; i++) {
      assert.ok(centers[i][1] >= centers[i - 1][1] - 1e-9, `lon recule à ${i}`);
      const stepPx = Math.abs((centers[i][1] - centers[i - 1][1]) * 10);
      assert.ok(stepPx <= maxPx, `saut ${stepPx} px > ${maxPx} px`);
    }
    assert.equal(filmPanMaxFrac(false), FILM_PAN_MAX_SCREEN * FILM_TILE_SLOW);
  });

  it("zoom de croisière stable au milieu de jambe (hors approche)", () => {
    const { map, calls } = fakeMap();
    const samples = [];
    pushFilmSample(samples, { t: 0, lat: 46, lon: -1, heading: 90, chapterIdx: 0 });
    pushFilmSample(samples, { t: 400, lat: 46.2, lon: 0, heading: 90, chapterIdx: 0 });
    let st = { lastChapterIdx: 0, lastCenter: [46, -1], flyingUntil: 0, framesSinceReset: 0 };
    for (let now = 80; now <= 400; now += 16) {
      const next = stepFilmCamera(map, {
        samples,
        now,
        ...st,
        zoom: 5,
        baseZoom: 5,
        chapterIdx: 0,
      });
      st = {
        lastChapterIdx: next.lastChapterIdx,
        lastCenter: next.lastCenter,
        flyingUntil: next.flyingUntil,
        framesSinceReset: next.framesSinceReset || 0,
      };
    }
    const zooms = calls.filter((c) => c.action === "setView").map((c) => c.zoom);
    assert.ok(zooms.every((z) => z == null || Math.abs(z - 5) < 0.4), `zoom ${zooms.join(",")}`);
  });

  it("interpole entre deux échantillons espacés", () => {
    const samples = [];
    pushFilmSample(samples, { t: 0, lat: 46, lon: -1, heading: 90, chapterIdx: 0, filmNm: 0 });
    pushFilmSample(samples, { t: 200, lat: 46, lon: 1, heading: 90, chapterIdx: 0, filmNm: 10 });
    const mid = interpolateFilmSamples(samples, 100);
    assert.ok(Math.abs(mid.lon - 0) < 1e-9, `lon milieu ${mid.lon}`);
    assert.ok(Math.abs(mid.filmNm - 5) < 1e-9);
  });

  it("précharge les tuiles d'une jambe au zoom du chapitre", () => {
    const tiles = tilesAlongLeg({ fromLat: 46, fromLon: -1, toLat: 46.2, toLon: 0 }, 5);
    assert.ok(tiles.length > 0);
    assert.ok(tiles.every((t) => t.z === 5));
    const urls = [];
    class FakeImage {
      set src(v) { urls.push(v); }
    }
    preloadFilmTiles("http://t/{z}/{y}/{x}", tiles.slice(0, 3), { ImageCtor: FakeImage });
    assert.equal(urls.length, 3);
    assert.match(urls[0], /\/5\//);
  });

  it("MapSceneController : boucle rAF hors du rendu React", () => {
    assert.match(controller, /ensureFilmCameraLoop/);
    assert.match(controller, /requestAnimationFrame\(tick\)/);
    assert.match(controller, /stepFilmCamera/);
    assert.match(controller, /preloadFilmTiles/);
    assert.doesNotMatch(controller, /if \(this\.config\.filmActive\) this\.syncFilmCamera\(this\.config\);/);
  });
});

describe("filmCamera lot RG13 — 60 Hz, cap lissé, zoom d'approche", () => {
  it("ne pose pas de setView à chaque frame : translation puis commit", () => {
    const calls = [];
    let here = { lat: 46, lng: -1 };
    const map = {
      flyTo() { calls.push("flyTo"); },
      setView(c) { calls.push("setView"); here = { lat: c[0], lng: c[1] }; },
      _rawPanBy() { calls.push("panBy"); },
      panBy() { calls.push("panBy"); },
      getSize() { return { x: 1000, y: 800 }; },
      getCenter() { return here; },
      getZoom() { return 5; },
      latLngToContainerPoint(ll) {
        const lat = Array.isArray(ll) ? ll[0] : ll.lat;
        const lng = Array.isArray(ll) ? ll[1] : ll.lng;
        return { x: lng * 10, y: lat * 10 };
      },
      containerPointToLatLng(p) { return { lat: p.y / 10, lng: p.x / 10 }; },
    };
    applyFilmCamera(map, {
      chapterIdx: 0, lastChapterIdx: null, lat: 46, lon: -1, heading: 90, zoom: 5, now: 0,
    });
    let lastCenter = [46, -1];
    let framesSinceReset = 0;
    for (let i = 1; i <= 12; i++) {
      const next = applyFilmCamera(map, {
        chapterIdx: 0, lastChapterIdx: 0, lat: 46, lon: -1 + i * 0.05, heading: 90, zoom: 5,
        now: i * 16, lastCenter, framesSinceReset, boatPx: 5,
      });
      lastCenter = next.lastCenter;
      framesSinceReset = next.framesSinceReset;
    }
    const views = calls.filter((c) => c === "setView").length;
    const pans = calls.filter((c) => c === "panBy").length;
    assert.ok(pans >= 6, `panBy ${pans}`);
    assert.ok(views <= 3, `setView trop fréquent : ${views}`);
    assert.equal(calls.filter((c) => c === "flyTo").length, 0);
  });

  it("lisse le cap sur la jambe, pas le cap instantané", () => {
    const samples = [];
    pushFilmSample(samples, { t: 0, lat: 46, lon: -1, heading: 80, chapterIdx: 0 });
    pushFilmSample(samples, { t: 80, lat: 46, lon: -0.8, heading: 90, chapterIdx: 0 });
    pushFilmSample(samples, { t: 160, lat: 46, lon: -0.6, heading: 100, chapterIdx: 0 });
    const h = smoothFilmHeading(samples, 160);
    assert.ok(Math.abs(h - 90) < 8, `cap lissé ${h} trop près de l'instantané 160`);
    assert.ok(h > 80 && h < 120);
  });

  it("resserre le zoom à l'approche et l'élargit au départ", () => {
    const mid = filmApproachZoom(5, 0.5);
    const start = filmApproachZoom(5, 0);
    const end = filmApproachZoom(5, 1);
    assert.ok(start < mid, `départ ${start} n'est pas plus large que ${mid}`);
    assert.ok(end > mid, `approche ${end} n'est pas plus serrée que ${mid}`);
    assert.equal(mid, 5);
  });

  it("keepBoatInFrame ramène un bateau trop loin du centre", () => {
    const map = {
      getSize() { return { x: 1000, y: 800 }; },
      latLngToContainerPoint(ll) {
        const lat = Array.isArray(ll) ? ll[0] : ll.lat;
        const lng = Array.isArray(ll) ? ll[1] : ll.lng;
        return { x: 500 + lng * 20, y: 400 - lat };
      },
      containerPointToLatLng(p) { return { lat: 400 - p.y, lng: (p.x - 500) / 20 }; },
    };
    const kept = keepBoatInFrame([0, 0], [0, 20], map);
    const boat = map.latLngToContainerPoint([0, 20]);
    const center = map.latLngToContainerPoint(kept);
    const dx = Math.abs(boat.x - center.x);
    assert.ok(dx <= 1000 * FILM_BOAT_KEEP_FRAC * 0.5 + 1, `bateau à ${dx} px du centre`);
  });

  it("MapSceneController : sillage à la frame et bateau posé pendant le film", () => {
    assert.match(controller, /this\.renderDynamic\(this\.currentPlayback \|\| this\.playback\.snapshot\(\)\)/);
    assert.match(controller, /zoomAnimating && markers\.length && !this\.config\.filmActive/);
    assert.match(controller, /filmActive: this\.config\.filmActive/);
    assert.match(controller, /filmFramesSinceReset/);
  });
});
