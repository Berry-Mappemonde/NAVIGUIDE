/**
 * Replay narré de l'expédition (lot E, commentaire 5 du porteur) : rejouer la
 * route **de Saint-Maur à la position d'aujourd'hui** sur l'horloge officielle,
 * en racontant. Pur, testé : le temps rejoué avance à `secondsPerDay`, la
 * position vient de l'horloge, le vent des GRIB déjà journalisés, les cartes
 * des lignes du journal (escales, ZEE, AMP, ports d'entrée, météo, notes).
 * Rien n'est inventé : pas de ligne de journal, pas de carte.
 */
import { DEFAULT_T0_ISO, sampleClockAtTime } from "./voyageClock.js";
import { expeditionStory, officialDatedStops } from "./expeditionStory.js";
import { cardFromJournalEntry, JOURNAL_CARD_KINDS } from "./momentCard.js";
import { unwrapLon } from "../utils/geo.js";

export { cardFromJournalEntry };
export const CARD_KINDS = JOURNAL_CARD_KINDS;

export const DEFAULT_SECONDS_PER_DAY = 1;
export const MIN_CARD_MS = 2500;
export const FILM_TARGET_SECONDS = 150;
export const FILM_TARGET_SECONDS_LONG = 180;
export const FILM_RATE_MIN = 0.9;
export const FILM_RATE_MAX = 1.25;
export const FILM_CALIBRATE_SLACK_S = 8;
export const FILM_ZOOM_MIN = 3;
export const FILM_ZOOM_MAX = 7;
export const FILM_FLY_SECONDS = 1.2;
export const FILM_VIEW_HZ = 30;
export const FILM_MIN_CHAPTER_SECONDS = 12;
export const FILM_RECALE_MS = 300;
export const FILM_BEHIND_SPEED = 0.7;
export const FILM_PAN_MAX_SCREEN = 0.02;
const WIND_WINDOW_MS = 4 * 3600 * 1000;

function lerpNum(a, b, t) {
  const x = Number(a);
  const y = Number(b);
  if (!Number.isFinite(x)) return y;
  if (!Number.isFinite(y)) return x;
  return x + t * (y - x);
}

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
/**
 * Position le long du trait (sommets consécutifs, lon dépliée).
 * Continue aux sommets : limite à gauche = limite à droite.
 */
export function positionAt(clock, tMs) {
  const verts = clock?.vertices || [];
  if (!verts.length) return null;
  const t0 = Date.parse(clock.t0);
  if (!Number.isFinite(t0) || !Number.isFinite(tMs)) return null;
  const tHours = (tMs - t0) / 3600000;
  const pts = [];
  let prevLon = null;
  for (const v of verts) {
    if (!Number.isFinite(v.lat) || !Number.isFinite(v.lon) || !Number.isFinite(v.tHours)) continue;
    const lon = prevLon == null ? v.lon : unwrapLon(prevLon, v.lon);
    pts.push({ lat: v.lat, lon, tHours: v.tHours, sailNm: v.sailNm, filmNm: v.filmNm });
    prevLon = lon;
  }
  if (!pts.length) return null;
  if (tHours <= pts[0].tHours) {
    return { lat: pts[0].lat, lon: pts[0].lon, sailNm: pts[0].sailNm, filmNm: pts[0].filmNm };
  }
  const last = pts[pts.length - 1];
  if (tHours >= last.tHours) {
    return { lat: last.lat, lon: last.lon, sailNm: last.sailNm, filmNm: last.filmNm };
  }
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i];
    const b = pts[i + 1];
    if (tHours > b.tHours) continue;
    const span = b.tHours - a.tHours;
    if (!(span > 1e-12)) {
      return { lat: b.lat, lon: b.lon, sailNm: b.sailNm, filmNm: b.filmNm };
    }
    const u = (tHours - a.tHours) / span;
    return {
      lat: a.lat + u * (b.lat - a.lat),
      lon: a.lon + u * (b.lon - a.lon),
      sailNm: lerpNum(a.sailNm, b.sailNm, u),
      filmNm: lerpNum(a.filmNm, b.filmNm, u),
    };
  }
  return { lat: last.lat, lon: last.lon, sailNm: last.sailNm, filmNm: last.filmNm };
}

