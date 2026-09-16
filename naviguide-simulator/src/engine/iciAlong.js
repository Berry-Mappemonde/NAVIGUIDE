/**
 * Lookahead on the planned GPS track of THIS leg.
 * Pearls every ROUTE_SAMPLE_NM. Not the globe. No chat.
 */

import { interpolateAtNm } from "./routePlayhead.js";
import {
  AMP_AHEAD_MIN_NM,
  ROUTE_SAMPLE_NM,
  MARINA_REFUGE_NM,
} from "./eventRules.js";

export { AMP_AHEAD_MIN_NM };
export const ALONG_AMP_NM = 15;
export const ALONG_MARINA_NM = MARINA_REFUGE_NM;
export const SUIVRE_LOOKAHEAD_H = 36;
export const SUIVRE_LOOKAHEAD_MAX_NM = 350;
export const MAX_PEARLS_SIM = 60;
export const MAX_PEARLS_SUIVRE = 24;
export const DEFAULT_KNOTS = 7;

export function pearlKey(lat, lon, month) {
  const la = Number(lat);
  const lo = Number(lon);
  if (!Number.isFinite(la) || !Number.isFinite(lo)) return "";
  return `${la.toFixed(2)}:${lo.toFixed(2)}:${month ?? ""}`;
}

export function lookaheadNmFor(mode, knots) {
  if (mode === "suivre") {
    const kn = Number.isFinite(knots) && knots > 0 ? knots : DEFAULT_KNOTS;
    return Math.min(SUIVRE_LOOKAHEAD_H * kn, SUIVRE_LOOKAHEAD_MAX_NM);
  }
  return Infinity;
}

export function filmCumAtNm(flat, nm) {
  const pts = flat?.points || [];
  if (!pts.length) return Number(nm) || 0;
  const target = Number(nm) || 0;
  if (pts.length === 1) return pts[0].filmCum ?? pts[0].cumNm ?? 0;
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i];
    const b = pts[i + 1];
    if (b.cumNm < target) continue;
    if (b.jump) return b.filmCum ?? b.cumNm;
    const span = b.cumNm - a.cumNm;
    const t = span > 0 ? (target - a.cumNm) / span : 1;
    const fa = a.filmCum ?? a.cumNm;
    const fb = b.filmCum ?? b.cumNm;
    return fa + t * (fb - fa);
  }
  return pts[pts.length - 1].filmCum ?? pts[pts.length - 1].cumNm ?? target;
}

/**
 * Sample THIS leg ahead of the boat. Skip air hops / non-maritime.
 */
export function sampleLeg(flat, {
  fromNm = 0,
  toNm = Infinity,
  boatNm = 0,
  sampleNm = ROUTE_SAMPLE_NM,
  maxPearls = MAX_PEARLS_SIM,
  lookaheadNm = Infinity,
  month = null,
} = {}) {
  const start = Math.max(Number(fromNm) || 0, Number(boatNm) || 0);
  const cap = Number.isFinite(lookaheadNm) ? start + lookaheadNm : Infinity;
  const end = Math.min(
    Number.isFinite(toNm) ? toNm : Infinity,
    cap,
    flat?.totalNm ?? Infinity,
  );
  const step = Number(sampleNm) > 0 ? sampleNm : ROUTE_SAMPLE_NM;
  const max = Math.max(1, maxPearls);
  const pearls = [];
  if (!flat?.points?.length || end < start) return pearls;
  for (let nm = start; nm <= end + 1e-6 && pearls.length < max; nm += step) {
    const hit = interpolateAtNm(flat, nm);
    if (!hit || hit.jump || hit.nonMaritime) continue;
    pearls.push({
      lat: hit.lat,
      lon: hit.lon,
      cumNm: nm,
      filmCum: filmCumAtNm(flat, nm),
      whenNm: nm - (Number(boatNm) || 0),
      month,
    });
  }
  return pearls;
}

export function attachBags(pearls, bagMap, month) {
  const map = bagMap instanceof Map ? bagMap : new Map(Object.entries(bagMap || {}));
  return (pearls || []).map((p) => {
    const bag = map.get(pearlKey(p.lat, p.lon, month ?? p.month))
      || map.get(pearlKey(p.lat, p.lon, p.month))
      || null;
    const amp = (bag?.amp || []).filter((a) => !Number.isFinite(a.nm) || a.nm <= ALONG_AMP_NM);
    const harbours = [
      ...(bag?.nearby?.marinas || []),
      ...(bag?.nearby?.capitaineries || []),
      ...(bag?.nearby?.wpi || []),
    ].filter((h) => Number.isFinite(h?.nm) && h.nm < ALONG_MARINA_NM && h.name);
    return {
      ...p,
      zee: bag?.zee ?? null,
      poe: bag?.poe || [],
      amp,
      harbours,
    };
  });
}

export function alongHarbours(pearls) {
  const list = [];
  for (const p of pearls || []) {
    for (const h of p.harbours || []) {
      list.push({
        ...h,
        nm: (p.whenNm ?? 0) + (Number(h.nm) || 0),
        along: true,
      });
    }
  }
  list.sort((a, b) => a.nm - b.nm);
  return list;
}

export function buildAlongIndex(pearls, bagMap, month) {
  const decorated = attachBags(pearls, bagMap, month);
  return {
    pearls: decorated,
    harbours: alongHarbours(decorated),
  };
}

/** Simulation: all visible on this leg. Suivre: live + one upcoming. */
export function filmEventMarks(events, { mode = "simulation" } = {}) {
  const visible = (events || []).filter((e) => (
    e && e.judge !== "hide" && e.type !== "group" && Number.isFinite(e.filmCum)
  ));
  if (mode !== "suivre") return visible;
  const nows = visible.filter((e) => e.judge === "now");
  const later = visible
    .filter((e) => e.judge === "later" || e.judge === "group")
    .sort((a, b) => (a.whenNm ?? 0) - (b.whenNm ?? 0));
  const out = [];
  if (nows.length) out.push(nows[nows.length - 1]);
  if (later[0]) out.push(later[0]);
  return out;
}

export function upsertLedger(ledger, incoming) {
  const out = [...(ledger || [])];
  for (const ev of incoming || []) {
    if (!ev || ev.judge === "hide") continue;
    const key = ev.stableKey || ev.id;
    const idx = out.findIndex((x) => (x.stableKey || x.id) === key);
    if (idx >= 0) {
      const prev = out[idx];
      const next = { ...prev, ...ev };
      const keepStory = prev.story
        && (prev.story.status === "pending" || prev.story.status === "ready")
        && (!ev.story || ev.story.status === "template");
      if (keepStory) {
        next.story = prev.story;
        if (prev.story.status === "ready" && prev.story.text) next.phrase = prev.story.text;
      }
      out[idx] = next;
    } else out.push(ev);
  }
  return out;
}

export function promoteLaterAtPlayhead(ledger, filmCum) {
  if (!Number.isFinite(filmCum)) return ledger || [];
  return (ledger || []).map((ev) => {
    if (ev.judge !== "later" || ev.promoted || ev.seenNow) return ev;
    if (!Number.isFinite(ev.filmCum) || filmCum + 0.5 < ev.filmCum) return ev;
    return { ...ev, judge: "now", promoted: true, seenNow: true, judgeReason: "playhead" };
  });
}
