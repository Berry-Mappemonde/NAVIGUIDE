import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  atlanticSpanNm,
  chapterAtNm,
  filmLegContext,
  flattenRoute,
  interpolateAtNm,
  isNamedEscale,
  mapEscalesOnRoute,
  nearestNm,
  nextEscaleNm,
  prevEscaleNm,
} from "./routePlayhead.js";

const SEGMENTS = [
  { nonMaritime: true, coords: [[0, 0], [0, 1]] },
  { nonMaritime: false, coords: [[0, 1], [1, 1], [2, 1]] },
];

describe("flattenRoute", () => {
  it("commence au premier vertex et cumule les nm", () => {
    const flat = flattenRoute(SEGMENTS);
    assert.equal(flat.points[0].lat, 0);
    assert.equal(flat.points[0].lon, 0);
    assert.ok(flat.totalNm > 60);
    assert.equal(flat.points[0].nonMaritime, true);
  });
});

describe("interpolateAtNm / nearestNm", () => {
  it("revient au départ à 0 et à l’arrivée au total", () => {
    const flat = flattenRoute(SEGMENTS);
    const a = interpolateAtNm(flat, 0);
    const b = interpolateAtNm(flat, flat.totalNm);
    assert.equal(a.lat, 0);
    assert.ok(Math.abs(b.lon - 2) < 1e-6);
    const mid = interpolateAtNm(flat, flat.totalNm / 2);
    const back = nearestNm(flat, mid.lat, mid.lon);
    assert.ok(Math.abs(back - flat.totalNm / 2) < 2);
  });
});

describe("escales", () => {
  it("ignore les points sans drapeau et avance dans l’ordre", () => {
    assert.equal(isNamedEscale({ flag: "" }), false);
    assert.equal(isNamedEscale({ flag: "/x.png" }), true);
    const flat = flattenRoute(SEGMENTS);
    const marks = mapEscalesOnRoute([
      { name: "A", lat: 0, lon: 0, flag: "f" },
      { name: "skip", lat: 0.5, lon: 0, flag: "" },
      { name: "B", lat: 1, lon: 2, flag: "f" },
    ], flat);
    assert.equal(marks.length, 2);
    assert.equal(marks[0].name, "A");
    assert.ok(marks[1].nm > marks[0].nm);
    const ch = chapterAtNm(marks, marks[0].nm + 1);
    assert.equal(ch.from.name, "A");
    assert.equal(ch.to.name, "B");
    assert.equal(nextEscaleNm(marks, 0), marks[1].nm);
    assert.equal(prevEscaleNm(marks, marks[1].nm), marks[0].nm);
  });
});

describe("atlanticSpanNm", () => {
  it("prend La Rochelle → Fort-de-France", () => {
    const span = atlanticSpanNm([
      { name: "La Rochelle", nm: 100 },
      { name: "Ajaccio (Corse)", nm: 2000 },
      { name: "Fort-de-France (Martinique)", nm: 7100 },
    ], 39000);
    assert.equal(span, 7000);
  });
});

describe("filmLegContext", () => {
  it("garde les noms complets et calcule l’ETA avec la vitesse du bateau", () => {
    const marks = [
      { name: "Saint-Maur (Berry, Indre)", nm: 0 },
      { name: "La Rochelle", nm: 200 },
    ];
    const hud = filmLegContext({
      marks,
      nm: 50,
      sample: { lon: 1, lat: 46, bearing: 270 },
      totalNm: 200,
      boatKnots: 10,
    });
    assert.equal(hud.fromStop, "Saint-Maur (Berry, Indre)");
    assert.equal(hud.toStop, "La Rochelle");
    assert.equal(hud.nmCovered, 50);
    assert.equal(hud.nmRemainingToStop, 150);
    assert.equal(hud.etaHours, 15);
    assert.equal(hud.finished, false);
    assert.deepEqual(hud.snappedPosition, [1, 46]);
  });
});
