import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  advance, cardDwellMs, cardFromJournalEntry, cardsBetween, journalTimeline, replayProgress, replaySample, replayScale, replayWindow, trimQueue, windFromJournalAt,
} from "./replay.js";
const T0 = "2026-05-15T08:00:00.000Z";

/** A hand-made official clock: La Rochelle → 230 nm SW in 29 h → Ajaccio at 125 h, 3 days alongside. */
function clock() {
  const v = (tHours, filmNm, lat, lon, extra = {}) => ({
    tHours, filmNm, sailNm: filmNm, lat, lon, bearing: 240, speedKnots: 8, vehicle: "main", seaHours: tHours, kind: "climatology", windKnots: 11, ...extra,
  });
  return {
    t0: T0,
    vertices: [
      v(0, 0, 46.15, -1.16),
      v(29, 230, 44.0, -6.0),
      v(125, 1000, 41.9, 8.7),
      v(197, 1000, 41.9, 8.7, { vehicle: "quay", speedKnots: null }),
    ],
    marks: [
      { name: "La Rochelle", nm: 0, filmNm: 0, lat: 46.15, lon: -1.16, tHours: 0, holdHours: 0 },
      { name: "Ajaccio (Corse)", nm: 1000, filmNm: 1000, lat: 41.9, lon: 8.7, tHours: 125, holdHours: 72 },
    ],
  };
}

describe("replay — rejouer la route de Saint-Maur à aujourd'hui", () => {
  it("window runs from the official departure to now, never beyond; time advances at seconds-per-day", () => {
    const now = Date.parse("2026-05-25T08:00:00Z");
    const w = replayWindow({ t0: T0 }, now);
    assert.equal(w.days, 10);
    assert.equal(replayWindow({ t0: T0 }, Date.parse("2026-05-14T00:00:00Z")), null, "before departure: nothing to replay");
    // 1 s of wall clock = 1 day of expedition.
    const a = advance(w.startMs, 1000, w, 1);
    assert.equal(a.done, false);
    assert.equal(Math.round((a.tMs - w.startMs) / 3600000), 24);
    // Clamps at now and says so.
    const b = advance(w.startMs, 20_000, w, 1);
    assert.equal(b.done, true);
    assert.equal(b.tMs, w.endMs);
    assert.equal(replayProgress(a.tMs, w), 0.1);
    assert.ok(replayScale(2) > replayScale(1));
  });

  it("the sample at a replayed instant comes from the clock, dated, with the journaled wind when there is one", () => {
    const c = clock();
    const tl = journalTimeline({ latest: [
      { id: "grib:1", kind: "grib", t: "2026-05-16T06:00:00Z", windKnots: 14, dirFromDeg: 250, hs: 1.2, model: "GFS" },
      { id: "grib:1", kind: "grib", t: "2026-05-16T06:00:00Z", windKnots: 14 }, // duplicate dropped
    ] });
    assert.equal(tl.length, 1);
    const t = Date.parse("2026-05-16T07:00:00Z");
    const s = replaySample(c, t, tl);
    assert.ok(s && Number.isFinite(s.lat) && Number.isFinite(s.lon));
    assert.equal(s.iso, "2026-05-16T07:00:00.000Z");
    assert.equal(s.replay, true);
    assert.equal(s.kind, "forecast");
    assert.equal(s.windKnots, 14);
    // Five hours later, out of the 4 h window: the clock's typical wind, labelled so.
    const far = replaySample(c, Date.parse("2026-05-16T12:00:00Z"), tl);
    assert.equal(far.kind, "climatology");
    assert.equal(windFromJournalAt(tl, Date.parse("2026-05-20T00:00:00Z")), null);
  });

  it("journal lines become cards in order; positions and notes travel; grib and positions are not cards", () => {
    const tl = journalTimeline({ events: [
      { id: "zee:1", kind: "zee", t: "2026-05-15T20:00:00Z", event: "enter", name: "Spanish Exclusive Economic Zone", lat: 45.0, lon: -3.0 },
      { id: "poe:1", kind: "poe", t: "2026-05-15T09:00:00Z", event: "passed", name: "La Rochelle - La Pallice", nm: 1.6, lat: 46.16, lon: -1.22 },
      { id: "grib:1", kind: "grib", t: "2026-05-15T12:00:00Z", windKnots: 10 },
      { id: "position:x", kind: "position", t: "2026-05-15T12:00:00Z", lat: 46, lon: -2 },
      { id: "wx:1", kind: "wx", t: "2026-05-17T06:00:00Z", event: "gale", windKnots: 36, dirFromDeg: 250, hs: 2 },
      { id: "note:1", kind: "note", t: "2026-05-16T10:00:00Z", text: "Belle étoile.", author: "Clément" },
    ] });
    const cards = cardsBetween(tl, Date.parse("2026-05-15T08:00:00Z"), Date.parse("2026-05-16T12:00:00Z"), "fr");
    assert.deepEqual(cards.map((c) => c.kind), ["poe", "zee", "note"]);
    assert.equal(cards[0].title, "Port d’entrée · 15 mai");
    assert.equal(cards[0].text, "Port d’entrée passé : La Rochelle - La Pallice (1,6 nm)");
    assert.equal(cards[0].entity.kind, "poe");
    assert.equal(cards[2].text, "Clément : Belle étoile.");
    assert.equal(cards[2].entity, null);
    const gale = cardFromJournalEntry(tl.find((e) => e.kind === "wx"), "en");
    assert.equal(gale.severity, "alert");
    assert.match(gale.title, /Weather at the boat · 17 May/);
    assert.equal(cardFromJournalEntry({ kind: "grib", t: "2026-05-15T12:00:00Z" }), null);
    assert.equal(cardsBetween(tl, 0, 0).length, 0);
    // A ZEE exit is not a card (the next entry says it).
    const exits = journalTimeline({ events: [{ id: "zee:x", kind: "zee", t: "2026-05-15T21:00:00Z", event: "exit", name: "French EEZ" }] });
    assert.equal(cardsBetween(exits, 0, Date.parse("2026-05-16T00:00:00Z")).length, 0);
  });

  it("the queue never lags the boat: low-priority cards are dropped first, dwell shrinks with the backlog", () => {
    const mk = (kind, i) => ({ key: `${kind}:${i}`, kind });
    const q = [mk("poe", 1), mk("stop", 2), mk("zee", 3), mk("wx", 4), mk("poe", 5), mk("note", 6), mk("amp", 7)];
    const trimmed = trimQueue(q, 4);
    assert.equal(trimmed.length, 4);
    assert.deepEqual(trimmed.map((c) => c.kind), ["stop", "wx", "note", "amp"], "stops, weather and notes survive; ports of entry go first");
    assert.equal(trimQueue([mk("stop", 1)], 4).length, 1);
    assert.equal(cardDwellMs(0), 2500);
    assert.equal(cardDwellMs(1), 2500);
    assert.equal(cardDwellMs(5), 900);
  });
});
