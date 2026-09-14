import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { ICI_RADIUS_NM, emptyDossier, ici } from "./ici.js";

describe("ici stub", () => {
  it("a les clés du sac vide", () => {
    const d = emptyDossier(46.15, -1.16);
    assert.equal(d.version, 1);
    assert.equal(d.radiusNm, ICI_RADIUS_NM);
    assert.equal(d.zee, null);
    assert.deepEqual(d.poe, []);
    assert.equal(d.science, null);
    assert.equal(d.event, null);
    assert.ok(d.nearby.marinas);
  });

  it("prend 0 ou 1 science local, jamais un catalogue", () => {
    const far = ici(46.15, -1.16, {
      scienceFeatures: [{
        type: "Feature",
        geometry: { type: "Point", coordinates: [0, 0] },
        properties: { id: "far", name: "loin", source: "sentinel-pilot" },
      }],
    });
    assert.equal(far.science, null);
    const near = ici(46.15, -1.16, {
      scienceFeatures: [{
        type: "Feature",
        geometry: { type: "LineString", coordinates: [[-1.161, 46.151], [-1.159, 46.149]] },
        properties: { id: "c1", name: "côte", source: "sentinel-pilot", error_m: 8 },
      }],
    });
    assert.equal(near.science.id, "c1");
    assert.equal(near.science.error_m, 8);
  });

  it("n'avale pas une grille polar", () => {
    const d = ici(0, 0, {
      polarMeta: {
        boat_name: "Leopard 46",
        vmg_summary: { 12: { upwind: { vmg: 5 } } },
        grid: new Array(181),
      },
    });
    assert.equal(d.polar.boat, "Leopard 46");
    assert.equal(d.polar.grid, undefined);
    assert.ok(d.polar.vmgHint);
  });
});
