import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { buildBerryLegs, isNonMaritimeLeg, orientCoords } from "./berryLegs.js";

describe("berryLegs", () => {
  it("skips Marigot / Halifax and inserts Marigot→Cayenne", () => {
    const pts = [
      { name: "Gustavia (Saint-Barthélemy)", lat: 1, lon: 1 },
      { name: "Marigot (Saint-Martin)", lat: 2, lon: 2 },
      { name: "Cayenne (Guyane)", lat: 3, lon: 3 },
      { name: "Halifax (Nouvelle-Écosse)", lat: 4, lon: 4 },
      { name: "Saint-Pierre (Saint-Pierre-et-Miquelon)", lat: 5, lon: 5 },
      { name: "Papeete (Polynésie française)", lat: 6, lon: 6 },
    ];
    const legs = buildBerryLegs(pts);
    const keys = legs.map((l) => `${l.from.name}|${l.to.name}`);
    assert.ok(keys.includes("Marigot (Saint-Martin)|Cayenne (Guyane)"));
    assert.ok(keys.includes("Cayenne (Guyane)|Papeete (Polynésie française)"));
    assert.ok(!keys.includes("Marigot (Saint-Martin)|Cayenne (Guyane)".replace("Cayenne", "Halifax")));
    assert.ok(!keys.some((k) => k.startsWith("Marigot (Saint-Martin)|Cayenne") === false && k.startsWith("Marigot")));
  });

  it("marque overland Saint-Maur ↔ La Rochelle", () => {
    assert.equal(isNonMaritimeLeg("Saint-Maur (Berry, Indre)", "La Rochelle"), true);
    assert.equal(isNonMaritimeLeg("La Rochelle", "Ajaccio (Corse)"), false);
  });

  it("oriente A→B", () => {
    const from = { lat: 0, lon: 0 };
    const to = { lat: 1, lon: 1 };
    const rev = orientCoords([[1, 1], [0, 0]], from, to);
    assert.deepEqual(rev[0], [0, 0]);
  });
});
