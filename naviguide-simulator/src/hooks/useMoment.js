import { useEffect, useState } from "react";
import { wrapLon } from "../utils/geo.js";
import fixture from "../fixtures/moment.json" with { type: "json" };

const API_URL = import.meta.env?.VITE_API_URL ?? "";

export const MOMENT_FIXTURE = fixture;

export function isMoment(body) {
  return Boolean(body && typeof body === "object" && typeof body.signature === "string" && body.signature);
}

/** Query string for GET /ici/moment. Longitudes folded into [−180, 180]. */
export function momentSearchParams({ lat, lon, t, mode, lang } = {}) {
  const q = new URLSearchParams({
    lat: String(lat),
    lon: String(wrapLon(Number(lon))),
  });
  if (t) q.set("t", String(t));
  if (mode) q.set("mode", String(mode));
  if (lang) q.set("lang", String(lang));
  return q;
}

/**
 * Fetch a Moment from GET /ici/moment. If the API does not answer, keep the
 * official_mini fixture (CI / preview without a server).
 */
export function useMoment({
  lat,
  lon,
  t,
  mode = "follow",
  lang = "fr",
  enabled = true,
} = {}) {
  const [state, setState] = useState({
    moment: MOMENT_FIXTURE,
    loading: false,
    error: null,
    source: "fixture",
  });

  useEffect(() => {
    if (!enabled || !Number.isFinite(Number(lat)) || !Number.isFinite(Number(lon))) {
      setState({ moment: MOMENT_FIXTURE, loading: false, error: null, source: "fixture" });
      return undefined;
    }
    const controller = new AbortController();
    setState((prev) => ({ ...prev, loading: true }));
    const q = momentSearchParams({ lat, lon, t, mode, lang });
    fetch(`${API_URL}/ici/moment?${q}`, { signal: controller.signal })
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((body) => {
        if (!isMoment(body)) throw new Error("moment invalide");
        setState({ moment: body, loading: false, error: null, source: "api" });
      })
      .catch((err) => {
        if (err?.name === "AbortError") return;
        setState({
          moment: MOMENT_FIXTURE,
          loading: false,
          error: err?.message || "error",
          source: "fixture",
        });
      });
    return () => controller.abort();
  }, [enabled, lat, lon, t, mode, lang]);

  return state;
}
