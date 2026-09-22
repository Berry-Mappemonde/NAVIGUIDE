import { useEffect, useMemo, useState } from "react";
import { reviewPlan, reviewLeg } from "../engine/planReview.js";
import planAdviceFixture from "../fixtures/planAdvice.json" with { type: "json" };

const API_URL = import.meta.env?.VITE_API_URL ?? "";
const REFRESH_MS = 10 * 60 * 1000;
/** Même plancher que voyage_clock.PLANNING_MIN_KN / skipperOrders.PLANNING_MIN_KN. */
export const ETA_MIN_KN = 3;
/** Plafond p90 − p10 (lot RA7) : quelques jours, jamais des mois. */
export const ETA_MAX_SPAN_DAYS = 7;
/** Recul progressif tant que l'ensemble n'est pas prêt (lot RB7). */
export const ETA_RETRY_MS = [2000, 4000, 8000, 16000, 30000];

export function stopMatch(name, query) {
  const n = String(name || "").toLowerCase();
  const q = String(query || "").toLowerCase();
  if (!n || !q) return false;
  return n === q || n.includes(q) || q.includes(n.split(" (")[0]);
}

function etaDayLabel(iso, lang) {
  const a = new Date(iso);
  if (Number.isNaN(a.getTime())) return "";
  return a.toLocaleDateString(lang === "en" ? "en-GB" : "fr-FR", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
}

export function tightenEtaMembers(members) {
  return (members || []).filter((m) => Number(m?.knots) >= ETA_MIN_KN && m?.arrival);
}

export function boundEtaIso(p10, p50, p90, maxSpanDays = ETA_MAX_SPAN_DAYS) {
  const a = Date.parse(p10);
  const b = Date.parse(p90);
  const m = Date.parse(p50 || "");
  if (!Number.isFinite(a) || !Number.isFinite(b)) return { p10: "", p90: "" };
  const span = (b - a) / 86400000;
  if (span <= maxSpanDays) return { p10, p90 };
  if (!Number.isFinite(m)) return { p10: "", p90: "" };
  const half = (maxSpanDays / 2) * 86400000;
  return {
    p10: new Date(Math.max(a, m - half)).toISOString(),
    p90: new Date(Math.min(b, m + half)).toISOString(),
  };
}

export function etaRangeFromMembers(members, maxSpanDays = ETA_MAX_SPAN_DAYS) {
  const kept = tightenEtaMembers(members);
  if (!kept.length) return null;
  const times = kept.map((m) => Date.parse(m.arrival)).filter(Number.isFinite).sort((x, y) => x - y);
  if (!times.length) return null;
  const pick = (q) => times[Math.min(times.length - 1, Math.max(0, Math.round((times.length - 1) * q)))];
  const p10 = new Date(pick(0.1)).toISOString();
  const p50 = new Date(pick(0.5)).toISOString();
  const p90 = new Date(pick(0.9)).toISOString();
  const bound = boundEtaIso(p10, p50, p90, maxSpanDays);
  if (!bound.p10 || !bound.p90) return null;
  return {
    members: kept.length,
    p10: bound.p10,
    p50,
    p90: bound.p90,
    memberKnots: kept.map((m) => Number(m.knots)),
  };
}

function displayEta(eta) {
  if (!eta || !Number(eta.members) || !eta.p10 || !eta.p90) return null;
  if (Array.isArray(eta.memberKnots) && eta.memberKnots.length) {
    if (!eta.memberKnots.some((k) => Number(k) >= ETA_MIN_KN)) return null;
  }
  const bound = boundEtaIso(eta.p10, eta.p50, eta.p90);
  if (!bound.p10 || !bound.p90) return null;
  return { ...eta, p10: bound.p10, p90: bound.p90 };
}

/** Texte de fourchette ; chaîne vide si pas d'ensemble (jamais inventé). */
export function formatEtaRange(eta, t, lang = "fr") {
  const tight = displayEta(eta);
  if (!tight) return "";
  const p10 = etaDayLabel(tight.p10, lang);
  const p90 = etaDayLabel(tight.p90, lang);
  if (!p10 || !p90) return "";
  return t("etaRange", { p10, p90 });
}

/** Détail p10–p90 / membres — info-bulle uniquement, jamais à l'écran. */
export function formatEtaRangeTitle(eta, t) {
  const tight = displayEta(eta);
  if (!tight) return "";
  return t("etaRangeTitle", { n: String(tight.members) });
}

export function nextStopFromMarks(marks, nowMs = Date.now()) {
  for (const m of marks || []) {
    const ts = Date.parse(m?.iso || "");
    if (Number.isFinite(ts) && ts > nowMs) return m.name || "";
  }
  return "";
}

export function nextEtaRetryMs(attempt) {
  const caps = ETA_RETRY_MS;
  if (!Number.isFinite(attempt) || attempt < 0) return caps[0];
  return caps[Math.min(attempt, caps.length - 1)];
}

export const REVIEW_FIXTURE = planAdviceFixture.review;
export const ADVICE_FIXTURE = planAdviceFixture.advice;

export function isAdviceDone(body) {
  return Boolean(body && body.status === "done" && body.best && typeof body.best === "object");
}

export function pickHeaviestLegIdx(legs) {
  let best = 0;
  let score = -1;
  (legs || []).forEach((leg, i) => {
    const n = Number(leg?.alertCount);
    const s = Number.isFinite(n) ? n : (leg?.level === "alert" ? 2 : leg?.level === "watch" ? 1 : 0);
    if (s > score) {
      score = s;
      best = i;
    }
  });
  return best;
}

export function readAdviceMeta(best) {
  const facts = Array.isArray(best?.facts) ? best.facts : [];
  let from = best?.from || "";
  let to = best?.to || "";
  let departWas = best?.departWas || "";
  let departNow = best?.departNow || "";
  for (const raw of facts) {
    const jambe = String(raw).match(/^jambe (.+) → (.+)$/);
    if (jambe) {
      from = from || jambe[1];
      to = to || jambe[2];
    }
    const dep = String(raw).match(/^départ (\d{4}-\d{2}-\d{2}) → (\d{4}-\d{2}-\d{2})$/);
    if (dep) {
      departWas = departWas || dep[1];
      departNow = departNow || dep[2];
    }
  }
  return {
    from,
    to,
    departWas,
    departNow,
    corridor: best?.corridor || "reference",
    shiftDays: Number.isFinite(Number(best?.shiftDays)) ? Number(best.shiftDays) : 0,
    extraNm: Number.isFinite(Number(best?.extraNm)) ? Math.round(Number(best.extraNm)) : 0,
    alertsBefore: Number.isFinite(Number(best?.alertsBefore)) ? Number(best.alertsBefore) : null,
    alertsAfter: Number.isFinite(Number(best?.alertsAfter)) ? Number(best.alertsAfter) : null,
    cascade: Array.isArray(best?.cascade) ? best.cascade : [],
  };
}

function looksEnglish(text) {
  return /\b(Leave|Instead|would change|alerts instead|later stops|rather than)\b/i.test(text);
}

function looksFrench(text) {
  return /\b(Partir|Rester|plutôt|alertes au lieu|escales suivantes)\b/i.test(text);
}

/** Phrase dans la langue de l'UI : gabarit i18n ; texte rédigé seulement s'il est déjà dans cette langue (L6). */
export function localizeAdviceSentence(best, t, lang = "fr") {
  const template = formatAdviceSentence(best, t, lang);
  const drafted = String(best?.sentence || "").trim();
  if (!drafted) return template;
  const draftedLang = String(best?.sentenceLang || "").slice(0, 2).toLowerCase();
  const ui = String(lang || "fr").slice(0, 2).toLowerCase();
  if (draftedLang && draftedLang === ui) {
    if (ui === "fr" && looksEnglish(drafted)) return template;
    if (ui === "en" && looksFrench(drafted)) return template;
    return drafted;
  }
  if (ui === "fr" && looksFrench(drafted) && !looksEnglish(drafted)) return drafted;
  return template;
}

export function formatAdviceSentence(best, t, lang = "fr") {
  const meta = readAdviceMeta(best);
  if (!meta.from && meta.alertsBefore == null) return "";
  const via = meta.corridor === "north"
    ? t("planAdviceViaNorth")
    : meta.corridor === "south" ? t("planAdviceViaSouth") : "";
  const extra = meta.extraNm
    ? t("planAdviceExtraNm", { nm: String(meta.extraNm) })
    : "";
  const absD = Math.abs(meta.shiftDays);
  const cascade = meta.shiftDays > 0
    ? t("planAdviceCascadeLater", { days: String(absD) })
    : meta.shiftDays < 0
      ? t("planAdviceCascadeEarlier", { days: String(absD) })
      : t("planAdviceCascadeNone");
  const vars = {
    from: meta.from || "—",
    via,
    extra,
    cascade,
    departWas: etaDayLabel(meta.departWas, lang) || meta.departWas || "—",
    departNow: etaDayLabel(meta.departNow, lang) || meta.departNow || "—",
    alertsBefore: meta.alertsBefore == null ? "—" : String(meta.alertsBefore),
    alertsAfter: meta.alertsAfter == null ? "—" : String(meta.alertsAfter),
    alerts: meta.alertsAfter == null ? "—" : String(meta.alertsAfter),
  };
  if (meta.shiftDays === 0) return t("planAdviceSentenceStay", vars);
  return t("planAdviceSentenceShift", vars);
}

export function formatAdvicePills(best, t) {
  const meta = readAdviceMeta(best);
  if (meta.alertsBefore == null || meta.alertsAfter == null) return null;
  const nm = meta.extraNm > 0 ? `+${meta.extraNm}` : String(meta.extraNm);
  const days = meta.shiftDays > 0 ? `+${meta.shiftDays}` : String(meta.shiftDays);
  return {
    alerts: t("planAdvicePillAlerts", { before: String(meta.alertsBefore), after: String(meta.alertsAfter) }),
    nm: t("planAdvicePillNm", { signed: nm }),
    days: t("planAdvicePillDays", { signed: days }),
  };
}

export function buildAdviceCompare(best, leg, t, lang = "fr") {
  const meta = readAdviceMeta(best);
  if (meta.alertsBefore == null) return null;
  const todayNm = Number.isFinite(Number(leg?.legNm)) ? Number(leg.legNm) : null;
  const advisedNm = todayNm != null ? todayNm + meta.extraNm : null;
  const sea = Number.isFinite(Number(leg?.daysAtSea)) ? Number(leg.daysAtSea) : null;
  const day = (iso) => etaDayLabel(iso, lang) || String(iso || "").slice(0, 10);
  return {
    today: {
      distance: todayNm == null ? "—" : t("planCompareDistance", { nm: String(Math.round(todayNm)) }),
      seaDays: sea == null ? "—" : t("planCompareSeaDays", { n: String(sea) }),
      alerts: t("planCompareAlerts", { n: String(meta.alertsBefore) }),
      stops: meta.cascade.map((row) => t("planCompareStop", { stop: row.stop || "—", date: day(row.was) })),
    },
    advised: {
      distance: advisedNm == null ? "—" : t("planCompareDistance", { nm: String(Math.round(advisedNm)) }),
      seaDays: sea == null || meta.extraNm ? "—" : t("planCompareSeaDays", { n: String(sea) }),
      alerts: t("planCompareAlerts", { n: String(meta.alertsAfter) }),
      stops: meta.cascade.map((row) => t("planCompareStop", { stop: row.stop || "—", date: day(row.now) })),
    },
  };
}

async function defaultAdviceFetch(legIdx, lang, { signal } = {}) {
  const q = new URLSearchParams({ leg: String(legIdx), lang: String(lang || "fr") });
  const r = await fetch(`${API_URL}/voyage/official/advice?${q}`, { signal });
  return r.ok ? r.json() : null;
}

export async function pollOfficialAdvice(legIdx, {
  fetchFn = defaultAdviceFetch,
  signal,
  sleep = sleepMs,
  onUpdate,
  lang = "fr",
} = {}) {
  let attempt = 0;
  while (!signal?.aborted) {
    let body = null;
    try {
      body = await fetchFn(legIdx, lang, { signal });
    } catch (err) {
      if (err?.name === "AbortError") throw err;
      body = null;
    }
    if (isAdviceDone(body)) {
      onUpdate?.(body);
      return body;
    }
    if (body?.status === "pending") onUpdate?.(body);
    else {
      onUpdate?.(null);
      return null;
    }
    await sleep(nextEtaRetryMs(attempt), signal);
    attempt += 1;
  }
  return null;
}

/** Corps /eta exploitable ; sinon null (jamais inventé). */
export function etaFromResponse(body) {
  if (body && Number(body.members) > 0 && body.p10 && body.p90) return body;
  return null;
}

export function sleepMs(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      const err = new Error("aborted");
      err.name = "AbortError";
      reject(err);
      return;
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener?.("abort", onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      const err = new Error("aborted");
      err.name = "AbortError";
      reject(err);
    };
    signal?.addEventListener?.("abort", onAbort, { once: true });
  });
}

