import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { ScenePlaybackController } from "./ScenePlaybackController.js";

const flat = {
  totalNm: 100,
  totalFilmNm: 100,
  points: [
    { lat: 0, lon: 0, cumNm: 0, filmCum: 0 },
    { lat: 1, lon: 1, cumNm: 100, filmCum: 100 },
  ],
};

describe("ScenePlaybackController", () => {
  it("garde le playhead hors de React et publie immédiatement les commandes", () => {
    const frames = [];
    const publications = [];
    const controller = new ScenePlaybackController({
      onFrame: (snapshot) => frames.push(snapshot),
      onPublish: (snapshot) => publications.push(snapshot),
      requestFrame: () => 1,
      cancelFrame: () => {},
    });

    controller.configure({ flat, marks: [], boatKnots: 8, enabled: true, stopAuto: false });
    controller.seek(42, { jump: true });
    controller.setProfile("fast");

    assert.equal(controller.snapshot().nm, 42);
    assert.equal(controller.snapshot().profile, "fast");
    assert.equal(controller.snapshot().jumpToken, 1);
    assert.ok(frames.length >= 3);
    assert.ok(publications.length >= 3);
    controller.destroy();
  });

  it("borne le seek et arrête la lecture", () => {
    const controller = new ScenePlaybackController({
      requestFrame: () => 1,
      cancelFrame: () => {},
    });
    controller.configure({ flat, marks: [], boatKnots: 8, enabled: true, stopAuto: false });
    controller.seek(999);
    controller.play();
    controller.pause();

    assert.equal(controller.snapshot().nm, 100);
    assert.equal(controller.snapshot().playing, false);
    controller.destroy();
  });
});
