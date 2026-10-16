import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { kickLayerWarm, pointsFromCustomRoute } from "./layerWarm.js";

const line = {
  type: "FeatureCollection",
  features: [{
    type: "Feature",
    properties: {},
    geometry: {
      type: "LineString",
      coordinates: [[-1.16, 46.15], [9.19, 41.31]],
    },
  }],
};

describe("layerWarm (lot LY1)", () => {
  it("extrait les sommets [lat, lon] d'une LineString", () => {
    assert.deepEqual(pointsFromCustomRoute(line), [[46.15, -1.16], [41.31, 9.19]]);
    assert.deepEqual(pointsFromCustomRoute(null), []);
    assert.deepEqual(pointsFromCustomRoute({ type: "FeatureCollection", features: [] }), []);
  });

  it("lit aussi un MultiLineString et ignore un polygone", () => {
    const mixed = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: {
            type: "MultiLineString",
            coordinates: [[[-17.8, 18.2], [-16.9, 17.6]]],
          },
        },
        {
          type: "Feature",
          geometry: {
            type: "Polygon",
            coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]],
          },
        },
      ],
    };
    assert.deepEqual(pointsFromCustomRoute(mixed), [[18.2, -17.8], [17.6, -16.9]]);
  });

  it("POST /ici/layers/warm sans bloquer, et ne lance rien sans points", () => {
    const calls = [];
    const fake = (url, opts) => {
      calls.push({ url, opts });
      return Promise.resolve({ ok: true });
    };
    assert.equal(kickLayerWarm({ type: "FeatureCollection", features: [] }, fake), false);
    assert.equal(calls.length, 0);
    assert.equal(kickLayerWarm(line, fake), true);
    assert.equal(calls.length, 1);
    assert.match(calls[0].url, /\/ici\/layers\/warm$/);
    assert.equal(calls[0].opts.method, "POST");
    const body = JSON.parse(calls[0].opts.body);
    assert.deepEqual(body.points, [[46.15, -1.16], [41.31, 9.19]]);
  });
});
