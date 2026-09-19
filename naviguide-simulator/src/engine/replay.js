/**
 * Replay narré de l'expédition (lot E, commentaire 5 du porteur) : rejouer la
 * route **de Saint-Maur à la position d'aujourd'hui** sur l'horloge officielle,
 * en racontant. Pur, testé : le temps rejoué avance à `secondsPerDay`, la
 * position vient de l'horloge, le vent des GRIB déjà journalisés, les cartes
 * des lignes du journal (escales, ZEE, AMP, ports d'entrée, météo, notes).
 * Rien n'est inventé : pas de ligne de journal, pas de carte.
 */
import { sampleClockAtTime } from "./voyageClock.js";
import { formatJournalEntry } from "./journalFormat.js";
import { LANE_NOW } from "./momentCard.js";

export const DEFAULT_SECONDS_PER_DAY = 1;
export const MIN_CARD_MS = 2500;
export const CARD_KINDS = new Set(["stop", "zee", "amp", "poe", "wx", "note"]);
const WIND_WINDOW_MS = 4 * 3600 * 1000;

function ms(iso) {
  const t = typeof iso === "number" ? iso : Date.parse(iso || "");
  return Number.isFinite(t) ? t : null;
}

/** Wall-clock milliseconds of replay per millisecond of expedition. */
export function replayScale(secondsPerDay = DEFAULT_SECONDS_PER_DAY) {
  return (Math.max(0.05, Number(secondsPerDay) || DEFAULT_SECONDS_PER_DAY) * 1000) / 86400000;
}

/** The replay window: from the official departure to now (never beyond). */
export function replayWindow(clock, nowMs) {
  const t0 = ms(clock?.t0);
  const end = Number.isFinite(nowMs) ? nowMs : Date.now();
  if (t0 == null || end <= t0) return null;
  return { startMs: t0, endMs: end, days: (end - t0) / 86400000 };
}

/** Advance the replayed instant by `dtMs` of wall clock; clamps at the end. */
export function advance(tMs, dtMs, window, secondsPerDay = DEFAULT_SECONDS_PER_DAY) {
  if (!window) return { tMs, done: true };
  const next = tMs + dtMs / replayScale(secondsPerDay);
  if (next >= window.endMs) return { tMs: window.endMs, done: true };
  return { tMs: next, done: false };
}

/** Journal entries (any shape the summary serves) sorted by time, once. */
export function journalTimeline(journal) {
  const all = [...(journal?.events || []), ...(journal?.latest || journal?.entries || [])];
  const seen = new Set();
  return all
    .filter((e) => {
      if (!e?.kind || ms(e.t) == null) return false;
      const id = e.id || `${e.kind}:${e.t}`;
      if (seen.has(id)) return false;
      seen.add(id);
      return true;
    })
    .sort((a, b) => ms(a.t) - ms(b.t));
}

/** The GRIB reading journaled closest to `tMs` (≤ 4 h away), or null. */
export function windFromJournalAt(timeline, tMs) {
  let best = null;
  let bestD = Infinity;
  for (const e of timeline) {
    if (e.kind !== "grib" || !Number.isFinite(e.windKnots)) continue;
    const d = Math.abs(ms(e.t) - tMs);
    if (d < bestD) { bestD = d; best = e; }
  }
  if (!best || bestD > WIND_WINDOW_MS) return null;
  return { windKnots: best.windKnots, dirFromDeg: best.dirFromDeg ?? null, hs: best.hs ?? null, model: best.model || null, kind: "forecast" };
}

/**
 * The boat at the replayed instant: the clock's sample, dated, with the wind
 * the journal recorded then. Same shape as the live sample the scene reads.
 */
export function replaySample(clock, tMs, timeline = []) {
  const s = sampleClockAtTime(clock, new Date(tMs));
  if (!s || !Number.isFinite(s.lat)) return null;
  const wind = windFromJournalAt(timeline, tMs);
  return {
    ...s,
    iso: new Date(tMs).toISOString(),
    replay: true,
    kind: wind ? "forecast" : "climatology",
    windKnots: wind ? wind.windKnots : (s.windKnots ?? null),
    dirFromDeg: wind ? wind.dirFromDeg : (s.dirFromDeg ?? null),
    hs: wind ? wind.hs : null,
    model: wind ? wind.model : null,
  };
}