/** Expedition-ms per wall-second for a planned chapter (F1 share). */
export function chapterNominalRate(chapter) {
  const seconds = Number(chapter?.seconds);
  const span = Number(chapter?.tB) - Number(chapter?.tA);
  if (!(seconds > 0) || !Number.isFinite(span) || span <= 0) return 0;
  return span / seconds;
}

/**
 * One rAF step of replayed time. Nominal advance ; onboundary target
 * recales in ≤ 300 ms ; never a visible backward jump (0.7× if behind).
 */
export function advanceReplayTime({
  t,
  dt,
  chapter,
  targetT = null,
  recaleRemainMs = 0,
} = {}) {
  const nominal = chapterNominalRate(chapter);
  const wall = Math.max(0, Number(dt) || 0);
  const tA = Number(chapter?.tA);
  const tB = Number(chapter?.tB);
  let next = Number(t);
  if (!Number.isFinite(next)) next = Number.isFinite(tA) ? tA : 0;
  let remain = Math.max(0, Number(recaleRemainMs) || 0);
  const hasTarget = targetT != null && Number.isFinite(Number(targetT));
  const target = hasTarget ? Number(targetT) : null;

  if (hasTarget && target < next - 1e-9) {
    next += wall * nominal * FILM_BEHIND_SPEED;
    remain = 0;
  } else if (hasTarget && target > next + 1e-9 && remain > 0) {
    const blend = Math.min(1, (wall * 1000) / remain);
    next += (target - next) * blend;
    remain = Math.max(0, remain - wall * 1000);
    if (remain <= 1e-6) {
      next = target;
      remain = 0;
    }
  } else {
    next += wall * nominal;
    remain = Math.max(0, remain - wall * 1000);
  }

  if (Number.isFinite(tA)) next = Math.max(tA, next);
  if (Number.isFinite(tB)) next = Math.min(tB, next);
  return { t: next, recaleRemainMs: remain };
}

