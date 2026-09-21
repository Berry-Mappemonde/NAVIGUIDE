import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "useVirtualVessel.js"), "utf8");
const dialog = readFileSync(join(here, "..", "components", "RecomputeDialog.jsx"), "utf8");

describe("useVirtualVessel — explication de recalcul (lot L5)", () => {
  it("expose route-advice-text depuis draft.advice, sans chiffre inventé côté client", () => {
    assert.match(src, /export function RouteAdviceText/);
    assert.match(src, /data-testid": "route-advice-text"/);
    assert.match(src, /draft\?\.advice\?\.text/);
    assert.doesNotMatch(src, /Nemotron|Tavily|99 kn/);
    assert.match(dialog, /<RouteAdviceText draft=\{draft\} \/>/);
  });

  it("poste toujours les contraintes skipper au recalcul", () => {
    assert.match(src, /body\.wind_max_kt = constraints\.windMaxKt/);
    assert.match(src, /body\.hs_max_m = constraints\.hsMaxM/);
  });
});
