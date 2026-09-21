import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { TILE_ATTRIBUTION } from "./styles.js";

describe("TILE_ATTRIBUTION", () => {
  it("crédite Esri une fois comme lien et quatre ancres (HERE, Garmin, OSM)", () => {
    const anchors = [...TILE_ATTRIBUTION.matchAll(/<a\b[^>]*>([^<]*)<\/a>/g)];
    assert.equal(anchors.length, 4);
    assert.deepEqual(anchors.map((m) => m[1]), [
      "Esri",
      "HERE",
      "Garmin",
      "OpenStreetMap contributors",
    ]);
    const esriAsLink = anchors.filter((m) => m[1] === "Esri");
    assert.equal(esriAsLink.length, 1);
    assert.match(TILE_ATTRIBUTION, /Tuiles/);
    assert.match(TILE_ATTRIBUTION, /données Esri/);
    assert.match(esriAsLink[0][0], /href="https:\/\/www\.esri\.com\/"/);
    assert.match(TILE_ATTRIBUTION, /href="https:\/\/www\.here\.com\/"/);
    assert.match(TILE_ATTRIBUTION, /href="https:\/\/www\.garmin\.com\/"/);
    assert.match(TILE_ATTRIBUTION, /href="https:\/\/www\.openstreetmap\.org\/copyright"/);
  });
});