async function defaultEtaFetch(stopName, { signal } = {}) {
  const r = await fetch(`${API_URL}/voyage/official/eta?stop=${encodeURIComponent(stopName)}`, { signal });
  return r.ok ? r.json() : null;
}

/**
 * Relance /eta tant que members == 0. Premier appel immédiat, puis recul
 * progressif. `onUpdate(null)` tant que l'ensemble n'est pas prêt.
 */
export async function pollOfficialEta(stopName, {
  fetchFn = defaultEtaFetch,
  signal,
  sleep = sleepMs,
  onUpdate,
} = {}) {
  let attempt = 0;
  while (!signal?.aborted) {
    let body = null;
    try {
      body = await fetchFn(stopName, { signal });
    } catch (err) {
      if (err?.name === "AbortError") throw err;
      body = null;
    }
    const ready = etaFromResponse(body);
    onUpdate?.(ready);
    if (ready) return ready;
    await sleep(nextEtaRetryMs(attempt), signal);
    attempt += 1;
  }
  return null;
}

export function useOfficialEta(stopName, { enabled = true } = {}) {
  const [eta, setEta] = useState(null);
  useEffect(() => {
    if (!enabled || !stopName) {
      setEta(null);
      return undefined;
    }
    const controller = new AbortController();
    let alive = true;
    pollOfficialEta(stopName, {
      signal: controller.signal,
      onUpdate: (ready) => { if (alive) setEta(ready); },
    }).catch((err) => {
      if (alive && err?.name !== "AbortError") setEta(null);
    });
    return () => {
      alive = false;
      controller.abort();
    };
  }, [enabled, stopName]);
  return eta;
}

