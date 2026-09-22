import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  buildBerryLegs,
  isAirLegNames,
  isAirSegment,
  isLandLegNames,
  isNonMaritimeLeg,
  legKind,
  nmToRoundedKm,
  officialAirRouteStyles,
  officialRouteLineStyle,
  NM_TO_KM,
  orientCoords,
} from "./berryLegs.js";

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
    assert.equal(isLandLegNames("Saint-Maur", "La Rochelle"), true);
    assert.equal(isLandLegNames("La Rochelle", "Ajaccio (Corse)"), false);
    assert.equal(nmToRoundedKm(122), Math.round(122 * NM_TO_KM));
  });

  it("marque avion Cayenne ↔ Saint-Pierre / Halifax", () => {
    assert.equal(isAirLegNames("Cayenne (Guyane)", "Saint-Pierre (Saint-Pierre-et-Miquelon)"), true);
    assert.equal(isAirLegNames("Saint-Pierre (Saint-Pierre-et-Miquelon)", "Cayenne (Guyane)"), true);
    assert.equal(isAirLegNames("Cayenne (Guyane)", "Halifax (Nouvelle-Écosse)"), true);
    assert.equal(isAirLegNames("Halifax (Nouvelle-Écosse)", "Saint-Pierre (Saint-Pierre-et-Miquelon)"), true);
    assert.equal(isAirLegNames("Cayenne (Guyane)", "Papeete (Polynésie française)"), false);
    assert.equal(isAirLegNames("La Rochelle", "Ajaccio (Corse)"), false);
    assert.equal(legKind("Cayenne (Guyane)", "Halifax (Nouvelle-Écosse)"), "air");
    assert.equal(legKind("Saint-Maur", "La Rochelle"), "land");
    assert.equal(legKind("La Rochelle", "Ajaccio (Corse)"), "sea");
    const air = officialRouteLineStyle({
      from: { name: "Cayenne (Guyane)" },
      to: { name: "Saint-Pierre (Saint-Pierre-et-Miquelon)" },
      coords: [[-52.3, 4.9], [-56.2, 46.8]],
    });
    assert.equal(air.color, "#111111");
    assert.equal(air.dash, "7 7");
    assert.equal(air.interactive, false);
    const layered = officialAirRouteStyles({ air: true });
    assert.equal(layered.length, 2);
    assert.equal(layered[0].color, "#e5e7eb");
    assert.equal(layered[1].color, "#111111");
    assert.equal(isAirSegment({ air: true, coords: [[0, 0], [1, 1]] }), true);
    assert.equal(officialRouteLineStyle({ nonMaritime: true })?.color, "orange");
    assert.equal(officialRouteLineStyle({ coords: [[0, 0], [1, 1]] }), null);
  });

  it("oriente A→B", () => {
    const from = { lat: 0, lon: 0 };
    const to = { lat: 1, lon: 1 };
    const rev = orientCoords([[1, 1], [0, 0]], from, to);
    assert.deepEqual(rev[0], [0, 0]);
  });
});
