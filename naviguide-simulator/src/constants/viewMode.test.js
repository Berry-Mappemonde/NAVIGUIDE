import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  VIEW_SUIVRE,
  VIEW_TRACER,
  SERVER_MODE_TRACER,
  hasTracerPlaybackControls,
  isSuivreView,
  isTracerView,
} from "./viewMode.js";
import fr from "../i18n/fr.js";
import en from "../i18n/en.js";

const FORBIDDEN = /mode suivre|Mode Suivre|Follow mode|bateau virtuel|virtual boat/i;

describe("viewMode U2", () => {
  it("deux vues exclusives", () => {
    assert.equal(VIEW_SUIVRE, "suivre");
    assert.equal(VIEW_TRACER, "tracer");
    assert.equal(SERVER_MODE_TRACER, "simulation");
    assert.ok(isSuivreView(VIEW_SUIVRE));
    assert.ok(isTracerView(VIEW_TRACER));
    assert.equal(isSuivreView(VIEW_TRACER), false);
  });

  it("libellés : Suivre l’expédition / Tracer, sans vocabulaire interdit", () => {
    assert.equal(fr.followExpeditionButton, "Suivre l’expédition");
    assert.equal(fr.tracerButton, "Tracer");
    assert.equal(en.tracerButton, "Plot");
    assert.doesNotMatch(fr.followExpeditionButton, FORBIDDEN);
    assert.doesNotMatch(fr.tracerButton, FORBIDDEN);
    assert.doesNotMatch(en.followExpeditionButton, FORBIDDEN);
    assert.doesNotMatch(en.tracerButton, FORBIDDEN);
  });

  it("réserve les contrôles du film à Tracer", () => {
    assert.equal(hasTracerPlaybackControls(VIEW_TRACER), true);
    assert.equal(hasTracerPlaybackControls(VIEW_SUIVRE), false);
  });
});
