import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { nearestAlongside, pickAutoEscaleStop } from "./escaleSheetPick.js";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "useEscaleSheetState.js"), "utf8");

const SAINT_MAUR = { name: "Saint-Maur (Berry, Indre)", lat: 46.8075, lon: 1.6358 };
const LA_ROCHELLE = { name: "La Rochelle", lat: 46.1541, lon: -1.167 };
const AJACCIO = { name: "Ajaccio", lat: 41.9267, lon: 8.7378 };
const FORT_DE_FRANCE = { name: "Fort-de-France (Martinique)", lat: 14.5887, lon: -61.0731 };
const MARKS = [SAINT_MAUR, LA_ROCHELLE, AJACCIO, FORT_DE_FRANCE];

const alongside = {
  isSuivre: true,
  atQuay: true,
  clockSample: { lat: FORT_DE_FRANCE.lat, lon: FORT_DE_FRANCE.lon },
  marks: MARKS,
};

describe("useEscaleSheetState — KO #309 Fort-de-France (lot RE2)", () => {
  it("à quai à Fort-de-France, nearestAlongside rend Fort-de-France, pas Saint-Maur", () => {
    const best = nearestAlongside(alongside.clockSample, MARKS);
    assert.equal(best?.name, FORT_DE_FRANCE.name);
    assert.notEqual(best?.name, SAINT_MAUR.name);
    assert.notEqual(best?.name, LA_ROCHELLE.name);
  });

  it("repro : après un clic-liste, l'horloge restée à quai ouvre Fort-de-France (le troisième nom)", () => {
    // handleSidebarSeek (App.jsx) pose userPreview + seek ; le curseur
    // reste sur la jambe live (KO bot #309). clockSample reste à quai à
    // Fort-de-France. Sans garde userPicked, l'auto-fiche ouvre ce nom-là
    // — pas Saint-Maur / La Rochelle / Ajaccio cliqués.
    const leaked = pickAutoEscaleStop(alongside);
    assert.equal(leaked?.name, FORT_DE_FRANCE.name);
    assert.notEqual(leaked?.name, SAINT_MAUR.name);
    assert.notEqual(leaked?.name, AJACCIO.name);
  });

  it("une fiche désignée (drapeau) n'est jamais remplacée par Fort-de-France", () => {
    const kept = pickAutoEscaleStop({ ...alongside, userPicked: true });
    assert.equal(kept, null);
  });

  it("la fiche auto ne s'ouvre que pour l'escale à quai la plus proche", () => {
    assert.equal(pickAutoEscaleStop({ ...alongside, isSuivre: false })?.name, undefined);
    assert.equal(pickAutoEscaleStop({ ...alongside, atQuay: false })?.name, undefined);
    assert.equal(pickAutoEscaleStop({ ...alongside, hold: true })?.name, undefined);
    assert.equal(pickAutoEscaleStop({ ...alongside, filmActive: true })?.name, undefined);
    const atAjaccio = pickAutoEscaleStop({
      ...alongside,
      clockSample: { lat: AJACCIO.lat, lon: AJACCIO.lon },
    });
    assert.equal(atAjaccio?.name, AJACCIO.name);
  });

  it("open() pose userPickedRef ; l'effet passe par pickAutoEscaleStop", () => {
    assert.match(src, /userPickedRef\.current = true/);
    assert.match(src, /pickAutoEscaleStop\(/);
    assert.match(src, /userPicked: userPickedRef\.current/);
  });
});
