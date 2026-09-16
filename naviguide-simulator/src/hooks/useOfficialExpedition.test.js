import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it } from "node:test";
import assert from "node:assert/strict";

const source = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "useOfficialExpedition.js"),
  "utf8",
);

describe("useOfficialExpedition — position officielle", () => {
  it("préfère l’horloge serveur et fige le premier snapshot client", () => {
    assert.match(source, /pickOfficialLiveClock\(serverClock, clock, frozenClientRef\.current\)/);
    assert.match(source, /if \(!enabled \|\| !liveClock\) return null;/);
    assert.doesNotMatch(source, /clock \|\| serverClock/);
    assert.match(source, /pickOfficialLiveClock/);
    assert.match(
      source,
      /liveClock\s*&&\s*sampleClockAtTime\(liveClock, new Date\(nowMs\)\)\?\.lat != null/,
    );
  });
});
