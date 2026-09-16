import { useEffect, useMemo, useRef, useState } from "react";
import { haversineNm, wrapLon } from "../utils/geo.js";
import {
  boatPositionFromCast,
  emptyDossier,
  mergeDossier,
} from "../engine/ici.js";
import { detectEvents, emptyEventMemory } from "../engine/eventRules.js";
import { judgeEvents } from "../engine/displayJudge.js";
import { narrateIci, phraseForEvent } from "../engine/iciBriefing.js";

const API_URL = import.meta.env.VITE_API_URL ?? "";
const DEBOUNCE_MS = 800;
const MOVE_NM = 3;
const FETCH_MS = 40000;
const MIN_SCHEDULE_MS = 8000;

function legKey(jambe) {
  if (!jambe) return "";
  return `${jambe.fromStop || ""}→${jambe.toStop || ""}`;
}

/**
 * Fill the `ici()` bag around the boat and turn it into a story.
 * One step = one GET /ici. No chat, no Tavily.
 * Detectors + judge run on the bag already collected. Never await a model.
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
  mode = "simulation",
  cinema = false,
  playbackProfile = "normal",
  cumNm = null,
  filmCum = null,
  clockMin = null,
  rainMm = null,
  rain3hMm = null,
  gribWindKnots = null,
  gribDirFromDeg = null,
  gribHs = null,
  gribModel = null,
  gribStatus = null,
  skipperClickId = null,
}) {
  const [remote, setRemote] = useState(null);
  const [tick, setTick] = useState({ events: [], briefing: null });
  const lastFetchRef = useRef(null);
  const lastScheduledRef = useRef(null);
  const abortRef = useRef(null);
  const timerRef = useRef(null);
  const requestIdRef = useRef(0);
  const memoryRef = useRef(emptyEventMemory(legKey(jambe)));
  const prevBagRef = useRef(undefined);
  const lastRemoteRef = useRef(null);
  const lastNowRef = useRef(null);
  const lastLegRef = useRef(legKey(jambe));
  const playheadRef = useRef({ cumNm, filmCum, clockMin });
  playheadRef.current = { cumNm, filmCum, clockMin };
  const boat = boatPositionFromCast(cast, snappedPosition);
  const currentLeg = legKey(jambe);

  if (lastLegRef.current !== currentLeg) {
    lastLegRef.current = currentLeg;
    memoryRef.current = emptyEventMemory(currentLeg);
    prevBagRef.current = undefined;
    lastRemoteRef.current = null;
    lastNowRef.current = null;
  }

  useEffect(() => {
    if (!enabled || !boat) {
      setRemote(null);
      setTick({ events: [], briefing: null });
      lastFetchRef.current = null;
      lastScheduledRef.current = null;
      prevBagRef.current = undefined;
      lastRemoteRef.current = null;
      lastNowRef.current = null;
      memoryRef.current = emptyEventMemory(currentLeg);
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
          lastFetchRef.current = { lat, lon, month, destLat, destLon };
          setRemote(data);
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
  }, [enabled, boat?.lat, boat?.lon, month, destLat, destLon, currentLeg]);

  useEffect(() => {
    if (!remote) {
      setTick({ events: [], briefing: null });
      return;
    }
    const isNewBag = lastRemoteRef.current !== remote;
    const prev = isNewBag ? prevBagRef.current : remote;
    const gribWind = Number.isFinite(gribWindKnots)
      ? {
        windKnots: gribWindKnots,
        dirFromDeg: gribDirFromDeg,
        hs: gribHs,
        model: gribModel,
      }
      : null;
    const ctx = {
      mode,
      cinema,
      profile: playbackProfile,
      cumNm: playheadRef.current.cumNm,
      filmCum: playheadRef.current.filmCum,
      clockMin: playheadRef.current.clockMin,
      rainMm,
      rain3hMm,
      gribWind,
      gribStatus,
      legId: currentLeg || null,
      airHop: jambe?.vehicle === "plane"
        || jambe?.phase === "air-out"
        || jambe?.phase === "air-return",
    };
    const { events: found, memory } = detectEvents({
      at: remote,
      prev,
      along: null,
      ctx,
      memory: memoryRef.current,
    });
    memoryRef.current = memory;
    if (isNewBag) {
      prevBagRef.current = remote;
      lastRemoteRef.current = remote;
    }
    const withPhrase = found.map((ev) => ({
      ...ev,
      phrase: phraseForEvent(ev, lang),
    }));
    const judged = judgeEvents(withPhrase, {
      cinema,
      profile: playbackProfile,
      skipperClickId,
      mode,
    });
    const nextBrief = judged.briefing
      ? { ...judged.briefing, phrase: phraseForEvent(judged.briefing, lang) }
      : lastNowRef.current;
    if (nextBrief) lastNowRef.current = nextBrief;
    setTick((prev) => {
      const sameBrief = prev.briefing?.id === nextBrief?.id
        && prev.briefing?.phrase === nextBrief?.phrase;
      const sameEvents = prev.events.length === judged.judged.length
        && prev.events.every((e, i) => (
          e.id === judged.judged[i]?.id && e.judge === judged.judged[i]?.judge
        ));
      if (sameBrief && sameEvents) return prev;
      return { events: judged.judged, briefing: nextBrief };
    });
  }, [
    remote,
    mode,
    cinema,
    playbackProfile,
    rainMm,
    rain3hMm,
    gribWindKnots,
    gribDirFromDeg,
    gribHs,
    gribModel,
    gribStatus,
    skipperClickId,
    lang,
    currentLeg,
    jambe?.vehicle,
    jambe?.phase,
  ]);

  const dossier = useMemo(() => {
    if (!enabled || !boat || !remote) return null;
    return mergeDossier(remote, {
      polarMeta,
      jambe,
      event: tick.briefing || remote.event || null,
      climatology: remote.climatology || climatology || null,
    });
  }, [enabled, boat, remote, polarMeta, jambe, climatology, tick.briefing]);

  const briefing = useMemo(
    () => (dossier ? narrateIci(dossier, lang) : ""),
    [dossier, lang],
  );

  return {
    dossier,
    briefing,
    loading: Boolean(enabled && boat && !remote),
    events: tick.events,
    display: tick.briefing,
  };
}
