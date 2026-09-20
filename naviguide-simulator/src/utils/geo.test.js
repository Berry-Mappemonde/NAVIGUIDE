import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { flattenRoute, mapEscalesOnRoute } from "../engine/routePlayhead.js";
import { mergeEpisodeMarks } from "../engine/filmCast.js";
import { routeFromOfficial } from "./routeFromOfficial.js";
import {
  haversineNm,
  summarizeRoute,
  summarizeLegs,
  marksForSummary,
  featuresToSegments,
  splitAntimeridianCoords,
  unwrapLon,
  unwrapLineCoords,
  unwrapPath,
  wrapLon,
  worldCopyCoords,
  worldCopyLineCoords,
  worldCopyLngs,
  worldCopyParts,
  worldCopyPolygonCoords,
} from "./geo.js";

const OFFICIAL_ESCALES = [
  "Saint-Maur (Berry, Indre)",
  "La Rochelle",
  "Ajaccio (Corse)",
  "Fort-de-France (Martinique)",
  "Pointe-à-Pitre (Guadeloupe)",
  "Gustavia (Saint-Barthélemy)",
  "Marigot (Saint-Martin)",
  "Cayenne (Guyane)",
  "Saint-Pierre (Saint-Pierre-et-Miquelon)",
  "Papeete (Polynésie française)",
  "Mata-Utu (Wallis-et-Futuna)",
  "Nouméa (Nouvelle-Calédonie)",
  "Dzaoudzi (Mayotte)",
  "Tromelin (TAAF)",
  "Saint-Gilles (La Réunion)",
  "Europa (TAAF)",
  "La Rochelle",
];

describe("summarizeRoute", () => {
  it("counts segments and a distance > 0", () => {
    const { nm, segments } = summarizeRoute([
      { coords: [[-1.16, 46.15], [-16.15, 28.55]] },
      { coords: [[-16.15, 28.55], [-23.6, 15.1]] },
    ]);
    assert.equal(segments, 2);
    assert.ok(nm > 1000);
  });

  it("ignores LineStrings that are too short", () => {
    assert.deepEqual(summarizeRoute([{ coords: [[0, 0]] }]), { nm: 0, segments: 0 });
  });
});

describe("summarizeLegs", () => {
  const landSeg = {
    coords: [[1.6358, 46.8075], [-1.167, 46.1541]],
    nonMaritime: true,
    from: { name: "Saint-Maur (Berry, Indre)" },
    to: { name: "La Rochelle" },
  };
  const seaSeg = {
    coords: [[-1.167, 46.1541], [8.7386, 41.9192]],
    nonMaritime: false,
    from: { name: "La Rochelle" },
    to: { name: "Ajaccio (Corse)" },
  };

  it("17 marques → 16 étapes, Saint-Maur → La Rochelle à terre", () => {
    const marks = OFFICIAL_ESCALES.map((name) => ({ name }));
    const out = summarizeLegs(marks, [landSeg, seaSeg]);
    assert.equal(out.legs, 16);
    assert.equal(out.escales, 17);
    assert.equal(out.land, 1);
    assert.equal(out.sea, 15);
  });

  it("route dessinée sans marques → 1 étape", () => {
    const out = summarizeLegs([], [{ coords: [[0, 0], [1, 1]], nonMaritime: false }]);
    assert.equal(out.legs, 1);
    assert.equal(out.sea, 1);
    assert.equal(out.land, 0);
    assert.equal(out.escales, 0);
  });

  it("Cayenne réinséré (HUD aérien) ne crée pas d'escale de plus", () => {
    const marks = [
      ...OFFICIAL_ESCALES.slice(0, 9).map((name) => ({ name })),
      { name: "Cayenne (Guyane)" },
      ...OFFICIAL_ESCALES.slice(9).map((name) => ({ name })),
    ];
    assert.equal(marks.length, 18);
    assert.equal(marksForSummary(marks).length, 17);
    const out = summarizeLegs(marks, [landSeg]);
    assert.equal(out.escales, 17);
    assert.equal(out.legs, 16);
  });

  it("route officielle Berry : 16 étapes (15 mer, 1 terre), 17 escales, 1248 sommets", () => {
    const raw = JSON.parse(readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), "../../public/route.geojson"),
      "utf8",
    ));
    const { segments, stops } = routeFromOfficial(raw);
    const flat = flattenRoute(segments);
    const marks = mergeEpisodeMarks(mapEscalesOnRoute(stops, flat), flat, stops);
    const out = summarizeLegs(marks, segments);
    assert.equal(out.legs, 16);
    assert.equal(out.sea, 15);
    assert.equal(out.land, 1);
    assert.equal(out.escales, 17);
    assert.equal(out.points, 1248);
    assert.equal(out.waypoints, 36);
  });
});