const TITLE = {
  fr: { stop: "Escale", zee: "ZEE", amp: "Aire marine protégée", poe: "Port d’entrée", wx: "Météo au bateau", note: "Mot du skipper" },
  en: { stop: "Stopover", zee: "EEZ", amp: "Marine protected area", poe: "Port of entry", wx: "Weather at the boat", note: "Skipper's note" },
};

function dayLabel(iso, lang) {
  const t = ms(iso);
  if (t == null) return "";
  return new Date(t).toLocaleDateString(lang === "en" ? "en-GB" : "fr-FR", { day: "numeric", month: "long", timeZone: "UTC" });
}

/** A moment card (NOW lane) from a journal line — the text the journal already formats. */
export function cardFromJournalEntry(entry, lang = "fr") {
  if (!entry || !CARD_KINDS.has(entry.kind)) return null;
  const f = formatJournalEntry(entry, lang);
  const words = TITLE[lang === "en" ? "en" : "fr"];
  const when = dayLabel(entry.t, lang);
  const hasPos = Number.isFinite(entry.lat) && Number.isFinite(entry.lon);
  return {
    key: `replay:${entry.id || `${entry.kind}:${entry.t}`}`,
    lane: LANE_NOW,
    origin: "journal",
    kind: entry.kind,
    type: `replay-${entry.kind}`,
    severity: entry.kind === "wx" ? "alert" : "info",
    title: `${words[entry.kind] || entry.kind}${when ? ` · ${when}` : ""}`,
    text: f.text,
    entity: hasPos
      ? { id: `replay:${entry.kind}:${entry.name || entry.t}`, kind: entry.kind === "poe" ? "poe" : (entry.kind === "amp" ? "amp" : "place"), name: entry.name || words[entry.kind], rawName: entry.name || "", lat: entry.lat, lon: entry.lon, nm: 0, url: entry.url || entry.visitUrl || null, source: entry.basis || null }
      : null,
    whenNm: 0,
    at: entry.t,
  };
}

/**
 * Journal lines that fall in (fromMs, toMs], as cards, in order. A ZEE
 * *exit* is not a card: entering the next zone (or nothing, high seas) says
 * it, and a replay has one second per day to spend.
 */
export function cardsBetween(timeline, fromMs, toMs, lang = "fr") {
  const out = [];
  for (const e of timeline) {
    const t = ms(e.t);
    if (t == null || t <= fromMs || t > toMs) continue;
    if (e.kind === "zee" && e.event === "exit") continue;
    const card = cardFromJournalEntry(e, lang);
    if (card) out.push(card);
  }
  return out;
}

/** Stops, weather and notes matter more than the tenth port of entry: keep the queue short. */
export const QUEUE_MAX = 4;
const LOW_PRIORITY = new Set(["poe", "zee", "amp"]);

export function trimQueue(queue, max = QUEUE_MAX) {
  if (queue.length <= max) return queue;
  const kept = [];
  let toDrop = queue.length - max;
  for (const card of queue) {
    if (toDrop > 0 && LOW_PRIORITY.has(card.kind)) { toDrop -= 1; continue; }
    kept.push(card);
  }
  return kept.slice(-max);
}

/** How long a card may stay: the queue must not fall behind the replay. */
export function cardDwellMs(queueLength, { min = 900, max = MIN_CARD_MS } = {}) {
  if (queueLength <= 0) return max;
  return Math.max(min, Math.round(max / Math.max(1, queueLength)));
}

/** 0 → 1 along the replay. */
export function replayProgress(tMs, window) {
  if (!window || window.endMs <= window.startMs) return 0;
  return Math.max(0, Math.min(1, (tMs - window.startMs) / (window.endMs - window.startMs)));
}
