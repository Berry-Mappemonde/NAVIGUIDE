import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { antimeridianLineCount, routeFromOfficial } from "./routeFromOfficial.js";

const root = join(dirname(fileURLToPath(import.meta.url)), "../..");
const fc = JSON.parse(readFileSync(join(root, "public/route.geojson"), "utf8"));

describe("routeFromOfficial", () => {
  it("separates overland and maritime", () => {
    const { segments, stops } = routeFromOfficial(fc);
    assert.ok(segments.some((s) => s.nonMaritime && s.from.name.includes("Saint-Maur")));
    assert.ok(segments.some((s) => !s.nonMaritime));
    assert.ok(stops.some((s) => s.flag && s.name === "La Rochelle"));
  });

  it("keeps two LineString Wallis→Nouméa", () => {
    assert.equal(antimeridianLineCount(fc), 2);
  });
});
