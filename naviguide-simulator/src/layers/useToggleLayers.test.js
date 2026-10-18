import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it } from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "useToggleLayers.js"), "utf8");

const GATED = ["setShowBalisage", "setShowBathymetry", "setShowFonds", "setShowCables"];

describe("useToggleLayers — sac de couches stable", () => {
  it("mémorise les setters filtrés pour ne pas republier le sac à chaque rendu", () => {
    // MapScene republie ce sac dans un setState. Une fonction neuve à chaque
    // rendu invalide le useMemo, le setState relance le rendu, et l'onglet
    // meurt en entrant dans Tracer (boucle sans plafond en production).
    for (const name of GATED) {
      assert.match(src, new RegExp(`const ${name} = useCallback\\(`));
      assert.doesNotMatch(src, new RegExp(`const ${name} = gatedSet\\(`));
    }
    const bagAt = src.indexOf("return useMemo(() => ({");
    assert.ok(bagAt > 0, "sac mémoïsé introuvable");
    const bag = src.slice(bagAt);
    for (const name of GATED) {
      assert.match(bag, new RegExp(`${name},`));
    }
  });

  it("garde le refus du bandeau « pas pour la navigation » sur ces quatre couches", () => {
    assert.match(src, /gateRef\.current\?\.onNeed\?\.\(kind\)/);
    assert.match(src, /return v;/);
    for (const kind of ["balisage", "bathymetry", "fonds", "cables"]) {
      assert.match(src, new RegExp(`"${kind}"`));
    }
  });
});
