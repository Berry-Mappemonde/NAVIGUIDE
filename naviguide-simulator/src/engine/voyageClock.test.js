import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  AIR_CALENDAR_HOURS,
  buildVoyageClock,
  findStartIndex,
  sampleClockAtHours,
  sampleClockAtTime,
} from "./voyageClock.js";

const GOLDEN = JSON.parse(readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../../server/tests/fixtures/clock_golden_route.json"),
  "utf8",
));

function clock(t0, extra = {}) {
  return buildVoyageClock({
    points: GOLDEN.points,
    marks: GOLDEN.marks,
    t0,
    polarRaw: null,
    startAt: "la-rochelle",
    ...extra,
  });
}

describe("voyageClock contrat A", () => {
  it("schéma golden : clés de table et de vertex", () => {
    const c = clock("2026-06-15T08:00:00Z");
    for (const key of ["t0", "kind", "vertices", "marks", "seaHours", "quayHours", "arrivalIso"]) {
      assert.ok(key in c, key);
    }
    assert.equal(c.kind, "climatology");
    const v = c.vertices[c.vertices.length - 1];
    for (const key of ["filmNm", "sailNm", "lat", "lon", "bearing", "tHours", "iso", "speedKnots", "windKnots", "twa", "month", "vehicle", "kind"]) {
      assert.ok(key in v, key);
    }
    assert.equal(c.vertices[0].tHours, 0);
    assert.ok(c.vertices.every((x, i, arr) => i === 0 || x.tHours >= arr[i - 1].tHours));
  });

  it("t0 15 juin → Fort-de-France après le 15 juin", () => {
    const c = clock("2026-06-15T08:00:00Z");
    const fdf = c.marks.find((m) => /Fort-de-France/i.test(m.name));
    assert.ok(fdf);
    assert.ok(new Date(fdf.iso) > new Date("2026-06-15T08:00:00Z"));
  });

  it("mars ≠ juillet à Fort-de-France", () => {
    const mar = clock("2026-03-15T08:00:00Z");
    const jul = clock("2026-07-15T08:00:00Z");
    const a = mar.marks.find((m) => /Fort-de-France/i.test(m.name));
    const b = jul.marks.find((m) => /Fort-de-France/i.test(m.name));
    assert.ok(a && b);
    const da = new Date(a.iso).getTime();
    const db = new Date(b.iso).getTime();
    assert.ok(Math.abs(da - db) > 24 * 3600 * 1000, "écart < 1 jour");
  });

  it("quai 2 j : trou de 48 h à filmNm constant", () => {
    const c = clock("2026-06-15T08:00:00Z");
    const fdf = c.marks.find((m) => /Fort-de-France/i.test(m.name));
    assert.equal(fdf.holdHours, 48);
    const same = c.vertices.filter((v) => Math.abs(v.filmNm - fdf.filmNm) < 1e-6);
    assert.ok(same.length >= 2);
    const span = same[same.length - 1].tHours - same[0].tHours;
    assert.ok(span >= 47.9);
  });

  it("hop aérien : +8 h, nœuds nuls", () => {
    const points = [
      { lat: 4.9, lon: -52.3, cumNm: 0, filmCum: 0, jump: false, nonMaritime: false },
      { lat: 44.6, lon: -63.6, cumNm: 0, filmCum: 80, jump: true, nonMaritime: false },
    ];
    const c = buildVoyageClock({
      points,
      marks: [],
      t0: "2026-06-15T08:00:00Z",
      startAt: "saint-maur",
    });
    assert.equal(c.vertices.at(-1).tHours, AIR_CALENDAR_HOURS);
    assert.equal(c.vertices.at(-1).speedKnots, null);
    assert.equal(c.vertices.at(-1).vehicle, "plane");
  });

  it("sans polar : source climatology, pas de crash", () => {
    const c = clock("2026-06-15T08:00:00Z");
    assert.ok(c.vertices.some((v) => v.kind === "climatology" && v.speedKnots > 0));
  });

  it("antiméridien : tHours monotone", () => {
    const points = [
      { lat: -20, lon: 170, cumNm: 0, filmCum: 0, jump: false },
      { lat: -20, lon: 176, cumNm: 300, filmCum: 300, jump: false },
      { lat: -20, lon: -178, cumNm: 600, filmCum: 600, jump: false },
      { lat: -20, lon: -170, cumNm: 900, filmCum: 900, jump: false },
    ];
    const c = buildVoyageClock({
      points,
      marks: [],
      t0: "2026-06-15T08:00:00Z",
      startAt: "saint-maur",
    });
    for (let i = 1; i < c.vertices.length; i++) {
      assert.ok(c.vertices[i].tHours >= c.vertices[i - 1].tHours);
    }
  });

  it("startAt saint-maur : premier dt sans polaire (4 h terre)", () => {
    const points = [
      { lat: 46.8, lon: 1.63, cumNm: 0, filmCum: 0, jump: false, nonMaritime: true },
      { lat: 46.15, lon: -1.16, cumNm: 200, filmCum: 200, jump: false, nonMaritime: true },
      { lat: 45.0, lon: -5.0, cumNm: 400, filmCum: 400, jump: false, nonMaritime: false },
    ];
    const marks = [{ name: "La Rochelle", nm: 200, filmNm: 200, lat: 46.15, lon: -1.16, index: 1 }];
    assert.equal(findStartIndex(points, marks, "saint-maur"), 0);
    const c = buildVoyageClock({
      points,
      marks,
      t0: "2026-06-15T08:00:00Z",
      startAt: "saint-maur",
    });
    const atLr = c.vertices.find((v) => Math.abs(v.sailNm - 200) < 1e-6 && v.vehicle !== "quay");
    assert.ok(atLr);
    assert.equal(atLr.tHours, 4);
  });

  it("sampleClockAtTime avant t0 → waiting", () => {
    const c = clock("2026-06-15T08:00:00Z");
    const s = sampleClockAtTime(c, "2026-06-14T08:00:00Z");
    assert.equal(s.status, "waiting");
    assert.ok(s.countdownHours > 20);
  });

  it("sampleClockAtHours interpolé", () => {
    const c = clock("2026-06-15T08:00:00Z");
    const s = sampleClockAtHours(c, 12);
    assert.ok(s);
    assert.equal(s.status, "live");
    assert.ok(s.lat);
  });
});
