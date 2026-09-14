import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { boatSpeedFromWind, zoneWindAt } from "./climatologyWind.js";

describe("zoneWindAt", () => {
  it("étiquète climatology", () => {
    const w = zoneWindAt(46.15, -1.16, 6);
    assert.equal(w.kind, "climatology");
    assert.ok(w.speedKnots > 0);
  });

  it("alizés atlantiques : mars plus fort que juillet", () => {
    const mar = zoneWindAt(16, -40, 3);
    const jul = zoneWindAt(16, -40, 7);
    assert.ok(mar.speedKnots > jul.speedKnots);
  });
});

describe("boatSpeedFromWind", () => {
  it("borne 4–11 kn", () => {
    assert.equal(boatSpeedFromWind(0), 4);
    assert.equal(boatSpeedFromWind(40), 11);
  });
});
