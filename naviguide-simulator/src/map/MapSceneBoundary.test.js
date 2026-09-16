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
});
