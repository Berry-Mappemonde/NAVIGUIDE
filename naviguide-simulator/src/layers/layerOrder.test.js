import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { LEAFLET_BUILTIN_PANES, PANES } from "./layerOrder.js";

describe("panes", () => {
  it("garde l'ordre verrouillé", () => {
    assert.deepEqual(PANES.map((p) => p.name), ["zee-wms", "balisage", "route", "amp", "boat"]);
    assert.ok(PANES.find((p) => p.name === "route").zIndex < LEAFLET_BUILTIN_PANES.markerPane);
    assert.ok(PANES.find((p) => p.name === "boat").zIndex > LEAFLET_BUILTIN_PANES.markerPane);
    assert.ok(PANES.find((p) => p.name === "boat").zIndex < LEAFLET_BUILTIN_PANES.popupPane);
  });
});