/**
 * Revue de plan par règles (lot K): GET /voyage/official/plan-review (legs,
 * ZEE, ports of entry, MPA, unwarmed pearls) put into words with the season
 * read from the atlas cache (`lookup`, `revision` = the cache changed).
 * Read-only; refreshed every 10 min (the pearls keep warming).
 * Lot C6 : fourchette p10–p90 de la prochaine escale, si l'ensemble répond.
 */
export function usePlanReview({ enabled = true, clock, lookup, revision = 0, lang = "fr", galeLimitPct } = {}) {
  const [review, setReview] = useState(null);
  const [advice, setAdvice] = useState(null);
  const [error, setError] = useState(null);
  const nextStop = useMemo(() => nextStopFromMarks(clock?.marks), [clock]);
  const eta = useOfficialEta(nextStop, { enabled: enabled && Boolean(nextStop) });

  useEffect(() => {
    if (!enabled) {
      setReview(REVIEW_FIXTURE);
      setAdvice(ADVICE_FIXTURE);
      setError(null);
      return undefined;
    }
    let alive = true;
    const controller = new AbortController();
    const load = () => fetch(`${API_URL}/voyage/official/plan-review`, { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((body) => {
        if (alive) {
          setReview(body);
          setError(null);
          setAdvice((prev) => (prev?.source === "fixture" ? null : prev));
        }
      })
      .catch((err) => {
        if (alive && err?.name !== "AbortError") {
          setReview(REVIEW_FIXTURE);
          setAdvice(ADVICE_FIXTURE);
          setError(null);
        }
      });
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => {
      alive = false;
      controller.abort();
      clearInterval(timer);
    };
  }, [enabled]);

  const reviewed = useMemo(() => {
    const source = review || (!enabled ? REVIEW_FIXTURE : null);
    if (!source) return [];
    const opts = galeLimitPct ? { galeLimitPct } : {};
    if (clock) return reviewPlan(source, clock, lookup, lang, opts);
    return (source.legs || []).map((leg) => reviewLeg(leg, null, lang, opts));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [review, error, enabled, clock, lookup, revision, lang, galeLimitPct]);

  const heaviestIdx = useMemo(() => pickHeaviestLegIdx(reviewed), [reviewed]);

  useEffect(() => {
    if (!enabled || !review || review.source === "fixture") return undefined;
    const controller = new AbortController();
    let alive = true;
    pollOfficialAdvice(heaviestIdx, {
      signal: controller.signal,
      lang,
      onUpdate: (body) => { if (alive) setAdvice(isAdviceDone(body) ? body : body); },
    }).catch((err) => {
      if (alive && err?.name !== "AbortError") setAdvice((prev) => prev?.source === "fixture" ? prev : null);
    });
    return () => {
      alive = false;
      controller.abort();
    };
  }, [enabled, review, heaviestIdx, lang]);

  const legs = useMemo(() => {
    const before = isAdviceDone(advice) ? Number(advice.best?.alertsBefore) : NaN;
    const idx = isAdviceDone(advice) ? Number(advice.leg) : NaN;
    const base = reviewed.map((leg, i) => (
      Number.isFinite(idx) && i === idx && Number.isFinite(before)
        ? { ...leg, alertCount: before }
        : leg
    ));
    if (!eta || !eta.members || !nextStop) return base;
    return base.map((leg) => (
      stopMatch(leg.to, nextStop) ? { ...leg, etaRange: eta } : leg
    ));
  }, [reviewed, advice, eta, nextStop]);

  return {
    review,
    legs,
    error,
    loading: enabled && !review && !error,
    eta,
    advice: isAdviceDone(advice) || advice?.source === "fixture" ? advice : null,
  };
}
