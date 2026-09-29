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
    assert.match(source, /const data = await putOfficial\(\)\.catch\(\(\) => null\);/);
    assert.match(source, /if \(!gotClock\) gotClock = Boolean\(await readClock\(\)\);/);
  });

  it("une seule lecture de l’horloge à la fois, relance espacée — jamais une pile de requêtes (29 sept.)", () => {
    // Grok Bot derrière le tunnel : 134 requêtes en 4 min, 50 horloges de 3,9 Mo en vol, bateau au jour 0.
    assert.match(source, /if \(inflightRef\.current\) \{/);
    assert.match(source, /inflightRef\.current = true;/);
    assert.match(source, /inflightRef\.current = false;/);
    assert.doesNotMatch(source, /setInterval\(\(\) => \{\s*if \(!putRef\.current/);
    assert.match(source, /timer = setTimeout\(kick, officialRetryDelayMs\(attemptRef\.current\)\);/);
    // Le PUT porte déjà l'horloge : pas de second téléchargement.
    assert.match(source, /gotClock = Boolean\(data\?\.clock\?\.t0\);/);
  });
});

describe("officialRetryDelayMs", () => {
  it("espace les relances : 5 s, 10, 20, 40, puis 60 s au plus", async () => {
    const { officialRetryDelayMs, OFFICIAL_RETRY_MS } = await import("./useOfficialExpedition.js");
    assert.deepEqual([1, 2, 3, 4, 5, 6, 40].map(officialRetryDelayMs), [5000, 10000, 20000, 40000, 60000, 60000, 60000]);
    assert.equal(officialRetryDelayMs(0), OFFICIAL_RETRY_MS[0]);
    assert.equal(officialRetryDelayMs(undefined), OFFICIAL_RETRY_MS[0]);
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
