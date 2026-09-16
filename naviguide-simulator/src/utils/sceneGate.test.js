import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  isSceneReady,
  playheadAligned,
  shouldPlaceInitialCamera,
  shouldResnapCamera,
} from "./sceneGate.js";

describe("playheadAligned", () => {
  it("Simulation : toujours prêt", () => {
    assert.equal(playheadAligned({ isSuivre: false, playbackNm: 0 }), true);
  });

  it("Suivre : faux tant que le playhead n’est pas sur le live", () => {
    assert.equal(playheadAligned({
      isSuivre: true,
      previewing: false,
      playbackNm: 0,
      liveFilmNm: 18400,
    }), false);
    assert.equal(playheadAligned({
      isSuivre: true,
      previewing: false,
      playbackNm: 18401,
      liveFilmNm: 18400,
    }), true);
  });
});

describe("isSceneReady", () => {
  it("attend route + caméra + live aligné en Suivre", () => {
    assert.equal(isSceneReady({
      routeReady: true,
      hasRoute: true,
      cameraPlaced: false,
      playheadReady: true,
      isSuivre: true,
      hasLive: true,
    }), false);
    assert.equal(isSceneReady({
      routeReady: true,
      hasRoute: true,
      cameraPlaced: true,
      playheadReady: false,
      isSuivre: true,
      hasLive: true,
    }), false);
    assert.equal(isSceneReady({
      routeReady: true,
      hasRoute: true,
      cameraPlaced: true,
      playheadReady: true,
      isSuivre: true,
      hasLive: true,
    }), true);
  });

  it("App aligne le playhead sans jump et masque jusqu’à sceneReady", () => {
    const src = readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), "../App.jsx"),
      "utf8",
    );
    assert.match(src, /playback\.seek\(target, \{ jump: false \}\)/);
    assert.match(src, /scene-load-mask/);
    assert.match(src, /isSceneReady/);
    assert.match(src, /shouldPlaceInitialCamera/);
    assert.match(src, /userNavigatedRef\.current = true/);
    assert.match(src, /shouldResnapCamera/);
  });
});

describe("shouldPlaceInitialCamera", () => {
  it("laisse l’utilisateur garder sa vue s’il a déjà navigué", () => {
    assert.equal(shouldPlaceInitialCamera({ userNavigated: false }), true);
    assert.equal(shouldPlaceInitialCamera({ userNavigated: true }), false);
  });
});

describe("shouldResnapCamera", () => {
  it("recadre si le live saute l’antiméridien (70° → −191°)", () => {
    assert.equal(shouldResnapCamera(null, { lat: -22.7, lon: -191.16 }), true);
    assert.equal(shouldResnapCamera({ lat: -19.8, lon: 70.5 }, { lat: -22.7, lon: -191.16 }), true);
    assert.equal(shouldResnapCamera({ lat: -22.76, lon: -191.15 }, { lat: -22.76, lon: -191.16 }), false);
  });
});
