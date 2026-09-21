import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { wrapLon } from "../utils/geo.js";
import { iciSearchParams } from "./useIciDossier.js";

const src = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "useIciDossier.js"), "utf8");

describe("useIciDossier — lot T wrapLon", () => {
  it("l'URL /ici porte une longitude dans [−180, 180] pour un point à 236,84°", () => {
    const q = iciSearchParams({ lat: 37.7, lon: 236.84 });
    const lon = Number(q.get("lon"));
    assert.ok(Number.isFinite(lon));
    assert.ok(lon >= -180 && lon <= 180, `lon=${lon}`);
    assert.equal(Number(lon.toFixed(2)), Number(wrapLon(236.84).toFixed(2)));
    assert.equal(Number(lon.toFixed(2)), -123.16);
    const dest = iciSearchParams({ lat: 18.1, lon: -16.4, destLat: 37.7, destLon: 236.84 });
    const destLon = Number(dest.get("dest_lon"));
    assert.ok(destLon >= -180 && destLon <= 180);
    assert.equal(Number(destLon.toFixed(2)), -123.16);
  });
});

describe("useIciDossier contract", () => {
  it("collects GET /ici without awaiting a chat, then judges locally", () => {
    assert.match(src, /One step = one GET \/ici/);
    assert.match(src, /Never await a model/);
    assert.match(src, /DEBOUNCE_MS = 800/);
    assert.match(src, /MOVE_NM = 3/);
    assert.match(src, /MIN_SCHEDULE_MS = 8000/);
    assert.match(src, /detectEvents/);
    assert.match(src, /judgeEvents/);
    assert.match(src, /along,/);
    assert.match(src, /enqueueStory/);
    assert.match(src, /orders = null/);
    assert.match(src, /orders,\n\s+lang,/);
    assert.match(src, /judgeEvents\(withPhrase, \{[\s\S]*?orders,[\s\S]*?\}\)/);
    assert.match(src, /Changing orders never rewinds/);
    assert.doesNotMatch(src, /await enqueueStory|await fetch\(.*chat|Nemotron|Token Factory/);
    assert.doesNotMatch(src, /tavily\?|nvidia\?/);
  });
});
