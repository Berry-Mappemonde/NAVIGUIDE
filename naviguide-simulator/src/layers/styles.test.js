import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { TILE_ATTRIBUTION } from "./styles.js";

describe("TILE_ATTRIBUTION", () => {
  it("crédite Esri une seule fois et quatre ancres (Esri, HERE, Garmin, OSM)", () => {
    const anchors = [...TILE_ATTRIBUTION.matchAll(/<a\b[^>]*>([^<]*)<\/a>/g)];
    assert.equal(anchors.length, 4);
    assert.deepEqual(anchors.map((m) => m[1]), [
      "Esri",
      "HERE",
      "Garmin",
      "OpenStreetMap contributors",
    ]);
    const esriHits = TILE_ATTRIBUTION.match(/Esri/g) || [];
    assert.equal(esriHits.length, 1, "le mot Esri une seule fois dans toute la chaîne");
    assert.match(TILE_ATTRIBUTION, /Tuiles/);
    assert.match(anchors[0][0], /href="https:\/\/www\.esri\.com\/"/);
    assert.match(TILE_ATTRIBUTION, /href="https:\/\/www\.here\.com\/"/);
    assert.match(TILE_ATTRIBUTION, /href="https:\/\/www\.garmin\.com\/"/);
    assert.match(TILE_ATTRIBUTION, /href="https:\/\/www\.openstreetmap\.org\/copyright"/);
  });
});
