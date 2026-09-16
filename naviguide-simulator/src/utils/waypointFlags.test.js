import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  flagIconMetrics,
  flagMarkerHtml,
  lonOnCameraCopy,
  waypointFlagSrcs,
  worldCopyLngs,
} from "./waypointFlags.js";

describe("waypointFlagSrcs", () => {
  it("préfère flags[] (Nouméa Kanak + FR)", () => {
    assert.deepEqual(waypointFlagSrcs({ flag: "a", flags: ["kanak", "france"] }), ["kanak", "france"]);
    assert.deepEqual(waypointFlagSrcs({ flag: "solo" }), ["solo"]);
    assert.deepEqual(waypointFlagSrcs({ flag: "" }), []);
    assert.deepEqual(waypointFlagSrcs({ flags: [] }), []);
  });

  it("divIcon 1 ou 2 images", () => {
    const one = flagMarkerHtml(["/k.png"]);
    const two = flagMarkerHtml(["/k.png", "/fr.png"], [3, -2]);
    assert.equal((one.match(/<img/g) || []).length, 1);
    assert.equal((two.match(/<img/g) || []).length, 2);
    assert.match(two, /translate\(3px,-2px\)/);
    assert.deepEqual(flagIconMetrics(["a"]).iconSize[0] < flagIconMetrics(["a", "b"]).iconSize[0], true);
  });
});

describe("lonOnCameraCopy / worldCopyLngs", () => {
  it("aligne la copie sur la caméra près de 180°", () => {
    assert.deepEqual(worldCopyLngs(166.4), [166.4, 526.4, -193.6]);
    assert.equal(lonOnCameraCopy(166.4, 170), 166.4);
    assert.equal(lonOnCameraCopy(166.4, 520), 526.4);
    assert.equal(lonOnCameraCopy(166.4, -190), -193.6);
  });
});

describe("Nouméa", () => {
  it("waypoints.js expose Kanak + français", () => {
    const src = readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), "../constants/waypoints.js"),
      "utf8",
    );
    assert.match(src, /"Nouméa \(Nouvelle-Calédonie\)":\s+\[nouvelleCaledonie, france\]/);
  });

  it("itineraryPoints pose flags: [kanak, france]", () => {
    const src = readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), "../constants/itineraryPoints.ts"),
      "utf8",
    );
    assert.match(src, /name: "Nouméa \(Nouvelle-Calédonie\)"[\s\S]{0,180}flags: \[nouvelleCaledonie, france\]/);
  });
});