export function replaySample(clock, tMs, timeline = []) {
  const s = sampleClockAtTime(clock, new Date(tMs));
  if (!s || !Number.isFinite(s.lat)) return null;
  const pos = positionAt(clock, tMs);
  const wind = windFromJournalAt(timeline, tMs);
  return {
    ...s,
    ...(pos && Number.isFinite(pos.lat) ? {
      lat: pos.lat,
      lon: pos.lon,
      sailNm: Number.isFinite(pos.sailNm) ? pos.sailNm : s.sailNm,
      filmNm: Number.isFinite(pos.filmNm) ? pos.filmNm : s.filmNm,
    } : {}),
    iso: new Date(tMs).toISOString(),
    replay: true,
    kind: wind ? "forecast" : "climatology",
    windKnots: wind ? wind.windKnots : (s.windKnots ?? null),
    dirFromDeg: wind ? wind.dirFromDeg : (s.dirFromDeg ?? null),
    hs: wind ? wind.hs : null,
    model: wind ? wind.model : null,
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

export function clampFilmRate(rate) {
  const n = Number(rate);
  if (!Number.isFinite(n)) return 1;
  return Math.max(FILM_RATE_MIN, Math.min(FILM_RATE_MAX, n));
}

/**
 * After chapter 1, scale `utterance.rate` so the remaining characters land
 * on the leftover budget. Always clamped to [0.9, 1.25].
 */
export function calibrateRate({
  chapterChars,
  elapsedSeconds,
  remainingChars,
  remainingBudgetSeconds,
} = {}) {
  const chars = Number(chapterChars);
  const elapsed = Number(elapsedSeconds);
  if (!(chars > 0) || !(elapsed > 0)) return 1;
  const remaining = Number(remainingChars) || 0;
  const budget = Number(remainingBudgetSeconds);
  if (!(remaining > 0)) return 1;
  if (!(budget > 0)) return FILM_RATE_MAX;
  const estimated = remaining / (chars / elapsed);
  return clampFilmRate(estimated / budget);
}

function markPos(mark, byName, clock, t, live) {
  const raw = mark ? (byName.get(mark.name) || mark) : null;
  if (Number.isFinite(raw?.lat) && Number.isFinite(raw?.lon)) {
    return { lat: raw.lat, lon: raw.lon };
  }
  if (clock) {
    const s = sampleClockAtTime(clock, new Date(t));
    if (s && Number.isFinite(s.lat)) return { lat: s.lat, lon: s.lon };
  }
  if (Number.isFinite(live?.lat) && Number.isFinite(live?.lon)) {
    return { lat: live.lat, lon: live.lon };
  }
  return { lat: null, lon: null };
}

function marksWithIso(marks, clock) {
  const raw = marks?.length ? marks : (clock?.marks || []);
  const clockMarks = clock?.marks || [];
  return (raw || []).map((m) => {
    if (m?.iso) return m;
    const film = Number(m?.filmNm ?? m?.nm);
    const hit = clockMarks.find((c) => (
      Number.isFinite(film) && Math.abs((c.filmNm ?? c.nm) - film) < 0.6 && (!m?.name || c.name === m.name)
    )) || clockMarks.find((c) => m?.name && c.name === m.name);
    return hit ? { ...m, iso: hit.iso, holdHours: hit.holdHours } : m;
  });
}

/**
 * Chapitres = jambes entre escales du récit existant (lot F1 ; F3 apportera
 * le script rédigé). Chaque chapitre porte [tA, tB] et le texte de la jambe.
 */
export function filmChaptersFromStory({
  clock, marks, live, journal = null, lang = "fr", nowMs, t0: storyT0,
} = {}) {
  const merged = marksWithIso(marks, clock);
  const dated = officialDatedStops(merged, clock);
  const byName = new Map((merged || []).map((m) => [m.name, m]));
  const t0 = Date.parse(DEFAULT_T0_ISO);
  const tEnd = ms(live?.iso) || nowMs || Date.now();
  if (t0 == null || !(tEnd > t0)) return [];

  const paragraphs = expeditionStory({
    clock, marks: merged, live, journal, now: live?.iso || tEnd, lang, t0: storyT0,
  }).map((p) => String(p || "").trim()).filter(Boolean);

  const stops = dated.length ? dated : [{ name: "Saint-Maur", iso: clock?.t0, filmNm: 0 }];
  const intervals = [];
  for (let i = 0; i < stops.length; i++) {
    const from = stops[i];
    const to = stops[i + 1];
    const tA = ms(from.iso) ?? (i === 0 ? t0 : null);
    if (tA == null || tA >= tEnd) break;
    const rawB = to ? ms(to.iso) : tEnd;
    const tB = Math.min(rawB == null ? tEnd : rawB, tEnd);
    if (tB <= tA) continue;
    const fromPos = markPos(from, byName, clock, tA, live);
    const toPos = markPos(to || live, byName, clock, tB, live);
    intervals.push({
      id: `leg-${i}`,
      fromName: from.name || "",
      toName: (to && tB < tEnd) ? (to.name || "") : "",
      tA,
      tB,
      fromLat: fromPos.lat,
      fromLon: fromPos.lon,
      toLat: toPos.lat,
      toLon: toPos.lon,
    });
    if (!to || (ms(to.iso) != null && ms(to.iso) >= tEnd)) break;
  }
  if (!intervals.length) {
    const a = markPos(null, byName, clock, t0, live);
    const b = markPos(null, byName, clock, tEnd, live);
    intervals.push({
      id: "leg-0",
      fromName: "Saint-Maur",
      toName: "",
      tA: t0,
      tB: tEnd,
      fromLat: a.lat,
      fromLon: a.lon,
      toLat: b.lat,
      toLon: b.lon,
    });
  }

  return intervals.map((leg, i) => {
    let text = "";
    if (i === 0) text = paragraphs[0] || "";
    else if (i < intervals.length - 1) text = paragraphs[i] || paragraphs[0] || "";
    else text = paragraphs.slice(Math.min(i, paragraphs.length - 1)).join(" ") || paragraphs[0] || "";
    return { ...leg, text };
  });
}

export function chapterAtElapsed(plan, elapsedSeconds) {
  const list = plan?.chapters || [];
  if (!list.length) return null;
  const t = Math.max(0, Number(elapsedSeconds) || 0);
  for (const ch of list) {
    if (t < ch.endWall - 1e-9) return ch;
  }
  return list[list.length - 1];
}

/**
 * Répartit `targetSeconds` au prorata des caractères. `timeAt(i, charIdx)`
 * est monotone : le bateau ne recule jamais.
 */
export function filmPlan({ chapters, targetSeconds = FILM_TARGET_SECONDS } = {}) {
  const target = Number(targetSeconds);
  const seconds = Number.isFinite(target) && target > 0 ? target : FILM_TARGET_SECONDS;
  const list = (chapters || []).filter((c) => c && (ms(c.tA) != null) && (ms(c.tB) != null) && ms(c.tB) > ms(c.tA));
  const weights = list.map((c) => Math.max(1, String(c.text || "").length));
  const totalChars = weights.reduce((s, n) => s + n, 0) || 1;
  let startWall = 0;
  const planned = list.map((c, i) => {
    const chars = weights[i];
    const share = i === list.length - 1
      ? Math.max(0, seconds - startWall)
      : (chars / totalChars) * seconds;
    const tA = ms(c.tA);
    const tB = ms(c.tB);
    const row = {
      ...c,
      idx: i,
      chars,
      seconds: share,
      startWall,
      endWall: startWall + share,
      tA,
      tB,
    };
    startWall += share;
    return row;
  });
  const merged = mergeShortChapters(planned, FILM_MIN_CHAPTER_SECONDS);

  function timeAt(chapterIdx, charIdx) {
    if (!merged.length) return null;
    const i = Math.max(0, Math.min(merged.length - 1, Number(chapterIdx) || 0));
    const ch = merged[i];
    const span = Math.max(1, ch.chars);
    const frac = Math.max(0, Math.min(1, Number(charIdx) / span));
    return ch.tA + frac * (ch.tB - ch.tA);
  }

  return { chapters: merged, targetSeconds: seconds, totalChars, timeAt };
}

export function mergeShortChapters(planned, minSeconds = FILM_MIN_CHAPTER_SECONDS) {
  if (!planned?.length) return [];
  const out = [];
  for (const ch of planned) {
    const prev = out[out.length - 1];
    if (prev && (prev.seconds < minSeconds || ch.seconds < minSeconds)) {
      const offset = (prev.text || "").length + (prev.text && ch.text ? 1 : 0);
      prev.text = [prev.text, ch.text].filter(Boolean).join(" ");
      prev.events = [
        ...(prev.events || []),
        ...((ch.events || []).map((e) => ({ ...e, charIdx: (Number(e.charIdx) || 0) + offset }))),
      ];
      prev.tB = ch.tB;
      prev.toName = ch.toName;
      prev.toLat = ch.toLat;
      prev.toLon = ch.toLon;
      prev.chars += ch.chars;
      prev.seconds += ch.seconds;
      prev.endWall = ch.endWall;
    } else {
      out.push({ ...ch });
    }
  }
  return out.map((c, i) => ({ ...c, idx: i }));
}

export function publishFilmStart(targetSeconds) {
  if (typeof window === "undefined") return;
  window.__naviguideFilm = {
    startedAt: performance.now(),
    ended: false,
    targetSeconds,
  };
}

export function publishFilmEnd() {
  if (typeof window === "undefined") return;
  const prev = window.__naviguideFilm || {};
  const endedAt = performance.now();
  const elapsed = Number.isFinite(prev.startedAt) ? (endedAt - prev.startedAt) / 1000 : null;
  window.__naviguideFilm = { ...prev, ended: true, endedAt, elapsed };
  try {
    window.dispatchEvent(new CustomEvent("naviguide-film-end", { detail: window.__naviguideFilm }));
  } catch { /* jsdom */ }
}