describe("wrapLon / unwrapPath (lot S)", () => {
  it("replie 236,84° (SF dépliée) dans [−180, 180]", () => {
    assert.equal(Number(wrapLon(236.84).toFixed(2)), -123.16);
    assert.ok(wrapLon(236.84) >= -180 && wrapLon(236.84) <= 180);
    assert.equal(wrapLon(-122.4), -122.4);
  });

  it("unwrapPath reste continu depuis Brisbane", () => {
    const path = unwrapPath(
      [[153.4, -27], [179, 0], [-179, 10], [-122.4, 37.7]],
      153.4,
    );
    const lons = path.map(([lon]) => lon);
    for (let i = 1; i < lons.length; i++) {
      assert.ok(Math.abs(lons[i] - lons[i - 1]) <= 180);
    }
    assert.ok(lons[lons.length - 1] > 180);
    assert.ok(path.every(([, lat]) => lat <= 50));
  });
});

describe("antimeridian geo", () => {
  it("measures the short path on both sides of 180°", () => {
    const d = haversineNm(-15, 179.5, -15, -179.5);
    assert.ok(d < 80);
    assert.ok(d > 20);
    assert.equal(unwrapLon(179.5, -179.5), 180.5);
  });

  it("splits a polyline at 180°", () => {
    const parts = splitAntimeridianCoords([[179, 0], [179.9, 0], [-179.9, 0], [-179, 0]]);
    assert.equal(parts.length, 2);
  });

  it("copies a track at ±360° so Africa stays visible from the Pacific", () => {
    const copies = worldCopyCoords([[166, -22], [45, -13]]);
    assert.equal(copies.length, 3);
    assert.equal(copies[1][0][0], 526);
    assert.equal(copies[2][0][0], -194);
    assert.equal(worldCopyParts(copies.slice(0, 1)).length, 3);
  });

  it("déplie et triple les lignes, y compris 179° → −179°", () => {
    const unwrapped = unwrapLineCoords([[170, -15], [179, -16], [-179, -17], [-170, -18]]);
    assert.deepEqual(unwrapped.map(([lon]) => lon), [170, 179, 181, 190]);
    const copies = worldCopyLineCoords(unwrapped);
    assert.equal(copies.length, 3);
    assert.deepEqual(copies[2].map(([lon]) => lon), [-190, -181, -179, -170]);
    copies.forEach((line) => {
      line.slice(1).forEach(([lon], index) => {
        assert.ok(Math.abs(lon - line[index][0]) <= 180);
      });
    });
  });

  it("triple les points et conserve les anneaux d’un polygone Pacifique", () => {
    assert.deepEqual(worldCopyLngs(179), [179, 539, -181]);
    const copies = worldCopyPolygonCoords([[
      [170, -10], [-170, -10], [-170, 10], [170, 10], [170, -10],
    ]]);
    assert.equal(copies.length, 3);
    assert.deepEqual(copies[0][0].map(([lon]) => lon), [170, 190, 190, 170, 170]);
    assert.deepEqual(copies[1][0].map(([lon]) => lon), [530, 550, 550, 530, 530]);
  });
});

describe("featuresToSegments", () => {
  it("extracts LineStrings from a FeatureCollection", () => {
    const segs = featuresToSegments({
      type: "FeatureCollection",
      features: [
        { type: "Feature", geometry: { type: "Point", coordinates: [0, 0] } },
        { type: "Feature", geometry: { type: "LineString", coordinates: [[0, 0], [1, 1]] } },
      ],
    });
    assert.equal(segs.length, 1);
    assert.equal(haversineNm(0, 0, 1, 1) > 0, true);
  });
});
