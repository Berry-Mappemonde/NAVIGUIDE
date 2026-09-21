import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { formatEtaRange, formatEtaRangeTitle, nextStopFromMarks } from "./usePlanReview.js";
import fr from "../i18n/fr.js";
import en from "../i18n/en.js";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "usePlanReview.js"), "utf8");

const interpolate = (dict) => (key, vars = {}) =>
  Object.entries(vars).reduce((s, [k, v]) => s.replace(`{${k}}`, v), dict[key] ?? key);

const tFr = interpolate(fr);
const tEn = interpolate(en);
const plain = (s) => String(s).replace(/[\u202f\u00a0]/g, " ");

describe("usePlanReview — fourchette ETA (lot R11)", () => {
  it("ne fabrique pas de fourchette sans membres ou sans dates", () => {
    assert.equal(formatEtaRange(null, tFr, "fr"), "");
    assert.equal(formatEtaRange({ members: 0, p10: "2026-10-11T00:00:00Z", p90: "2026-10-14T00:00:00Z" }, tFr, "fr"), "");
    assert.equal(formatEtaRange({ members: 80, p10: null, p90: null }, tFr, "fr"), "");
    assert.equal(formatEtaRangeTitle(null, tFr), "");
  });

  it("écrit les dates courtes fr/en, sans p10 ni membres à l'écran", () => {
    const eta = { members: 80, p10: "2026-10-31T08:00:00Z", p90: "2026-11-04T18:00:00Z" };
    const frLabel = plain(formatEtaRange(eta, tFr, "fr"));
    assert.match(frLabel, /^arrivée entre le 31 oct\.? et le 4 nov/);
    assert.doesNotMatch(frLabel, /p10|membres/i);
    const enLabel = plain(formatEtaRange(eta, tEn, "en"));
    assert.match(enLabel, /^arrival between 31 Oct\.? and 4 Nov/i);
    assert.doesNotMatch(enLabel, /p10|members/i);
    assert.equal(formatEtaRangeTitle(eta, tFr), "p10–p90, 80 membres");
    assert.equal(formatEtaRangeTitle(eta, tEn), "p10–p90, 80 members");
  });

  it("garde le mois même quand p10 et p90 sont dans le même mois", () => {
    const eta = { members: 30, p10: "2026-10-11T08:00:00Z", p90: "2026-10-14T18:00:00Z" };
    const frLabel = plain(formatEtaRange(eta, tFr, "fr"));
    assert.match(frLabel, /11 oct/);
    assert.match(frLabel, /14 oct/);
    assert.doesNotMatch(frLabel, /p10|membres/i);
  });

  it("prend la prochaine escale dont l'iso est dans le futur", () => {
    const now = Date.parse("2026-09-20T12:00:00Z");
    const name = nextStopFromMarks([
      { name: "Nouméa", iso: "2026-09-01T00:00:00Z" },
      { name: "Dzaoudzi", iso: "2026-10-12T00:00:00Z" },
    ], now);
    assert.equal(name, "Dzaoudzi");
    assert.equal(nextStopFromMarks([], now), "");
  });

  it("appelle GET /voyage/official/eta et n'invente rien si members=0", () => {
    assert.match(src, /\/voyage\/official\/eta\?stop=/);
    assert.match(src, /Number\(body\.members\) > 0/);
    assert.match(src, /etaRange: eta/);
    assert.match(src, /formatEtaRangeTitle/);
  });
});
