import { useEffect, useMemo, useRef, useState } from "react";
import { haversineNm, wrapLon } from "../utils/geo.js";
import {
  boatPositionFromCast,
  emptyDossier,
  mergeDossier,
} from "../engine/ici.js";
import { detectEvents, emptyEventMemory } from "../engine/eventRules.js";
import { judgeEvents } from "../engine/displayJudge.js";
import { narrateIci, narrateIciSegments, phraseForEvent } from "../engine/iciBriefing.js";
import { promoteLaterAtPlayhead, upsertLedger } from "../engine/iciAlong.js";
import { enqueueStory, shouldEnqueueStory, storyPayload, subscribeStories } from "../engine/storyQueue.js";
import { WEATHER_POLL_MS, fetchWeatherForecast } from "./weatherSnapshot.js";

const API_URL = import.meta.env?.VITE_API_URL ?? "";
const DEBOUNCE_MS = 800;
const MOVE_NM = 3;
const FETCH_MS = 40000;
const MIN_SCHEDULE_MS = 8000;
/** A bag collected this far from the boat is history: the briefing waits for the next one. */
export const STALE_BAG_NM = 60;
/** Two consecutive bags this far apart = the boat jumped (mode switch, seek): no transition event. */
export const JUMP_NM = 100;

function legKey(jambe) {
  if (!jambe) return "";
  return `${jambe.fromStop || ""}→${jambe.toStop || ""}`;
}

/** Distance between the bag's centre and the boat, in nm (Infinity when unknown). */
export function bagDistanceNm(bag, boat) {
  const lat = Number(bag?.at?.lat);
  const lon = Number(bag?.at?.lon);
  if (!boat || !Number.isFinite(lat) || !Number.isFinite(lon)) return Infinity;
  return haversineNm(lat, lon, boat.lat, wrapLon(boat.lon));
}

export function isStaleBag(bag, boat, limitNm = STALE_BAG_NM) {
  if (!bag) return false;
  return bagDistanceNm(bag, boat) > limitNm;
}

/** The previous bag is a fresh start (no zee-exit, no wind-shift) when the boat jumped. */
export function isJump(prevBag, bag, limitNm = JUMP_NM) {
  if (!prevBag?.at || !bag?.at) return false;
  const d = haversineNm(Number(prevBag.at.lat), Number(prevBag.at.lon), Number(bag.at.lat), Number(bag.at.lon));
  return Number.isFinite(d) && d > limitNm;
}

