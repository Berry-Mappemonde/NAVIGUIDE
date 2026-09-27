import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { haversineNm, wrapLon } from "../utils/geo.js";
import {
  MOVE_NM,
  countIciFetchesAlongTrack,
  iciSearchParams,
  shouldCatchUpIci,
  shouldScheduleIciFetch,
} from "./useIciDossier.js";

function trackNm(startLat, startLon, totalNm, stepNm = 10) {
  const points = [];
  for (let d = 0; d <= totalNm; d += stepNm) {
    points.push({ lat: startLat + d / 60, lon: startLon });
  }
  return points;
}

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
    assert.match(src, /frozen = false/);
    assert.match(src, /shouldScheduleIciFetch/);
    assert.match(src, /shouldCatchUpIci/);
  });
});

describe("useIciDossier — film gelé (lot RF4)", () => {
  const last = { lat: 0, lon: 0, month: 5, destLat: 10, destLon: 10 };
  const dest = { month: 5, destLat: 10, destLon: 10 };

  it("un tour de 3 000 nm pendant le film : zéro GET /ici, un rattrapage à l'arrêt", () => {
    const points = trackNm(0, 0, 3000, 10);
    assert.ok(haversineNm(0, 0, points.at(-1).lat, 0) >= 2990, "piste ≥ 3 000 nm");
    assert.equal(countIciFetchesAlongTrack(points, { frozen: true, last, ...dest }), 0);
    assert.equal(shouldCatchUpIci({ wasFrozen: true, frozen: true }), false);
    assert.equal(shouldCatchUpIci({ wasFrozen: true, frozen: false }), true);
    assert.equal(
      shouldScheduleIciFetch({ frozen: false, last: null, lat: 0, lon: 0, ...dest }),
      true,
    );
  });

  it("hors film, 3 nm déclenchent encore une sonde", () => {
    const unfrozen = countIciFetchesAlongTrack(trackNm(0, 0, 3000, 10), { frozen: false, last, ...dest });
    assert.ok(unfrozen > 100, `hors film ${unfrozen} sondes`);
    assert.equal(MOVE_NM, 3);
    assert.equal(shouldScheduleIciFetch({
      frozen: false, last, lat: 0, lon: 0, ...dest,
    }), false);
  });

  it("App gèle le sac, le moment, l'along et la revue pendant replay.active", () => {
    const app = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "..", "App.jsx"), "utf8");
    assert.match(app, /frozen:\s*replay\.active/);
    assert.match(app, /enabled: Boolean\(cast && routeReady\) && !replay\.active/);
    assert.match(app, /frozen=\{Boolean\(replay\.active\)\}/);
  });
});
