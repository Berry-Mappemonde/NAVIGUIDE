import { useEffect, useState } from "react";
import { wrapLon } from "../utils/geo.js";

const API_URL = import.meta.env?.VITE_API_URL ?? "";

/** One lookup per film step: 0.2° (~12 nm), not one request per frame. */
export const FILM_ZEE_STEP_DEG = 0.2;

export function filmZeeBucket(lat, lon, stepDeg = FILM_ZEE_STEP_DEG) {
  const la = Number(lat);
  const lo = Number(lon);
  if (!Number.isFinite(la) || !Number.isFinite(lo)) return "";
  const q = (n) => (Math.round(n / stepDeg) * stepDeg).toFixed(1);
  return `${q(la)}:${q(wrapLon(lo))}`;
}

/**
 * EEZ at the replayed position, refreshed when the film boat changes bucket.
 * GET /zee/at is local polygons only. A missing answer stays null (unknown),
 * never a high-seas claim.
 */
export function useFilmZee({ enabled = false, lat = null, lon = null } = {}) {
  const [zee, setZee] = useState(null);
  const bucket = enabled ? filmZeeBucket(lat, lon) : "";

  useEffect(() => {
    if (!bucket) {
      setZee(null);
      return undefined;
    }
    const [la, lo] = bucket.split(":").map(Number);
    const ctrl = new AbortController();
    let cancelled = false;
    fetch(`${API_URL}/zee/at?lat=${encodeURIComponent(la)}&lon=${encodeURIComponent(lo)}`, {
      signal: ctrl.signal,
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!cancelled && data && typeof data === "object") setZee(data);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, [bucket]);

  return enabled ? zee : null;
}
