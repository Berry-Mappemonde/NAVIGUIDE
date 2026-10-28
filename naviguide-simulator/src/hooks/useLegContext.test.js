import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { legAtClockNow } from "./useLegContext.js";
import {
  clockTickLabelsFromClock,
  formatFilmClockLine,
  sampleClockAtTime,
  seaDayNumber,
} from "../engine/voyageClock.js";
import { formatLegLine, withNowLeg } from "../components/iciMaintenant.js";
import en from "../i18n/en.js";
import fr from "../i18n/fr.js";

describe("legAtClockNow", () => {
  const t0 = "2026-05-15T08:00:00Z";
  const now = "2026-10-18T08:00:00Z";
  const marks = [
    { name: "La Rochelle", nm: 0, filmNm: 0 },
    { name: "Ajaccio (Corse)", nm: 400, filmNm: 400 },
    { name: "Mata-Utu (Wallis-et-Futuna)", nm: 18000, filmNm: 18000 },
    { name: "Nouméa (Nouvelle-Calédonie)", nm: 19000, filmNm: 19000 },
  ];
  const nowHours = (Date.parse(now) - Date.parse(t0)) / 3600000;
  const clock = {
    t0,
    marks,
    vertices: [
      { tHours: 0, sailNm: 0, filmNm: 0, lat: 46.16, lon: -1.15, speedKnots: 6, bearing: 200, vehicle: "main" },
      { tHours: 100, sailNm: 400, filmNm: 400, lat: 41.92, lon: 8.73, speedKnots: 6, bearing: 180, vehicle: "main" },
      { tHours: nowHours - 48, sailNm: 18100, filmNm: 18100, lat: -13.28, lon: -176.18, speedKnots: 7.5, bearing: 210, vehicle: "main" },
      { tHours: nowHours + 200, sailNm: 19000, filmNm: 19000, lat: -22.27, lon: 166.44, speedKnots: 7.5, bearing: 210, vehicle: "main" },
    ],
  };

  it("reads the leg at clock now, not at t0 and not at the cursor", () => {
    const leg = legAtClockNow({
      clock,
      now,
      marks,
      cursor: 0,
      t0,
      speedKnots: 7.5,
    });
    assert.equal(leg.fromStop, "Mata-Utu (Wallis-et-Futuna)");
    assert.equal(leg.toStop, "Nouméa (Nouvelle-Calédonie)");
    assert.ok(leg.nmCovered > 18000);
    const atStart = legAtClockNow({
      clock,
      now: t0,
      marks,
      cursor: 18500,
      t0: now,
    });
    assert.equal(atStart.fromStop, "La Rochelle");
    assert.equal(atStart.toStop, "Ajaccio (Corse)");
    assert.notEqual(leg.fromStop, atStart.fromStop);
  });
});

describe("un seul jour de mer : barre film = panneau Maintenant", () => {
  const t0 = "2026-05-15T08:00:00.000Z";
  const marks = [
    { name: "La Rochelle", nm: 0, filmNm: 0 },
    { name: "Nouméa (Nouvelle-Calédonie)", nm: 30000, filmNm: 30000 },
  ];
  const clock = {
    t0,
    marks,
    vertices: [
      { tHours: 0, seaHours: 0, sailNm: 0, filmNm: 0, lat: 46.16, lon: -1.15, speedKnots: 7, bearing: 250, vehicle: "main" },
      { tHours: 4000, seaHours: 4000, sailNm: 28000, filmNm: 28000, lat: -22.27, lon: 166.44, speedKnots: 7, bearing: 250, vehicle: "main" },
    ],
  };
  const at = (hours) => new Date(Date.parse(t0) + hours * 3600000).toISOString();
  const tr = (table) => (key, vars = {}) => Object.entries(vars)
    .reduce((s, [k, v]) => s.replaceAll(`{${k}}`, String(v ?? "")), table[key] ?? key);

  /** Les trois libellés d'un même instant d'horloge : ligne d'état, graduation, panneau. */
  function labelsAt(now, lang) {
    const sample = sampleClockAtTime(clock, now);
    const film = formatFilmClockLine({ sailNm: sample.sailNm, seaHours: sample.seaHours, iso: sample.iso, lang });
    const tick = clockTickLabelsFromClock(clock, lang, {
      filmNm: sample.filmNm,
      sailNm: sample.sailNm,
      seaHours: sample.seaHours,
    })[1]?.label || "";
    const leg = withNowLeg(null, legAtClockNow({ clock, now, marks })).leg;
    const panel = formatLegLine(leg, tr(lang === "en" ? en : fr), lang);
    return { sample, film, tick, panel };
  }

  it("à 130,4 jours de mer, la barre dit d131 comme le panneau D131 (plus d130)", () => {
    const enLabels = labelsAt(at(130.4 * 24), "en");
    assert.match(enLabels.film, /\bd131\b/);
    assert.match(enLabels.tick, /\bd131\b/);
    assert.match(enLabels.panel, /\bD131\b/);
    assert.doesNotMatch(enLabels.film, /\bd130\b/);
    const frLabels = labelsAt(at(130.4 * 24), "fr");
    assert.match(frLabels.film, /\bj131\b/);
    assert.match(frLabels.panel, /\bJ131\b/);
  });

  it("même nombre partout, à chaque instant échantillonné", () => {
    for (const hours of [0.5, 23.9, 24, 47.99, 130.4 * 24, 3999]) {
      const { sample, film, tick, panel } = labelsAt(at(hours), "fr");
      const want = String(seaDayNumber(sample.seaHours));
      assert.equal(film.match(/\bj(\d+)\b/)?.[1], want, `barre à ${hours} h : ${film}`);
      assert.equal(tick.match(/\bj(\d+)\b/)?.[1], want, `graduation à ${hours} h : ${tick}`);
      assert.equal(panel.match(/\bJ(\d+)\b/)?.[1], want, `panneau à ${hours} h : ${panel}`);
    }
  });

  it("au départ, aucune heure de mer : j0 dans la barre, pas de J inventé dans le panneau", () => {
    const { film, panel } = labelsAt(at(0), "fr");
    assert.match(film, /\bj0\b/);
    assert.doesNotMatch(panel, /\bJ\d+\b/);
  });
});
