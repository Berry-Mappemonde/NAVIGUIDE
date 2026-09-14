import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { catamaranTransform } from "./catamaranIcon.js";

describe("catamaranTransform", () => {
  it("reste à l’endroit (pas de scaleY) quel que soit le cap", () => {
    for (const b of [0, 90, 180, 270, 45]) {
      const t = catamaranTransform(b);
      assert.equal(t.includes("scaleY"), false);
      assert.ok(t.includes("rotate"));
    }
  });

  it("oriente l’étrave vers l’est sans miroir", () => {
    assert.equal(catamaranTransform(90), "rotate(0deg)");
  });
});
