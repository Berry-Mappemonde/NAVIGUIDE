import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { catalogSourceCount, isCapitainerieEmpty } from "../layers/catalogSource.js";

const src = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "LayerToggles.jsx"), "utf8");

describe("Capitainerie vide", () => {
  it("ne grise que l'effectif 0 de la source", () => {
    assert.equal(isCapitainerieEmpty(0), true);
    assert.equal(isCapitainerieEmpty(null), false);
    assert.equal(isCapitainerieEmpty(undefined), false);
    assert.equal(isCapitainerieEmpty(4), false);
    assert.equal(catalogSourceCount({ metadata: { total: 0, matched: 0 } }), 0);
    assert.equal(catalogSourceCount({ metadata: { matched: 0 } }), null);
    assert.equal(catalogSourceCount(null), null);
  });

  it("désactive le bouton Capitainerie sans retirer les autres pastilles", () => {
    assert.match(src, /key === "capitaineries" && harbourEmpty/);
    assert.match(src, /disabled=\{empty\}/);
    assert.match(src, /ALL_LAYER_CONFIG\.map/);
  });
});
