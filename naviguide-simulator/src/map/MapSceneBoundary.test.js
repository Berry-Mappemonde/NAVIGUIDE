import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (file) => readFileSync(join(here, file), "utf8");

describe("MapScene boundary", () => {
  it("retire les hooks Leaflet et le playhead de App", () => {
    const app = read("../App.jsx");
    assert.match(app, /<MapScene/);
    assert.doesNotMatch(app, /useRoutePlayback/);
    assert.doesNotMatch(app, /useWakeLayer/);
    assert.doesNotMatch(app, /useSimulatorMap/);
    assert.doesNotMatch(app, /useFilmCamera/);
  });

  it("garde les objets Leaflet dans un contrôleur add/update/remove", () => {
    const controller = read("./MapSceneController.js");
    const playback = read("./ScenePlaybackController.js");
    assert.match(controller, /SceneLayerRegistry/);
    assert.match(controller, /renderDynamic/);
    assert.match(controller, /syncWake/);
    assert.match(controller, /syncMarkers/);
    assert.match(playback, /SCENE_INTERVAL_MS = 125/);
    assert.match(playback, /HUD_INTERVAL_MS = 250/);
    assert.match(playback, /onFrame/);
    assert.match(playback, /onPublish/);
  });

  it("borne la latitude à ±85 et la longitude à ±540 (une copie de chaque côté)", () => {
    const src = read("./MapSceneController.js");
    const start = src.indexOf("static mount");
    const end = src.indexOf("constructor(map");
    assert.ok(start >= 0 && end > start, "bloc mount() introuvable");
    const mount = src.slice(start, end);
    assert.match(mount, /minZoom:\s*2/);
    assert.match(mount, /worldCopyJump:\s*false/);
    assert.match(mount, /maxBoundsViscosity:\s*1/);
    assert.match(src, /MAP_LON_BOUND = 540/);
    assert.match(src, /MAP_LAT_BOUND = 85/);
    assert.match(mount, /maxBounds:\s*MAP_MAX_BOUNDS/);
    assert.doesNotMatch(mount, /-Infinity/);
    assert.doesNotMatch(mount, /Infinity/);
  });

  it("désactive le zoom haut-gauche et le pose en bas à droite (lot RB2)", () => {
    const src = read("./MapSceneController.js");
    const start = src.indexOf("static mount");
    const end = src.indexOf("constructor(map");
    assert.ok(start >= 0 && end > start, "bloc mount() introuvable");
    const mount = src.slice(start, end);
    assert.match(mount, /zoomControl:\s*false/);
    assert.match(mount, /L\.control\.zoom\(\{\s*position:\s*"bottomright"\s*\}\)/);
    const css = read("../index.css");
    assert.match(css, /\.leaflet-control-zoom/);
    assert.match(css, /flex-direction:\s*row/);
    assert.match(css, /\.leaflet-bottom\.leaflet-right \.leaflet-control/);
  });

  it("trace une jambe air en dash noir non interactif", () => {
    const src = read("./MapSceneController.js");
    assert.match(src, /officialRouteLineStyle/);
    assert.match(src, /interactive,\s*$/m);
    assert.match(src, /pts\[i \+ 1\]\.jump/);
    const styleSrc = read("../utils/berryLegs.js");
    assert.match(styleSrc, /color: "#111111"/);
    assert.match(styleSrc, /dash: "7 7"/);
    assert.match(styleSrc, /interactive: false/);
  });
});
