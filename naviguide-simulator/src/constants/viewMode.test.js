import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  VIEW_SUIVRE,
  VIEW_SIMULATION,
  hasSimulationPlaybackControls,
  isSuivreView,
  isSimulationView,
} from "./viewMode.js";
import fr from "../i18n/fr.js";
import en from "../i18n/en.js";

const FORBIDDEN = /mode suivre|Mode Suivre|Follow mode|bateau virtuel|virtual boat/i;

describe("viewMode U2", () => {
  it("deux vues exclusives", () => {
    assert.equal(VIEW_SUIVRE, "suivre");
    assert.equal(VIEW_SIMULATION, "simulation");
    assert.ok(isSuivreView(VIEW_SUIVRE));
    assert.ok(isSimulationView(VIEW_SIMULATION));
    assert.equal(isSuivreView(VIEW_SIMULATION), false);
  });

  it("libellés : Suivre l’expédition / Simulation, sans vocabulaire interdit", () => {
    assert.equal(fr.followExpeditionButton, "Suivre l’expédition");
    assert.equal(fr.simulationButton, "Simulation");
    assert.equal(en.simulationButton, "Simulation");
    assert.doesNotMatch(fr.followExpeditionButton, FORBIDDEN);
    assert.doesNotMatch(fr.simulationButton, FORBIDDEN);
    assert.doesNotMatch(en.followExpeditionButton, FORBIDDEN);
    assert.doesNotMatch(en.simulationButton, FORBIDDEN);
  });

  it("réserve les contrôles du film à Simulation", () => {
    assert.equal(hasSimulationPlaybackControls(VIEW_SIMULATION), true);
    assert.equal(hasSimulationPlaybackControls(VIEW_SUIVRE), false);
  });
});
