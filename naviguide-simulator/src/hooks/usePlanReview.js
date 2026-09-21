import { useEffect, useMemo, useState } from "react";
import { reviewPlan } from "../engine/planReview.js";

const API_URL = import.meta.env?.VITE_API_URL ?? "";
const REFRESH_MS = 10 * 60 * 1000;

function stopMatch(name, query) {
  const n = String(name || "").toLowerCase();
  const q = String(query || "").toLowerCase();
  if (!n || !q) return false;
  return n === q || n.includes(q) || q.includes(n.split(" (")[0]);
}

function etaDayLabel(iso, otherIso, lang) {
  const a = new Date(iso);
  const b = new Date(otherIso);
  if (Number.isNaN(a.getTime()) || Number.isNaN(b.getTime())) return "";
  const sameMonth = a.getUTCMonth() === b.getUTCMonth() && a.getUTCFullYear() === b.getUTCFullYear();
  if (sameMonth) return String(a.getUTCDate());
  return a.toLocaleDateString(lang === "en" ? "en-GB" : "fr-FR", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
}

/** Texte de fourchette ; chaîne vide si pas d'ensemble (jamais inventé). */
export function formatEtaRange(eta, t, lang = "fr") {
  if (!eta || !Number(eta.members) || !eta.p10 || !eta.p90) return "";
  const p10 = etaDayLabel(eta.p10, eta.p90, lang);
  const p90 = etaDayLabel(eta.p90, eta.p10, lang);
  if (!p10 || !p90) return "";
  return t("etaRange", { p10, p90, n: String(eta.members) });
}

export function nextStopFromMarks(marks, nowMs = Date.now()) {
  for (const m of marks || []) {
    const ts = Date.parse(m?.iso || "");
    if (Number.isFinite(ts) && ts > nowMs) return m.name || "";
  }
  return "";
}

export function useOfficialEta(stopName, { enabled = true } = {}) {
  const [eta, setEta] = useState(null);
  useEffect(() => {
    if (!enabled || !stopName) {
      setEta(null);
      return undefined;
    }
    let alive = true;
    const controller = new AbortController();
    fetch(`${API_URL}/voyage/official/eta?stop=${encodeURIComponent(stopName)}`, { signal: controller.signal })
      .then(async (r) => (r.ok ? r.json() : null))
      .then((body) => {
        if (!alive) return;
        if (body && Number(body.members) > 0 && body.p10 && body.p90) setEta(body);
        else setEta(null);
      })
      .catch((err) => {
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
  const [error, setError] = useState(null);
  const nextStop = useMemo(() => nextStopFromMarks(clock?.marks), [clock]);
  const eta = useOfficialEta(nextStop, { enabled: enabled && Boolean(nextStop) });

  useEffect(() => {
    if (!enabled) return undefined;
    let alive = true;
    const controller = new AbortController();
    const load = () => fetch(`${API_URL}/voyage/official/plan-review`, { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((body) => { if (alive) { setReview(body); setError(null); } })
      .catch((err) => { if (alive && err?.name !== "AbortError") setError(err?.message || "error"); });
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => {
      alive = false;
      controller.abort();
      clearInterval(timer);
    };
  }, [enabled]);

  const legs = useMemo(() => {
    const base = review && clock ? reviewPlan(review, clock, lookup, lang, galeLimitPct ? { galeLimitPct } : {}) : [];
    if (!eta || !eta.members || !nextStop) return base;
    return base.map((leg) => (
      stopMatch(leg.to, nextStop) ? { ...leg, etaRange: eta } : leg
    ));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [review, clock, lookup, revision, lang, galeLimitPct, eta, nextStop]);

  return { review, legs, error, loading: enabled && !review && !error, eta };
}
