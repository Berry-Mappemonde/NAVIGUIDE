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
  it("préfère l’horloge serveur et ne peint pas le cache client en attendant", () => {
    assert.match(source, /if \(serverClock\) \{/);
    assert.match(source, /if \(clockStatus !== "absent"\) return null;/);
    assert.match(source, /pickOfficialLiveClock\(null, officialClient, frozenClientRef\.current\)/);
    assert.match(source, /if \(!enabled \|\| !liveClock\) return null;/);
    assert.doesNotMatch(source, /clock \|\| serverClock/);
    assert.match(
      source,
      /liveClock\s*&&\s*sampleClockAtTime\(liveClock, new Date\(nowMs\)\)\?\.lat != null/,
    );
  });

  it("ne fige jamais une horloge de Simulation (t0 = aujourd’hui) comme position officielle", () => {
    // Régression du 18 sept. : le bateau restait à Saint-Maur au jour 0 en Suivre.
    assert.match(source, /const officialClient = isOfficialClock\(clock\) \? clock : null;/);
    assert.match(source, /if \(!enabled\) \{\s*frozenClientRef\.current = null;\s*return null;/);
  });

  it("lit l’horloge serveur même quand le PUT officiel est refusé", () => {
    assert.match(source, /putOfficial\(\)\s*\.catch\(\(\) => null\)\s*\.then\(\(\) => \{ if \(!cancelled\) return readClock\(\);/);
    assert.match(source, /if \(!putRef\.current \|\| !serverClockRef\.current\) kick\(\);/);
  });
});

describe("isOfficialClock", () => {
  it("reconnaît le t0 fixe de l’expédition, avec ou sans millisecondes", async () => {
    const { isOfficialClock } = await import("./useOfficialExpedition.js");
    assert.equal(isOfficialClock({ t0: "2026-05-15T08:00:00.000Z" }), true);
    assert.equal(isOfficialClock({ t0: "2026-05-15T08:00:00Z" }), true);
    assert.equal(isOfficialClock({ t0: "2026-09-19T08:00:00.000Z" }), false);
    assert.equal(isOfficialClock(null), false);
    assert.equal(isOfficialClock({}), false);
  });
});
