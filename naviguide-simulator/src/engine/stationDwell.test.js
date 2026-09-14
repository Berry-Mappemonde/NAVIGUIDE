import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { nextStationAfter, stepPlayback, dwellMsForProfile } from "./stationDwell.js";

const stations = [
  { filmNm: 0, name: "Départ", kind: "start" },
  { filmNm: 100, name: "Horta", kind: "waypoint" },
  { filmNm: 250, name: "Halifax", kind: "waypoint" },
];

describe("stationDwell", () => {
  it("ignore le départ à 0 nm", () => {
    assert.equal(nextStationAfter(-1, stations).name, "Horta");
    assert.equal(nextStationAfter(0, stations).name, "Horta");
  });

  it("s’arrête à l’escale et pose un dwell", () => {
    const r = stepPlayback({
      filmNm: 99,
      deltaMs: 1000,
      rate: 2,
      stations,
      maxFilmNm: 400,
      dwellMs: 1800,
    });
    assert.equal(r.filmNm, 100);
    assert.equal(r.dwellMsLeft, 1800);
    assert.equal(r.holding, true);
    assert.equal(r.arrived.name, "Horta");
  });

  it("reste immobile pendant le dwell", () => {
    const r = stepPlayback({
      filmNm: 100,
      dwellMsLeft: 800,
      deltaMs: 300,
      rate: 40,
      stations,
      maxFilmNm: 400,
      dwellMs: 1800,
    });
    assert.equal(r.filmNm, 100);
    assert.equal(r.dwellMsLeft, 500);
    assert.equal(r.holding, true);
  });

  it("reprend après la fin du dwell", () => {
    const r = stepPlayback({
      filmNm: 100,
      dwellMsLeft: 200,
      deltaMs: 500,
      rate: 10,
      stations,
      maxFilmNm: 400,
      dwellMs: 1800,
    });
    assert.equal(r.holding, false);
    assert.ok(r.filmNm > 100);
    assert.equal(r.dwellMsLeft, 0);
  });

  it("jump saute le dwell", () => {
    const r = stepPlayback({
      filmNm: 100,
      dwellMsLeft: 1800,
      deltaMs: 16,
      rate: 10,
      stations,
      maxFilmNm: 400,
      dwellMs: 1800,
      jump: true,
    });
    assert.equal(r.holding, false);
    assert.equal(r.dwellMsLeft, 0);
  });

  it("profil fast = pause plus courte", () => {
    assert.ok(dwellMsForProfile("fast") < dwellMsForProfile("real"));
  });
});
