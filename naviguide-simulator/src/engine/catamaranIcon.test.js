import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { catamaranTransform } from "./catamaranIcon.js";

describe("catamaranTransform", () => {
  it("stays upright (no scaleY) regardless of heading", () => {
    for (const b of [0, 90, 180, 270, 45]) {
      const t = catamaranTransform(b);
      assert.equal(t.includes("scaleY"), false);
      assert.ok(t.includes("rotate"));
    }
  });

  it("points the bow east without mirroring", () => {
    assert.equal(catamaranTransform(90), "rotate(0deg)");
  });
});
