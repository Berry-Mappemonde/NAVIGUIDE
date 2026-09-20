import { useEffect, useMemo, useState } from "react";
import { reviewPlan } from "../engine/planReview.js";

const API_URL = import.meta.env.VITE_API_URL ?? "";
const REFRESH_MS = 10 * 60 * 1000;

/**
 * Revue de plan par règles (lot K): GET /voyage/official/plan-review (legs,
 * ZEE, ports of entry, MPA, unwarmed pearls) put into words with the season
 * read from the atlas cache (`lookup`, `revision` = the cache changed).
 * Read-only; refreshed every 10 min (the pearls keep warming).
 */
export function usePlanReview({ enabled = true, clock, lookup, revision = 0, lang = "fr", galeLimitPct } = {}) {
  const [review, setReview] = useState(null);
  const [error, setError] = useState(null);

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

  const legs = useMemo(
    () => (review && clock ? reviewPlan(review, clock, lookup, lang, galeLimitPct ? { galeLimitPct } : {}) : []),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [review, clock, lookup, revision, lang, galeLimitPct],
  );

  return { review, legs, error, loading: enabled && !review && !error };
}
