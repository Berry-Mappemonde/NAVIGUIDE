import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { datedMarks, dayMonth, expeditionStory, expeditionStoryText } from "./expeditionStory.js";

const clock = { t0: "2026-05-15T08:00:00Z" };
const marks = [
  { name: "Saint-Maur (Berry, Indre)", nm: 0, filmNm: 0, iso: "2026-05-15T08:00:00Z", holdHours: 0 },
  { name: "La Rochelle", nm: 0, filmNm: 122, iso: "2026-05-15T12:00:00Z", holdHours: 72 },
  { name: "Ajaccio (Corse)", nm: 1820, filmNm: 1942, iso: "2026-05-24T12:51:00Z", holdHours: 72 },
  { name: "Fort-de-France (Martinique)", nm: 6973, filmNm: 7095, iso: "2026-06-23T08:34:00Z", holdHours: 72 },
  { name: "Nouméa (Nouvelle-Calédonie)", nm: 19055, filmNm: 19177, iso: "2026-09-17T22:48:00Z", holdHours: 72 },
  { name: "Dzaoudzi (Mayotte)", nm: 28206, filmNm: 28328, iso: "2026-11-02T02:41:00Z", holdHours: 72 },
];
const now = Date.parse("2026-09-19T02:00:00Z");
const plain = (s) => s.replace(/[\u202f\u00a0]/g, " ");

