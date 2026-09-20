import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  formatDay,
  formatJournalEntry,
  formatLatLon,
  formatTimeUtc,
  groupJournalByDay,
} from "./journalFormat.js";

describe("journalFormat", () => {
  it("formats coordinates in both languages", () => {
    assert.equal(formatLatLon(46.15, -1.16, "fr"), "46,15° N · 1,16° O");
    assert.equal(formatLatLon(46.15, -1.16, "en"), "46.15° N · 1.16° W");
    assert.equal(formatLatLon(-14.6, 61.07, "en"), "14.60° S · 61.07° E");
    assert.equal(formatLatLon(null, 1), "");
  });

  it("formats time and day", () => {
    assert.equal(formatTimeUtc("2026-05-16T06:00:00Z"), "06:00 UTC");
    assert.equal(formatTimeUtc(""), "");
    assert.equal(formatDay("2026-05-16", "fr"), "16 mai 2026");
    assert.equal(formatDay("2026-05-16", "en"), "16 May 2026");
  });

  it("position: place, miles and state — nothing invented", () => {
    const f = formatJournalEntry({ kind: "position", t: "2026-05-16T12:00:00Z", lat: 45.2, lon: -3.9, sailNm: 142.3, vehicle: "main", status: "live" }, "fr");
    assert.equal(f.icon, "📍");
    assert.equal(f.time, "12:00 UTC");
    assert.equal(f.text, "45,20° N · 3,90° O · 142 nm · en mer");
    const quay = formatJournalEntry({ kind: "position", t: "2026-05-15T06:00:00Z", lat: 46.15, lon: -1.16, sailNm: 0, status: "waiting" }, "en");
    assert.equal(quay.text, "46.15° N · 1.16° W · 0 nm · before departure");
    const noNm = formatJournalEntry({ kind: "position", t: "2026-05-15T06:00:00Z", lat: 46.15, lon: -1.16, atQuay: true }, "fr");
    assert.equal(noNm.text, "46,15° N · 1,16° O · à quai");
  });

  it("stop, grib and note", () => {
    assert.equal(
      formatJournalEntry({ kind: "stop", t: "2026-06-05T09:00:00Z", event: "arrival", name: "Fort-de-France", holdHours: 72 }, "fr").text,
      "Arrivée à Fort-de-France · 3 jours à quai",
    );
    assert.equal(
      formatJournalEntry({ kind: "stop", t: "2026-06-08T09:00:00Z", event: "departure", name: "Fort-de-France" }, "en").text,
      "Departure from Fort-de-France",
    );
    const g = formatJournalEntry({ kind: "grib", t: "2026-05-17T06:00:00Z", windKnots: 14.2, dirFromDeg: 250, pressHpa: 1013.2, hs: 1.1, rainMm: 0, model: "GFS" }, "fr");
    assert.equal(g.icon, "🌬");
    assert.equal(g.text, "Vent 14 kn de OSO · 1013 hPa · Hs 1,1 m (GFS)");
    const gEn = formatJournalEntry({ kind: "grib", t: "2026-05-17T06:00:00Z", windKnots: 14.2, dirFromDeg: 250, rainMm: 2.5 }, "en");
    assert.equal(gEn.text, "Wind 14 kn from WSW · rain 2.5 mm");
    assert.equal(formatJournalEntry({ kind: "grib", t: "2026-05-17T06:00:00Z" }, "fr").text, "GRIB reçu");
    assert.equal(formatJournalEntry({ kind: "note", t: "2026-05-17T07:00:00Z", text: "Largué les amarres.", author: "Clément" }, "fr").text, "Clément : Largué les amarres.");
    assert.equal(formatJournalEntry({ kind: "weird", t: "2026-05-17T07:00:00Z" }, "fr").text, "weird");
  });

  it("v2: ZEE crossings and MPA neighbourhoods read on the pearls", () => {
    const z = formatJournalEntry({ kind: "zee", t: "2026-05-17T07:00:00Z", event: "enter", name: "Spanish Exclusive Economic Zone" }, "fr");
    assert.equal(z.icon, "🛂");
    assert.equal(z.text, "Entrée dans Spanish Exclusive Economic Zone");
    assert.equal(formatJournalEntry({ kind: "zee", t: "2026-05-20T07:00:00Z", event: "exit", name: "Spanish Exclusive Economic Zone" }, "en").text, "Left Spanish Exclusive Economic Zone — high seas");
    assert.equal(formatJournalEntry({ kind: "amp", t: "2026-05-16T07:00:00Z", event: "nearby", name: "Pertuis Charentais", nm: 3.6 }, "fr").text, "Aire marine protégée à portée : Pertuis Charentais (3,6 nm)");
  });

  it("groups newest day first and caps the number of days", () => {
    const entries = [
      { id: "a", kind: "note", t: "2026-05-18T07:00:00Z", text: "c" },
      { id: "b", kind: "position", t: "2026-05-17T12:00:00Z", lat: 1, lon: 2 },
      { id: "c", kind: "position", t: "2026-05-17T06:00:00Z", lat: 1, lon: 2 },
      { id: "d", kind: "position", t: "2026-05-16T06:00:00Z", lat: 1, lon: 2 },
    ];
    const groups = groupJournalByDay(entries, "fr", { maxDays: 2 });
    assert.deepEqual(groups.map((g) => g.day), ["2026-05-18", "2026-05-17"]);
    assert.equal(groups[1].entries.length, 2);
    assert.equal(groups[0].label, "18 mai 2026");
    assert.equal(groups[1].entries[0].id, "b");
  });
});
