import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { allTilesErrored, loadClimoLayerFeatures } from "./climoLayerLoad.js";

const TILE_A = { z: 4, x: 8, y: 5 };
const TILE_B = { z: 4, x: 8, y: 6 };
const ROSE = {
  type: "Feature",
  geometry: { type: "Point", coordinates: [-3.2, 45.5] },
  properties: { speed_knots: 12, dir_from_deg: 270 },
};

function abortErr() {
  const err = new Error("aborted");
  err.name = "AbortError";
  return err;
}

describe("allTilesErrored", () => {
  it("true only when every tile is an error", () => {
    assert.equal(allTilesErrored(["error", "error"]), true);
    assert.equal(allTilesErrored(["error", "ok"]), false);
    assert.equal(allTilesErrored(["error", "abort"]), false);
    assert.equal(allTilesErrored(["abort", "abort"]), false);
    assert.equal(allTilesErrored([]), false);
  });
});

describe("loadClimoLayerFeatures", () => {
  it("tuiles en erreur → charge la route globale, des features existent", async () => {
    const urls = [];
    const fetchFn = async (url) => {
      urls.push(url);
      if (url.includes("/tiles/")) throw new Error("HTTP 404");
      return { features: [ROSE] };
    };
    const result = await loadClimoLayerFeatures({
      kind: "wind",
      month: 5,
      extra: {},
      tiles: [TILE_A, TILE_B],
      cache: new Map(),
      fetchJson: fetchFn,
    });
    assert.equal(result.source, "global");
    assert.equal(result.aborted, false);
    assert.equal(result.features.length, 1);
    assert.ok(urls.some((u) => u.includes("/wind/tiles/")));
    assert.ok(urls.some((u) => /wind\.geojson\?/.test(u) && /spacing_deg=4/.test(u)));
  });

  it("tuiles OK → aucun appel à la route globale", async () => {
    const urls = [];
    const fetchFn = async (url) => {
      urls.push(url);
      if (url.includes(".geojson")) throw new Error("global must not be called");
      return { features: [ROSE] };
    };
    const result = await loadClimoLayerFeatures({
      kind: "wind",
      month: 5,
      extra: {},
      tiles: [TILE_A],
      cache: new Map(),
      fetchJson: fetchFn,
    });
    assert.equal(result.source, "tiles");
    assert.equal(result.features.length, 1);
    assert.ok(urls.every((u) => u.includes("/tiles/") && !u.includes(".geojson")));
  });

  it("annulation → pas de repli global", async () => {
    const urls = [];
    const fetchFn = async (url) => {
      urls.push(url);
      throw abortErr();
    };
    const result = await loadClimoLayerFeatures({
      kind: "wind",
      month: 5,
      tiles: [TILE_A, TILE_B],
      cache: new Map(),
      fetchJson: fetchFn,
    });
    assert.equal(result.source, "tiles");
    assert.ok(result.aborted || !urls.some((u) => u.includes(".geojson")));
    assert.ok(!urls.some((u) => u.includes(".geojson")));
  });

  it("succès partiel → pas de repli même si d'autres tuiles échouent", async () => {
    const urls = [];
    let n = 0;
    const fetchFn = async (url) => {
      urls.push(url);
      if (url.includes(".geojson")) throw new Error("global must not be called");
      n += 1;
      if (n === 1) return { features: [ROSE] };
      throw new Error("HTTP 502");
    };
    const result = await loadClimoLayerFeatures({
      kind: "wind",
      month: 5,
      tiles: [TILE_A, TILE_B],
      cache: new Map(),
      fetchJson: fetchFn,
    });
    assert.equal(result.source, "tiles");
    assert.equal(result.features.length, 1);
    assert.ok(!urls.some((u) => u.includes(".geojson")));
  });

  it("repli jamais définitif : passe suivante retente les tuiles", async () => {
    const urls = [];
    let pass = 0;
    const fetchFn = async (url) => {
      urls.push(url);
      if (url.includes("/tiles/")) {
        if (pass === 0) throw new Error("HTTP 404");
        return { features: [ROSE, ROSE] };
      }
      return { features: [ROSE] };
    };
    const cache = new Map();
    const first = await loadClimoLayerFeatures({
      kind: "wave",
      month: 9,
      extra: { stat: "p50" },
      tiles: [TILE_A],
      cache,
      fetchJson: fetchFn,
    });
    assert.equal(first.source, "global");
    pass = 1;
    const second = await loadClimoLayerFeatures({
      kind: "wave",
      month: 9,
      extra: { stat: "p50" },
      tiles: [TILE_A],
      cache,
      fetchJson: fetchFn,
    });
    assert.equal(second.source, "tiles");
    assert.equal(second.features.length, 2);
    const geoAfter = urls.filter((u) => u.includes("wave.geojson")).length;
    assert.equal(geoAfter, 1);
  });
});
