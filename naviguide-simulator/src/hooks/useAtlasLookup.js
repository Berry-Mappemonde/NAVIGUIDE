import { useCallback, useEffect, useState } from "react";
import { atlasOrZone, cellKey, clampMonth } from "../utils/atlasPoint.js";
import { monthOfT0 } from "../engine/voyageClock.js";
import { createAtlasScheduler, routeCells } from "../engine/atlasScheduler.js";

/**
 * Browser fetch → JSON; HTTP errors carry `.status` so the scheduler can tell
 * « atlas down » (5xx / 429 / network) from « this cell never answers » (4xx).
 */
async function fetchJson(url) {
  const r = await fetch(url);
  if (!r.ok) {
    const err = new Error(`atlas ${r.status}`);
    err.status = r.status;
    throw err;
  }
  return r.json();
}

// One scheduler per tab: the cache and the in-flight table are shared by
// every mount, and by resetAtlasCache() (tests, new voyage).
const scheduler = createAtlasScheduler({ fetchJson });

/**
 * Session cache of /climatology/point. Sync lookup for the clock;
 * async fill replaces zone_fallback as cells arrive.
 *
 * The React side only listens: the rules (dedup, no abort per tick, boat
 * interval, cooldown when the atlas is down) live in engine/atlasScheduler.js.
 */
export function useAtlasLookup({
  enabled = true,
  t0,
  points = [],
  boatLat,
  boatLon,
  destLat,
  destLon,
  month,
} = {}) {
  const [revision, setRevision] = useState(0);
  const [boatPoint, setBoatPoint] = useState(null);
  const [alive, setAlive] = useState(null);
  const [retryTick, setRetryTick] = useState(0);
  const [boatTick, setBoatTick] = useState(0);

  const windAt = useCallback((lat, lon, m) => {
    const hit = scheduler.cache.get(cellKey(lat, lon, m));
    return atlasOrZone(lat, lon, m, hit?.point || null);
  }, []);

  const lookup = useCallback((lat, lon, m) => {
    return scheduler.cache.get(cellKey(lat, lon, m)) || null;
  }, []);

  // One subscription per mount: cells and boat answers land here whenever
  // they arrive, even after the boat moved on (nothing is aborted).
  useEffect(() => {
    if (!enabled) return undefined;
    return scheduler.subscribe((event) => {
      if (event.type === "down") {
        setAlive(false);
        return;
      }
      if (event.type === "boat") setBoatPoint(event.point);
      if (event.entry?.source === "atlas") setAlive(true);
      setRevision((n) => n + 1);
    });
  }, [enabled]);

  // Route prefetch: depends on the route and the clock, never on the boat.
  useEffect(() => {
    if (!enabled) return undefined;
    let active = true;
    let timer = null;
    scheduler.prefetch(routeCells(points, t0)).then((res) => {
      if (!active || res.deferred === 0) return;
      const wait = Math.max(250, scheduler.downUntil() - Date.now() + 50);
      timer = setTimeout(() => setRetryTick((n) => n + 1), wait);
    }).catch(() => {});
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [enabled, t0, points, month, retryTick]);

  // Boat cell (+ crossings): once per cell, at most one request per interval.
  useEffect(() => {
    if (!enabled || !Number.isFinite(Number(boatLat))) return undefined;
    const m = clampMonth(month || monthOfT0(t0, 0));
    const res = scheduler.boat({ lat: boatLat, lon: boatLon, month: m, destLat, destLon });
    if (res.status !== "wait" && res.status !== "down") return undefined;
    const timer = setTimeout(() => setBoatTick((n) => n + 1), Math.max(100, res.waitMs || 0));
    return () => clearTimeout(timer);
  }, [enabled, boatLat, boatLon, destLat, destLon, month, t0, boatTick]);

  return {
    windAt,
    lookup,
    boatPoint,
    revision,
    alive,
  };
}

export function resetAtlasCache() {
  scheduler.reset();
}
