import { useEffect, useMemo, useRef, useState } from "react";
import { haversineNm, wrapLon } from "../utils/geo.js";
import {
  boatPositionFromCast,
  emptyDossier,
  mergeDossier,
  zeeEnterEvent,
} from "../engine/ici.js";
import { narrateIci } from "../engine/iciBriefing.js";

const API_URL = import.meta.env.VITE_API_URL ?? "";
const DEBOUNCE_MS = 800;
const MOVE_NM = 3;
const FETCH_MS = 40000;
const MIN_SCHEDULE_MS = 8000;

/**
 * Fill the `ici()` bag around the boat and turn it into a story.
 * One step = one GET /ici. No chat, no Tavily.
 */
export function useIciDossier({
  enabled,
  cast,
  snappedPosition,
  polarMeta,
  jambe,
  lang = "fr",
  month,
  destLat,
  destLon,
  climatology,
}) {
  const [remote, setRemote] = useState(null);
  const lastFetchRef = useRef(null);
  const lastScheduledRef = useRef(null);
  const prevZeeRef = useRef(undefined);
  const abortRef = useRef(null);
  const timerRef = useRef(null);
  const requestIdRef = useRef(0);
  const boat = boatPositionFromCast(cast, snappedPosition);

  useEffect(() => {
    if (!enabled || !boat) {
      setRemote(null);
      lastFetchRef.current = null;
      lastScheduledRef.current = null;
      prevZeeRef.current = undefined;
      requestIdRef.current += 1;
      clearTimeout(timerRef.current);
      abortRef.current?.abort();
      return undefined;
    }

    const lat = boat.lat;
    const lon = wrapLon(boat.lon);
    const last = lastFetchRef.current || lastScheduledRef.current;
    if (
      last
      && haversineNm(last.lat, last.lon, lat, lon) < MOVE_NM
      && last.month === month
      && last.destLat === destLat
      && last.destLon === destLon
    ) {
      return undefined;
    }

    const now = Date.now();
    if (
      lastScheduledRef.current
      && lastScheduledRef.current.month === month
      && lastScheduledRef.current.destLat === destLat
      && lastScheduledRef.current.destLon === destLon
      && now - lastScheduledRef.current.scheduledAt < MIN_SCHEDULE_MS
    ) {
      return undefined;
    }
    lastScheduledRef.current = { lat, lon, month, destLat, destLon, scheduledAt: now };
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      const requestId = requestIdRef.current + 1;
      requestIdRef.current = requestId;
      abortRef.current = ctrl;
      const kill = setTimeout(() => ctrl.abort(), FETCH_MS);
      const q = new URLSearchParams({
        lat: String(lat),
        lon: String(lon),
      });
      if (Number.isFinite(Number(month))) q.set("month", String(month));
      if (Number.isFinite(Number(destLat)) && Number.isFinite(Number(destLon))) {
        q.set("dest_lat", String(destLat));
        q.set("dest_lon", String(destLon));
      }
      fetch(`${API_URL}/ici?${q.toString()}`, {
        signal: ctrl.signal,
      })
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`ici ${r.status}`))))
        .then((data) => {
          if (requestIdRef.current !== requestId) return;
          const event = zeeEnterEvent(prevZeeRef.current, data?.zee);
          prevZeeRef.current = data?.zee?.mrgid ?? null;
          lastFetchRef.current = { lat, lon, month, destLat, destLon };
          setRemote({ ...data, event });
        })
        .catch(() => {
          if (ctrl.signal.aborted || requestIdRef.current !== requestId) return;
          setRemote({
            ...emptyDossier(lat, lon),
            sources: { zee: "error", bi: "unavailable" },
          });
        })
        .finally(() => {
          clearTimeout(kill);
        });
    }, DEBOUNCE_MS);

    return () => clearTimeout(timerRef.current);
  }, [enabled, boat?.lat, boat?.lon, month, destLat, destLon]);

  const dossier = useMemo(() => {
    if (!enabled || !boat || !remote) return null;
    return mergeDossier(remote, {
      polarMeta,
      jambe,
      event: remote.event,
      climatology: remote.climatology || climatology || null,
    });
  }, [enabled, boat, remote, polarMeta, jambe, climatology]);

  const briefing = useMemo(
    () => (dossier ? narrateIci(dossier, lang) : ""),
    [dossier, lang],
  );

  return { dossier, briefing, loading: Boolean(enabled && boat && !remote) };
}
