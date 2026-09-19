import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { datedMarks, dayMonth, expeditionStory, expeditionStoryText } from "./expeditionStory.js";

const clock = { t0: "2026-05-15T08:00:00Z" };
const marks = [
  { name: "Saint-Maur (Berry, Indre)", filmNm: 0, iso: "2026-05-15T08:00:00Z", holdHours: 0 },
  { name: "La Rochelle", filmNm: 122, iso: "2026-05-15T12:00:00Z", holdHours: 72 },
  { name: "Ajaccio (Corse)", filmNm: 1942, iso: "2026-05-24T12:51:00Z", holdHours: 72 },
  { name: "Fort-de-France (Martinique)", filmNm: 7095, iso: "2026-06-23T08:34:00Z", holdHours: 72 },
  { name: "Nouméa (Nouvelle-Calédonie)", filmNm: 19177, iso: "2026-09-17T22:48:00Z", holdHours: 72 },
  { name: "Dzaoudzi (Mayotte)", filmNm: 28328, iso: "2026-11-02T02:41:00Z", holdHours: 72 },
];
const now = Date.parse("2026-09-19T02:00:00Z");

describe("expeditionStory — le récit depuis Saint-Maur", () => {
  it("départ, escales franchies avec dates, aujourd’hui avec cap et ETA", () => {
    const live = { filmNm: 19400, sailNm: 19260, seaHours: 94 * 24, iso: "2026-09-19T02:00:00Z", status: "live", vehicle: "main", kind: "forecast", windKnots: 12.4, dirFromDeg: 135, model: "GFS" };
    const leg = { fromStop: "Nouméa (Nouvelle-Calédonie)", toStop: "Dzaoudzi (Mayotte)", remainingNm: 9100, etaHours: 44 * 24 };
    const paras = expeditionStory({ clock, marks, live, leg, now, lang: "fr" });
    assert.equal(paras.length, 4);
    assert.equal(paras[0], "L’expédition Berry-Mappemonde a quitté Saint-Maur le 15 mai 2026, et le bateau a pris la mer à La Rochelle.");
    assert.equal(paras[1], "Depuis, 3 escales : Ajaccio (Corse) (24 mai), Fort-de-France (Martinique) (23 juin) et Nouméa (Nouvelle-Calédonie) (17 septembre) — 9 jours à quai en tout.");
    // toLocaleString("fr-FR") writes a narrow no-break space in "19 260": compare on plain spaces.
    assert.equal(paras[2].replace(/[\u202f\u00a0]/g, " "), "Aujourd’hui, jour 126 (94 de mer) : le bateau est à 19 260 nm du départ, cap sur Dzaoudzi (Mayotte) (encore 9 100 nm), arrivée prévue le 2 novembre.");
    assert.equal(paras[3], "Au bateau : vent 12 kn de SE (prévision GFS).");
    assert.equal(expeditionStoryText({ clock, marks, live, leg, now }).split("\n\n").length, 4);
  });

  it("anglais, à quai, vent du journal quand le GRIB live manque", () => {
    const live = { filmNm: 19177, sailNm: 19060, seaHours: 94 * 24, status: "live", vehicle: "quay", atQuay: true, kind: "absent" };
    const leg = { fromStop: "Nouméa (Nouvelle-Calédonie)", toStop: "Dzaoudzi (Mayotte)", remainingNm: 9151 };
    const journal = { latest: [
      { kind: "position", t: "2026-09-18T12:00:00Z" },
      { kind: "grib", t: "2026-09-18T06:00:00Z", windKnots: 17.6, dirFromDeg: 90, model: "GFS" },
      { kind: "grib", t: "2026-09-17T06:00:00Z", windKnots: 9, dirFromDeg: 45, model: "GFS" },
    ] };
    const paras = expeditionStory({ clock, marks, live, leg, journal, now, lang: "en" });
    assert.match(paras[0], /^The Berry-Mappemonde expedition left Saint-Maur on 15 May 2026, and the boat put to sea at La Rochelle\.$/);
    assert.match(paras[1], /^Since then, 3 stopovers: Ajaccio \(Corse\) \(24 May\)/);
    assert.equal(paras[2], "Today, day 126 (94 at sea): the boat is in port at Nouméa (Nouvelle-Calédonie), 19,060 nm from the start; next leg to Dzaoudzi (Mayotte), expected on 2 November.");
    assert.equal(paras[3], "On 18 September, at the boat: wind 18 kn from the E (GFS forecast).");
  });

  it("avant le départ : une seule phrase, au futur", () => {
    const paras = expeditionStory({ clock, marks, live: null, leg: null, now: Date.parse("2026-05-01T00:00:00Z"), lang: "fr" });
    assert.deepEqual(paras, ["L’expédition Berry-Mappemonde quitte Saint-Maur le 15 mai 2026 et prend la mer à La Rochelle."]);
  });

  it("sans horloge ni escales : rien ; sans live : départ + escales seulement", () => {
    assert.deepEqual(expeditionStory({ now }), []);
    const paras = expeditionStory({ clock, marks, live: null, now, lang: "fr" });
    assert.equal(paras.length, 2);
    assert.match(paras[1], /Nouméa/);
  });

  it("datedMarks dédoublonne et trie ; dayMonth écrit 1er en français", () => {
    const d = datedMarks([...marks, { name: "La Rochelle", filmNm: 122.2, iso: "2026-05-15T12:00:00Z" }, { name: "Sans date", filmNm: 5 }]);
    assert.equal(d.length, marks.length);
    assert.equal(dayMonth("2026-06-01T10:00:00Z", "fr"), "1er juin");
    assert.equal(dayMonth("2026-06-01T10:00:00Z", "en"), "1 June");
    assert.equal(dayMonth("bad"), "");
  });
});
