import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { ALL_LAYER_CONFIG } from "./layers.js";

describe("ALL_LAYER_CONFIG", () => {
  it("expose les 13 pastilles du cockpit (dont WMS EMODnet)", () => {
    assert.equal(ALL_LAYER_CONFIG.length, 13);
    const keys = ALL_LAYER_CONFIG.map((c) => c.key);
    assert.deepEqual(keys, [
      "zee", "wpi", "balisage", "projects", "marinas",
      "capitaineries", "poe", "amp", "science", "climatology",
      "wmsBathy", "wmsSubstrate", "wmsCables",
    ]);
  });
});