describe("expeditionStory — chronologique, jambe par jambe", () => {
  it("départ, puis chaque jambe (départ, traversée, arrivée, quai), puis la jambe en cours et aujourd’hui", () => {
    const live = { filmNm: 19400, sailNm: 19260, seaHours: 94 * 24, iso: "2026-09-19T02:00:00Z", status: "live", vehicle: "main", kind: "forecast", windKnots: 12.4, dirFromDeg: 135, model: "GFS" };
    const leg = { fromStop: "Nouméa (Nouvelle-Calédonie)", toStop: "Dzaoudzi (Mayotte)", remainingNm: 9100, etaHours: 44 * 24 };
    const journal = { latest: [
      { kind: "grib", t: "2026-05-20T06:00:00Z", windKnots: 10, dirFromDeg: 270, model: "GFS" },
      { kind: "grib", t: "2026-05-22T06:00:00Z", windKnots: 18, dirFromDeg: 300, model: "GFS" },
      { kind: "note", t: "2026-05-21T10:00:00Z", text: "Première nuit au large, belle étoile." },
      { kind: "zee", t: "2026-05-16T09:00:00Z", event: "exit", name: "French Exclusive Economic Zone", mrgid: 5677 },
      { kind: "zee", t: "2026-05-17T15:00:00Z", event: "enter", name: "Spanish Exclusive Economic Zone", mrgid: 5693 },
      { kind: "zee", t: "2026-05-18T01:00:00Z", event: "exit", name: "Spanish Exclusive Economic Zone", mrgid: 5693 },
      { kind: "zee", t: "2026-05-18T09:00:00Z", event: "enter", name: "Spanish Exclusive Economic Zone", mrgid: 5693 },
      { kind: "amp", t: "2026-05-18T02:00:00Z", event: "nearby", name: "Cabrera", nm: 8 },
      { kind: "grib", t: "2026-09-18T06:00:00Z", windKnots: 14, dirFromDeg: 120, model: "GFS" },
    ] };
    const paras = expeditionStory({ clock, marks, live, leg, journal, now, lang: "fr" }).map(plain);
    assert.equal(paras[0], "L’expédition Berry-Mappemonde a quitté Saint-Maur le 15 mai 2026.");
    assert.equal(paras[1], "Le 15 mai, le bateau a pris la mer à La Rochelle, vers Ajaccio (Corse) : 1 820 nm en 9 jours. "
      + "Entre-temps — entré dans : Spanish Exclusive Economic Zone le 17 mai ; aire marine protégée à portée : Cabrera. "
      + "Vent au bateau : 14 kn en moyenne, 18 kn au plus fort (GFS, 2 relevés). "
      + "Le skipper a noté : « Première nuit au large, belle étoile. » "
      + "Arrivée à Ajaccio (Corse) le 24 mai, 3 jours à quai.");
    assert.equal(paras[2], "Puis, le 27 mai, départ vers Fort-de-France (Martinique) : 5 153 nm en 27 jours. Arrivée à Fort-de-France (Martinique) le 23 juin, 3 jours à quai.");
    assert.equal(paras[3], "Puis, le 26 juin, départ vers Nouméa (Nouvelle-Calédonie) : 12 082 nm en 84 jours. Arrivée à Nouméa (Nouvelle-Calédonie) le 17 septembre, 3 jours à quai.");
    assert.equal(paras[4], "Depuis le 20 septembre, en route de Nouméa (Nouvelle-Calédonie) vers Dzaoudzi (Mayotte) : encore 9 100 nm, arrivée prévue le 2 novembre.");
    assert.equal(paras[5], "Aujourd’hui, jour 126 (94 de mer) : le bateau est à 19 260 nm du départ.");
    assert.equal(paras[6], "Au bateau maintenant : vent 12 kn de SE (prévision GFS).");
    assert.equal(paras.length, 7);
    assert.equal(expeditionStoryText({ clock, marks, live, leg, journal, now }).split("\n\n").length, 7);
  });

  it("anglais, à quai, vent du journal quand le GRIB live manque", () => {
    const live = { filmNm: 19177, sailNm: 19055, seaHours: 94 * 24, status: "live", vehicle: "quay", atQuay: true, kind: "absent" };
    const leg = { fromStop: "Nouméa (Nouvelle-Calédonie)", toStop: "Dzaoudzi (Mayotte)", remainingNm: 9151 };
    const journal = { latest: [
      { kind: "position", t: "2026-09-18T12:00:00Z" },
      { kind: "grib", t: "2026-09-18T06:00:00Z", windKnots: 17.6, dirFromDeg: 90, model: "GFS" },
      { kind: "grib", t: "2026-09-17T06:00:00Z", windKnots: 9, dirFromDeg: 45, model: "GFS" },
    ] };
    const paras = expeditionStory({ clock, marks, live, leg, journal, now, lang: "en" }).map(plain);
    assert.equal(paras[0], "The Berry-Mappemonde expedition left Saint-Maur on 15 May 2026.");
    assert.match(paras[1], /^On 15 May, the boat put to sea at La Rochelle, bound for Ajaccio \(Corse\) : 1,820 nm in 9 days\. Arrival at Ajaccio \(Corse\) on 24 May, 3 days in port\.$/);
    assert.match(paras[2], /^Then on 27 May, departure for Fort-de-France/);
    assert.equal(paras[4], "Today, day 126 (94 at sea): the boat is in port at Nouméa (Nouvelle-Calédonie), 19,055 nm from the start; next leg to Dzaoudzi (Mayotte), expected on 2 November.");
    assert.equal(paras[5], "On 18 September, at the boat: wind 18 kn from the E (GFS forecast).");
  });

  it("avant le départ : une seule phrase, au futur", () => {
    const paras = expeditionStory({ clock, marks, live: null, leg: null, now: Date.parse("2026-05-01T00:00:00Z"), lang: "fr" });
    assert.deepEqual(paras, ["L’expédition Berry-Mappemonde quitte Saint-Maur le 15 mai 2026 et prend la mer à La Rochelle."]);
  });

  it("sans horloge ni escales : rien ; sans live : départ + jambes franchies seulement", () => {
    assert.deepEqual(expeditionStory({ now }), []);
    const paras = expeditionStory({ clock, marks, live: null, now, lang: "fr" });
    assert.equal(paras.length, 4);
    assert.match(paras[3], /Nouméa/);
  });

  it("datedMarks dédoublonne et trie ; dayMonth écrit 1er en français", () => {
    const d = datedMarks([...marks, { name: "La Rochelle", filmNm: 122.2, iso: "2026-05-15T12:00:00Z" }, { name: "Sans date", filmNm: 5 }]);
    assert.equal(d.length, marks.length);
    assert.equal(dayMonth("2026-06-01T10:00:00Z", "fr"), "1er juin");
    assert.equal(dayMonth("2026-06-01T10:00:00Z", "en"), "1 June");
    assert.equal(dayMonth("bad"), "");
  });
});
