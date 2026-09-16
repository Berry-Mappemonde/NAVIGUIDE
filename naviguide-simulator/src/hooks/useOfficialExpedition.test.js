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
  it("attend et emploie l’horloge serveur, jamais l’horloge cliente mutable", () => {
    assert.match(source, /const liveClock = serverClock;/);
    assert.match(source, /if \(!enabled \|\| !liveClock\) return null;/);
    assert.doesNotMatch(source, /clock \|\| serverClock/);
    assert.match(
      source,
      /serverClock\s*&&\s*sampleClockAtTime\(serverClock, new Date\(nowMs\)\)\?\.lat != null/,
    );
  });
});
