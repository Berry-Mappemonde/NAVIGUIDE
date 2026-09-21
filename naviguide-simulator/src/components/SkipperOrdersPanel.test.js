import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  BOAT_FIELDS,
  DEFAULT_BOAT,
  DEFAULT_PROFILE,
  resolveOrders,
} from "../engine/skipperOrders.js";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "SkipperOrdersPanel.jsx"), "utf8");

/**
 * Même contrat que `resetNumberToProfile` exporté du panneau (fichier JSX,
 * non importable par node --test) : valeur du profil, forced faux.
 */
function resetNumberToProfile(id, profile = DEFAULT_PROFILE) {
  const orders = resolveOrders({ profile });
  const value = id in BOAT_FIELDS ? orders.boat[id] : orders.values[id];
  return { value, forced: false };
}

describe("SkipperOrdersPanel — remise d’un chiffre (lot R1)", () => {
  it("exporte resetNumberToProfile et câble onReset sur loa, draft et chaque chiffre", () => {
    assert.match(src, /export function resetNumberToProfile/);
    assert.match(src, /onChange\?\.\(id, null\)/);
    assert.match(src, /id="loaM"[\s\S]*?onReset=\{\(fieldId\) => onBoat\?\.\(fieldId, null\)\}/);
    assert.match(src, /id="draftM"[\s\S]*?onReset=\{\(fieldId\) => onBoat\?\.\(fieldId, null\)\}/);
    assert.equal((src.match(/onReset=\{\(fieldId\) => onExpert\?\.\(fieldId, null\)\}/g) || []).length, 2);
    assert.doesNotMatch(src, /skipperExpertHint/);
  });

  it("après remise, la valeur est celle du profil et forced est faux", () => {
    const profile = "cruise";
    const id = "galePct";
    const forced = resolveOrders({ profile, expert: { [id]: 40 } });
    assert.equal(forced.values[id], 40);
    assert.equal(id in forced.expert, true);

    const after = resolveOrders({ profile, expert: {} });
    const expected = resetNumberToProfile(id, profile);
    assert.equal(after.values[id], expected.value);
    assert.equal(expected.value, 15);
    assert.equal(expected.forced, false);
    assert.equal(id in after.expert, false);

    const coastalRain = resetNumberToProfile("rainMmH", "coastal");
    assert.equal(coastalRain.value, 3);
    assert.equal(coastalRain.forced, false);
    const oceanRain = resetNumberToProfile("rainMmH", "ocean");
    assert.equal(oceanRain.value, 6);
  });

  it("après remise de la longueur, la valeur polar/défaut revient et forced est faux", () => {
    const before = resolveOrders({ profile: "cruise", boat: { loaM: 20 } });
    assert.equal(before.boat.loaM, 20);
    assert.equal(before.boat.source.loa, "skipper");

    const after = resolveOrders({ profile: "cruise", boat: {} });
    const expected = resetNumberToProfile("loaM", "cruise");
    assert.equal(after.boat.loaM, expected.value);
    assert.equal(expected.value, DEFAULT_BOAT.loaM);
    assert.equal(expected.forced, false);
    assert.notEqual(after.boat.source.loa, "skipper");
  });
});
