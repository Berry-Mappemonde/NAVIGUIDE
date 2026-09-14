import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  FALLBACK_EXPEDITION_KNOTS,
  airHopSeconds,
  expeditionBoatKnots,
  nmPerSecond,
  trueWindAngle,
} from "./playSpeeds.js";

describe("expeditionBoatKnots", () => {
  it("averages downwind speed (BS), else VMG, else 7 kt", () => {
    assert.equal(expeditionBoatKnots(null), FALLBACK_EXPEDITION_KNOTS);
    assert.ok(Math.abs(expeditionBoatKnots({
      vmg_summary: { 12: { downwind: { vmg: 8 } }, 16: { downwind: { vmg: 10 } } },
    }) - 9) < 1e-9);
    assert.ok(Math.abs(expeditionBoatKnots({
      vmg_summary: { 12: { downwind: { speed: 8.3, vmg: 7.8 } }, 16: { downwind: { speed: 9.4, vmg: 8.9 } } },
    }) - 8.85) < 1e-9);
  });
});

describe("nmPerSecond", () => {
  it("real = knots / 3600; fast = Atlantic / 20 s", () => {
    assert.ok(Math.abs(nmPerSecond("real", { boatKnots: 7.2, atlanticNm: 3600 }) - 7.2 / 3600) < 1e-9);
    assert.equal(nmPerSecond("fast", { boatKnots: 7, atlanticNm: 3600 }), 180);
    assert.equal(nmPerSecond("read", { boatKnots: 7, atlanticNm: 3600 }), 15);
    assert.ok(Math.abs(nmPerSecond("normal", { boatKnots: 7, atlanticNm: 3600 }) - 3600 / 70) < 1e-9);
    assert.ok(nmPerSecond("read", { boatKnots: 7, atlanticNm: 3600 }) < nmPerSecond("normal", { boatKnots: 7, atlanticNm: 3600 }));
  });
});

describe("airHopSeconds", () => {
  it("stays visible on every profile, longer in real", () => {
    assert.ok(airHopSeconds("real") > airHopSeconds("read"));
    assert.ok(airHopSeconds("read") > airHopSeconds("fast"));
    assert.ok(airHopSeconds("fast") >= 1.5);
  });
});

describe("trueWindAngle", () => {
  it("clamps to 0–180", () => {
    assert.equal(trueWindAngle(90, 90), 0);
    assert.equal(trueWindAngle(0, 180), 180);
    assert.equal(trueWindAngle(10, 350), 20);
  });
});
