import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fr from "./fr.js";
import en from "./en.js";

const KEYS = [
  "skipperOrdersTitle",
  "skipperProfileCoastal",
  "skipperProfileCruise",
  "skipperProfileOcean",
  "skipperSharedClock",
  "skipperBoat",
  "skipperBoatUnknown",
  "skipperLoa",
  "skipperDraft",
  "skipperBerryDefault",
  "skipperPlanningKn",
  "skipperFromPolar",
  "skipperProfileDefault",
  "skipperHorizon",
  "skipperHorizonLeg",
  "skipperGale",
  "skipperRainSuivre",
  "skipperRainSimulation",
  "skipperSuggestCoastal",
  "skipperSuggestYes",
  "skipperSuggestNo",
  "skipperResetBerry",
];

describe("skipper i18n", () => {
  it("has every skipper label in FR and EN", () => {
    for (const k of KEYS) {
      assert.equal(typeof fr[k], "string", `fr.${k}`);
      assert.equal(typeof en[k], "string", `en.${k}`);
      assert.ok(fr[k].length > 0 && en[k].length > 0, k);
    }
  });

  it("tells the shared Suivre truth: the official clock does not change", () => {
    assert.match(fr.skipperSharedClock, /horloge officielle ne change pas/);
    assert.match(fr.skipperSharedClock, /ton skipper/);
    assert.match(en.skipperSharedClock, /official clock does not change/);
    assert.match(en.skipperSharedClock, /your skipper/);
  });

  it("names the characters, never raw event types", () => {
    assert.equal(fr.skipperProfileCoastal, "Côtier");
    assert.equal(fr.skipperProfileCruise, "Croisière");
    assert.equal(fr.skipperProfileOcean, "Large");
    for (const k of KEYS) {
      assert.doesNotMatch(fr[k], /wind-gale|hs-shift|depth-alert/);
      assert.doesNotMatch(en[k], /wind-gale|hs-shift|depth-alert/);
    }
    assert.match(fr.skipperRainSimulation, /Pas de pluie inventée/);
  });
});
