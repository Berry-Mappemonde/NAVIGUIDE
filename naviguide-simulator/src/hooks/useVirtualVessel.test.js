import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "useVirtualVessel.js"), "utf8");
const dialog = readFileSync(join(here, "..", "components", "RecomputeDialog.jsx"), "utf8");

describe("useVirtualVessel — explication de recalcul (lot L5)", () => {
  it("espace les re-créations après un échec (lot RF3)", () => {
    assert.match(src, /export function createBackoffMs/);
    assert.match(src, /\[2000, 4000, 8000, 16000, 30000\]/);
    assert.match(src, /failCountRef/);
    assert.match(src, /nextCreateAtRef/);
    assert.match(src, /createBackoffMs\(failCountRef\.current\)/);
    assert.match(src, /if \(wait > 0\)/);
  });

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

describe("createBackoffMs — repli progressif (lot RF3)", () => {
  function createBackoffMs(failCount) {
    const n = Number(failCount);
    if (!Number.isFinite(n) || n <= 0) return 0;
    const steps = [2000, 4000, 8000, 16000, 30000];
    const i = Math.min(steps.length, Math.floor(n)) - 1;
    return steps[i];
  }

  it("double jusqu'à 30 s, zéro si aucun échec — même suite que le hook", () => {
    assert.match(src, /\[2000, 4000, 8000, 16000, 30000\]/);
    assert.equal(createBackoffMs(0), 0);
    assert.equal(createBackoffMs(1), 2000);
    assert.equal(createBackoffMs(2), 4000);
    assert.equal(createBackoffMs(5), 30000);
    assert.equal(createBackoffMs(9), 30000);
  });
});