/**
 * Fill the `ici()` bag around the boat and turn it into a story.
 * One step = one GET /ici. No chat, no Tavily.
 * Detectors + judge run on the bag already collected. Never await a model.
 * enqueueStory is fire-and-forget (NIM → OR → Claude).
 * `orders` (skipper) feed detectors + judge locally, without a new GET /ici.
 * Changing orders never rewinds: pastilles already in the ledger stay as judged.
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
  along = null,
  nearestBag = null,
  orders = null,
}) {
  const [remote, setRemote] = useState(null);
  const [tick, setTick] = useState({ events: [], briefing: null });
  // One GET /ici at a time, never aborted by the next position: aborting it
  // every 8 s while the film played meant no bag ever completed — and no
  // event all the way across the Atlantic. `wantRef` remembers where the
  // boat is now; when the request lands we fetch again if it moved.
  const [refetch, setRefetch] = useState(0);
  const inFlightRef = useRef(false);
  const wantRef = useRef(null);
  const lastFetchRef = useRef(null);
  const lastScheduledRef = useRef(null);
  const abortRef = useRef(null);
  const timerRef = useRef(null);
  const requestIdRef = useRef(0);
  // S7 Expert `iciRadiusNm`: read through a ref so a new radius applies to the
  // NEXT scheduled bag only — changing orders never triggers a GET /ici by itself.
  const radiusRef = useRef(null);
  radiusRef.current = Number.isFinite(orders?.values?.iciRadiusNm) && orders.values.iciRadiusNm !== 30
    ? orders.values.iciRadiusNm
    : null;
  const memoryRef = useRef(emptyEventMemory(legKey(jambe)));
  const prevBagRef = useRef(undefined);
  const lastRemoteRef = useRef(null);
  const lastNowRef = useRef(null);
  const ledgerRef = useRef([]);
  const lastLegRef = useRef(legKey(jambe));
  const playheadRef = useRef({ cumNm, filmCum, clockMin });
  playheadRef.current = { cumNm, filmCum, clockMin };
  const filmBucket = Number.isFinite(filmCum) ? Math.round(filmCum / 5) * 5 : null;
  const boat = boatPositionFromCast(cast, snappedPosition);
  const currentLeg = legKey(jambe);

  if (lastLegRef.current !== currentLeg) {
    lastLegRef.current = currentLeg;
    memoryRef.current = emptyEventMemory(currentLeg);
    prevBagRef.current = undefined;
    lastRemoteRef.current = null;
    lastNowRef.current = null;
    ledgerRef.current = [];
  }

  // A bag collected far from where the boat is now (fast playback, mode
  // switch) must not narrate this place. Meanwhile the along pearl just
  // passed (thin bag: ZEE, ports of entry, MPA, harbours) stands in — it is
  // what makes events fire at any film speed.
  const staleRemote = Boolean(remote && boat && isStaleBag(remote, boat));
  const fresh = remote && !staleRemote ? remote : null;
  const latB = boat ? Math.round(boat.lat * 20) / 20 : null;
  const lonB = boat ? Math.round(wrapLon(boat.lon) * 20) / 20 : null;
  const thinBag = useMemo(() => {
    if (fresh || !boat || typeof nearestBag !== "function") return null;
    // Far ahead the pearls sit 48 nm apart: the nearest one is at most 24 nm away.
    return nearestBag({ lat: latB, lon: lonB }, 26);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fresh, nearestBag, latB, lonB]);
  const effective = fresh || thinBag;

  useEffect(() => {
    // New leg: the old bag belongs to another place — drop it now rather than
    // letting it narrate (or fire a zee-exit) at the new leg's start.
    setRemote(null);
    lastFetchRef.current = null;
    lastScheduledRef.current = null;
  }, [currentLeg]);

  useEffect(() => subscribeStories((job) => {
    const idx = ledgerRef.current.findIndex((e) => (
      e.id === job.eventId || (job.stableKey && e.stableKey === job.stableKey)
    ));
    if (idx < 0) return;
    const ev = ledgerRef.current[idx];
    const next = {
      ...ev,
      story: job,
      phrase: job.status === "ready" && job.text ? job.text : ev.phrase,
    };
    ledgerRef.current = ledgerRef.current.map((e, i) => (i === idx ? next : e));
    if (lastNowRef.current && (lastNowRef.current.id === ev.id || lastNowRef.current.stableKey === ev.stableKey)) {
      lastNowRef.current = { ...lastNowRef.current, phrase: next.phrase, story: job };
    }
    setTick({ events: ledgerRef.current, briefing: lastNowRef.current });
  }), []);

  useEffect(() => {
    if (!enabled || !boat) {
      setRemote(null);
      setTick({ events: [], briefing: null });
      lastFetchRef.current = null;
      lastScheduledRef.current = null;
      wantRef.current = null;
      prevBagRef.current = undefined;
      lastRemoteRef.current = null;
      lastNowRef.current = null;
      ledgerRef.current = [];
      memoryRef.current = emptyEventMemory(currentLeg);
      requestIdRef.current += 1;
      clearTimeout(timerRef.current);
      abortRef.current?.abort();
      inFlightRef.current = false;
      return undefined;
    }

    const lat = boat.lat;
    const lon = wrapLon(boat.lon);
    wantRef.current = { lat, lon, month, destLat, destLon };
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
    // A bag is on its way: let it land, then fetch again from wherever the
    // boat is by then (see `finally` below). Never abort a request in flight.
    if (inFlightRef.current) return undefined;

    const now = Date.now();
    const sameTarget = lastScheduledRef.current
      && lastScheduledRef.current.month === month
      && lastScheduledRef.current.destLat === destLat
      && lastScheduledRef.current.destLon === destLon;
    if (sameTarget && now - lastScheduledRef.current.scheduledAt < MIN_SCHEDULE_MS && !refetch) {
      return undefined;
    }
    lastScheduledRef.current = { lat, lon, month, destLat, destLon, scheduledAt: now };
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      if (inFlightRef.current) return;
      const ctrl = new AbortController();
      const requestId = requestIdRef.current + 1;
      requestIdRef.current = requestId;
      abortRef.current = ctrl;
      inFlightRef.current = true;
      const kill = setTimeout(() => ctrl.abort(), FETCH_MS);
      const q = new URLSearchParams({
        lat: String(lat),
        lon: String(lon),
      });
      if (Number.isFinite(Number(month))) q.set("month", String(month));
      if (radiusRef.current != null) q.set("radius_nm", String(radiusRef.current));
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
          inFlightRef.current = false;
          if (requestIdRef.current !== requestId) return;
          // The boat kept moving while the bag was collected: go again now.
          const want = wantRef.current;
          if (want && haversineNm(want.lat, want.lon, lat, lon) >= MOVE_NM) {
            lastScheduledRef.current = null;
            setRefetch((n) => n + 1);
          }
        });
    }, DEBOUNCE_MS);

    return () => clearTimeout(timerRef.current);
  }, [enabled, boat?.lat, boat?.lon, month, destLat, destLon, currentLeg, refetch]);

  useEffect(() => {
    if (!remote || remote.weather?.status !== "pending") return undefined;
    const lat = remote.at?.lat;
    const lon = remote.at?.lon;
    if (!Number.isFinite(Number(lat)) || !Number.isFinite(Number(lon))) return undefined;
    let cancelled = false;
    const tick = () => {
      fetchWeatherForecast(lat, lon, { api: API_URL })
        .then((wx) => {
          if (cancelled || !wx) return;
          setRemote((prev) => {
            if (!prev || prev.at?.lat !== lat || prev.at?.lon !== lon) return prev;
            return {
              ...prev,
              weather: wx,
              sources: { ...prev.sources, weather: wx.source ?? prev.sources?.weather },
            };
          });
        })
        .catch(() => {});
    };
    const id = setInterval(tick, WEATHER_POLL_MS);
    tick();
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [remote?.weather?.status, remote?.at?.lat, remote?.at?.lon]);

  useEffect(() => {
    const remote = effective;
    if (!remote) {
      // Nothing at the boat yet: keep the ledger (pastilles), clear the brief.
      setTick((prevTick) => (prevTick.briefing ? { events: prevTick.events, briefing: null } : prevTick));
      return;
    }
    const isNewBag = lastRemoteRef.current !== remote;
    let prev = isNewBag ? prevBagRef.current : remote;
    if (isNewBag && prev && isJump(prev, remote)) {
      // The boat jumped (mode switch, seek, plane): the old bag is another
      // place. No zee-exit / wind-shift between the two — fresh memory.
      prev = undefined;
      memoryRef.current = emptyEventMemory(currentLeg);
    }
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
      orders,
      lang,
      airHop: jambe?.vehicle === "plane"
        || jambe?.phase === "air-out"
        || jambe?.phase === "air-return",
    };
    const { events: found, memory } = detectEvents({
      at: remote,
      prev,
      along,
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
      orders,
    });
    ledgerRef.current = promoteLaterAtPlayhead(
      upsertLedger(ledgerRef.current, judged.judged.map((ev) => ({
        ...ev,
        phrase: ev.phrase || phraseForEvent(ev, lang),
      }))),
      playheadRef.current.filmCum,
    );
    const clicked = skipperClickId
      ? ledgerRef.current.find((e) => e.id === skipperClickId || e.stableKey === skipperClickId)
      : null;
    let nextBrief = judged.briefing
      ? { ...judged.briefing, phrase: phraseForEvent(judged.briefing, lang) }
      : lastNowRef.current;
    if (clicked) {
      nextBrief = { ...clicked, judge: "now", judgeReason: "skipper-click", phrase: phraseForEvent(clicked, lang) };
      ledgerRef.current = ledgerRef.current.map((e) => (
        e === clicked || e.id === clicked.id
          ? { ...e, judge: "now", seenNow: true, judgeReason: "skipper-click" }
          : e
      ));
    }
    const promotedNow = ledgerRef.current.find((e) => e.promoted && e.judge === "now");
    if (!clicked && promotedNow && !judged.briefing) {
      nextBrief = { ...promotedNow, phrase: phraseForEvent(promotedNow, lang) };
    }
    if (nextBrief) lastNowRef.current = nextBrief;
    for (const ev of ledgerRef.current) {
      if (!shouldEnqueueStory(ev)) continue;
      ev.story = enqueueStory(storyPayload(ev, lang));
    }
    const ledger = ledgerRef.current;
    setTick((prevTick) => {
      const sameBrief = prevTick.briefing?.id === nextBrief?.id
        && prevTick.briefing?.phrase === nextBrief?.phrase;
      const sameEvents = prevTick.events.length === ledger.length
        && prevTick.events.every((e, i) => (
          e.id === ledger[i]?.id
          && e.judge === ledger[i]?.judge
          && e.story?.status === ledger[i]?.story?.status
        ));
      if (sameBrief && sameEvents) return prevTick;
      return { events: ledger, briefing: nextBrief };
    });
  }, [
    effective,
    along,
    mode,
    cinema,
    playbackProfile,
    filmBucket,
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
    orders,
  ]);

  const dossier = useMemo(() => {
    if (!enabled || !boat || !effective) return null;
    return mergeDossier(effective, {
      polarMeta,
      jambe,
      event: tick.briefing || effective.event || null,
      // A thin pearl has no climatology of its own: the atlas at the boat still does.
      climatology: effective.climatology || climatology || null,
    });
  }, [enabled, boat, effective, polarMeta, jambe, climatology, tick.briefing]);

  const briefing = useMemo(
    () => (dossier ? narrateIci(dossier, lang) : ""),
    [dossier, lang],
  );
  // Same text, split around the places it names (links: map focus + sheet).
  const briefingSegments = useMemo(
    () => (dossier ? narrateIciSegments(dossier, lang) : []),
    [dossier, lang],
  );

  return {
    dossier,
    briefing,
    briefingSegments,
    loading: Boolean(enabled && boat && !effective),
    stale: staleRemote,
    thin: Boolean(effective?.thin),
    pearl: effective?.pearl ?? (effective?.thin ? "thin" : null),
    events: tick.events,
    display: tick.briefing,
  };
}
