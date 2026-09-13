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
