import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { wakeParts } from "./filmWake.js";

describe("wakeParts", () => {
  it("cuts before the end and interpolates the last vertex", () => {
    const flat = {
      points: [
        { lon: 0, lat: 0, cumNm: 0, jump: false },
        { lon: 1, lat: 0, cumNm: 60, jump: false },
        { lon: 2, lat: 0, cumNm: 120, jump: false },
      ],
    };
    const parts = wakeParts(flat, 90);
    assert.equal(parts.length, 1);
    assert.equal(parts[0][0][0], 0);
    const last = parts[0][parts[0].length - 1];
    assert.ok(last[0] > 1 && last[0] < 2);
  });

  it("breaks the wake at an air hop", () => {
    const flat = {
      points: [
        { lon: -52, lat: 5, cumNm: 0, jump: false },
        { lon: -52.5, lat: 5.1, cumNm: 40, jump: false },
        { lon: -63.5, lat: 44.6, cumNm: 40, jump: true },
        { lon: -64, lat: 44.7, cumNm: 80, jump: false },
      ],
    };
    const parts = wakeParts(flat, 80);
    assert.ok(parts.length >= 2);
    assert.ok(parts.every((p) => p.length >= 2));
  });

  it("stays empty without a route", () => {
    assert.deepEqual(wakeParts({ points: [] }, 10), []);
  });
});
