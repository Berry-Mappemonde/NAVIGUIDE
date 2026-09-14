import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { haversineNm, summarizeRoute, featuresToSegments, splitAntimeridianCoords, unwrapLon } from "./geo.js";

describe("summarizeRoute", () => {
  it("compte les segments et une distance > 0", () => {
    const { nm, segments } = summarizeRoute([
      { coords: [[-1.16, 46.15], [-16.15, 28.55]] },
      { coords: [[-16.15, 28.55], [-23.6, 15.1]] },
    ]);
    assert.equal(segments, 2);
    assert.ok(nm > 1000);
  });

  it("ignore les LineString trop courtes", () => {
    assert.deepEqual(summarizeRoute([{ coords: [[0, 0]] }]), { nm: 0, segments: 0 });
  });
});

describe("antiméridien geo", () => {
  it("mesure le court chemin de part et d’autre du 180°", () => {
    const d = haversineNm(-15, 179.5, -15, -179.5);
    assert.ok(d < 80);
    assert.ok(d > 20);
    assert.equal(unwrapLon(179.5, -179.5), 180.5);
  });

  it("coupe une polyligne au 180°", () => {
    const parts = splitAntimeridianCoords([[179, 0], [179.9, 0], [-179.9, 0], [-179, 0]]);
    assert.equal(parts.length, 2);
  });
});

describe("featuresToSegments", () => {
  it("extrait les LineString d'une FeatureCollection", () => {
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
