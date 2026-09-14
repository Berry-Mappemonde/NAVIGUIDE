import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { COASTAL_CUTOFF_NM, gebcoLookup } from "./gebco.js";

const GRID = { sample: () => -4200 };

describe("gebcoLookup", () => {
  it("sans grille : null honnête", () => {
    assert.equal(gebcoLookup(0, -30), null);
  });

  it("près des côtes (< 20 M) : null même avec grille", () => {
    assert.equal(gebcoLookup(46.15, -1.16, { grid: GRID, distToShoreNm: 5 }), null);
    assert.ok(COASTAL_CUTOFF_NM === 20);
  });

  it("Atlantique large + grille : une profondeur", () => {
    assert.equal(gebcoLookup(35, -40, { grid: GRID, distToShoreNm: 800 }), -4200);
  });
});
