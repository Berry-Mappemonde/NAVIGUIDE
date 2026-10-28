import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (name) => readFileSync(join(here, name), "utf8");
const PALETTE = /\b(?:bg|text|border|ring|from|to|via|divide|placeholder|decoration)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|white|black)(?:-\d{2,3})?\b/;

describe("components on the semantic tokens", () => {
  for (const name of ["EtapePanel.jsx", "EventBubble.jsx", "LogbookChat.jsx"]) {
    it(`${name} uses no palette class, so the themes reach it without .light-mode overrides`, () => {
      const hit = read(name).match(PALETTE);
      assert.equal(hit, null, hit ? `found ${hit[0]}` : "");
    });
  }

  it("bubble links keep the important modifier, which beats Leaflet's unlayered link colour", () => {
    assert.match(read("EventBubble.jsx"), /text-accent-text! hover:text-text-primary!/);
  });
});
