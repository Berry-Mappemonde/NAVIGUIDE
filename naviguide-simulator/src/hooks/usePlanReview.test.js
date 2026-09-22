import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  ADVICE_FIXTURE,
  ETA_MIN_KN,
  ETA_RETRY_MS,
  boundEtaIso,
  buildAdviceCompare,
  etaFromResponse,
  etaRangeFromMembers,
  formatAdvicePills,
  formatAdviceSentence,
  formatEtaRange,
  formatEtaRangeTitle,
  isAdviceDone,
  localizeAdviceSentence,
  nextEtaRetryMs,
  nextStopFromMarks,
  pickHeaviestLegIdx,
  pollOfficialAdvice,
  pollOfficialEta,
  tightenEtaMembers,
} from "./usePlanReview.js";
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
    assert.match(src, /pollOfficialEta/);
    assert.match(src, /ETA_RETRY_MS/);
  });

  it("affiche la fourchette dès que members passe de 0 à un ensemble", async () => {
    const empty = { members: 0, p10: null, p90: null };
    const full = {
      members: 40,
      p10: "2026-11-13T00:00:00Z",
      p50: "2026-11-15T00:00:00Z",
      p90: "2026-11-18T00:00:00Z",
    };
    let n = 0;
    const seen = [];
    const ready = await pollOfficialEta("Dzaoudzi", {
      fetchFn: async () => {
        n += 1;
        return n === 1 ? empty : full;
      },
      sleep: async () => {},
      onUpdate: (eta) => seen.push(eta),
    });
    assert.equal(etaFromResponse(empty), null);
    assert.equal(seen[0], null);
    assert.equal(formatEtaRange(empty, tFr, "fr"), "");
    assert.equal(ready.members, 40);
    const label = plain(formatEtaRange(ready, tFr, "fr"));
    assert.match(label, /arrivée entre le 13 nov/);
    assert.match(label, /18 nov/);
    assert.doesNotMatch(label, /p10|membres/i);
    assert.equal(plain(formatEtaRange(ready, tEn, "en")).slice(0, 16).toLowerCase(), "arrival between ");
    assert.equal(n, 2);
    assert.equal(nextEtaRetryMs(0), ETA_RETRY_MS[0]);
    assert.ok(nextEtaRetryMs(9) >= nextEtaRetryMs(0));
    assert.equal(ETA_RETRY_MS[ETA_RETRY_MS.length - 1], 30000);
  });

  it("écarte tout membre à 0 kn de la fourchette (lot RA7)", () => {
    assert.equal(ETA_MIN_KN, 3);
    const members = [
      { knots: 8.1, arrival: "2026-11-13T00:00:00Z" },
      { knots: 0, arrival: "2027-06-10T00:00:00Z" },
      { knots: 7.8, arrival: "2026-11-16T00:00:00Z" },
    ];
    const kept = tightenEtaMembers(members);
    assert.equal(kept.some((m) => m.knots === 0), false);
    assert.equal(kept.length, 2);
    const eta = etaRangeFromMembers(members);
    assert.ok(eta);
    assert.ok(eta.memberKnots.every((k) => k >= ETA_MIN_KN));
    assert.doesNotMatch(eta.p90, /2027-06/);
    const days = (Date.parse(eta.p90) - Date.parse(eta.p10)) / 86400000;
    assert.ok(days <= 7, `span ${days} j`);
    const label = plain(formatEtaRange({
      members: 80,
      p10: "2026-11-13T00:00:00Z",
      p50: "2026-11-15T00:00:00Z",
      p90: "2027-06-10T00:00:00Z",
      memberKnots: [8, 8],
    }, tFr, "fr"));
    assert.doesNotMatch(label, /juin/i);
    assert.match(label, /arrivée entre le/);
    const hidden = boundEtaIso("2026-11-13T00:00:00Z", null, "2027-06-10T00:00:00Z");
    assert.equal(hidden.p10, "");
  });
});

describe("usePlanReview — conseil (lot R10d)", () => {
  it("écrit la phrase et les pastilles en FR et EN, sans anglais en FR", () => {
    const best = ADVICE_FIXTURE.best;
    const fr = formatAdviceSentence(best, tFr, "fr");
    const en = formatAdviceSentence(best, tEn, "en");
    assert.match(fr, /Partir de Nouméa/);
    assert.match(fr, /5 alertes au lieu de 11/);
    assert.match(fr, /\+41 nm/);
    assert.match(fr, /7 jours/);
    assert.doesNotMatch(fr, /\b(Leave|Instead|alerts instead)\b/);
    assert.match(en, /Leave Nouméa/);
    assert.match(en, /5 alerts instead of 11/);
    const pillsFr = formatAdvicePills(best, tFr);
    assert.equal(pillsFr.alerts, "11 → 5 alertes");
    assert.equal(pillsFr.nm, "+41 nm");
    assert.equal(pillsFr.days, "+7 j");
    const pillsEn = formatAdvicePills(best, tEn);
    assert.equal(pillsEn.alerts, "11 → 5 alerts");
  });

  it("écarte un texte rédigé anglais quand l'UI est FR", () => {
    const best = {
      ...ADVICE_FIXTURE.best,
      sentence: "Leave Nouméa rather than 1 Oct: 5 alerts instead of 11.",
      sentenceLang: "en",
    };
    const fr = localizeAdviceSentence(best, tFr, "fr");
    assert.match(fr, /Partir de Nouméa/);
    assert.doesNotMatch(fr, /Leave Nouméa/);
    const en = localizeAdviceSentence({ ...ADVICE_FIXTURE.best, sentenceLang: "fr" }, tEn, "en");
    assert.match(en, /Leave Nouméa/);
  });

  it("construit deux colonnes avec les dates d'escale décalées", () => {
    const compare = buildAdviceCompare(ADVICE_FIXTURE.best, { legNm: 6144, daysAtSea: 32 }, tFr, "fr");
    assert.match(compare.today.distance, /6144 nm/);
    assert.match(compare.advised.distance, /6185 nm/);
    assert.equal(compare.today.alerts, "11 alertes");
    assert.equal(compare.advised.alerts, "5 alertes");
    assert.ok(compare.today.stops.some((s) => /Dzaoudzi/.test(s)));
    assert.ok(compare.advised.stops.some((s) => /Dzaoudzi/.test(s)));
    assert.notEqual(compare.today.stops[0], compare.advised.stops[0]);
  });

  it("prend la jambe la plus chargée et sondé /advice?leg=", () => {
    assert.equal(pickHeaviestLegIdx([{ alertCount: 2 }, { alertCount: 11 }]), 1);
    assert.equal(isAdviceDone(ADVICE_FIXTURE), true);
    assert.match(src, /\/voyage\/official\/advice\?/);
    assert.match(src, /pollOfficialAdvice/);
  });

  it("relance /advice tant que pending, puis garde le best", async () => {
    const pending = { status: "pending", leg: 0 };
    const done = ADVICE_FIXTURE;
    let n = 0;
    const seen = [];
    const ready = await pollOfficialAdvice(0, {
      fetchFn: async () => {
        n += 1;
        return n === 1 ? pending : done;
      },
      sleep: async () => {},
      onUpdate: (body) => seen.push(body),
      lang: "fr",
    });
    assert.equal(n, 2);
    assert.equal(ready.best.alertsAfter, 5);
    assert.equal(seen[0].status, "pending");
  });
});
