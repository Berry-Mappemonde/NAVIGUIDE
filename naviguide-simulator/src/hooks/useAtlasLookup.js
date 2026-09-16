import { useCallback, useEffect, useRef, useState } from "react";
import {
  atlasCrossingsUrl,
  atlasOrZone,
  atlasPointUrl,
  cellKey,
  clampMonth,
  windFromAtlasPoint,
} from "../utils/atlasPoint.js";
import { monthOfT0 } from "../engine/voyageClock.js";

const CACHE = new Map();
const INFLIGHT = new Map();
const CONCURRENCY = 6;

function monthsAround(t0) {
  const m0 = monthOfT0(t0, 0);
  return [m0, clampMonth(m0 + 1), clampMonth(m0 + 2)];
}

function sampleCells(points, t0, boatLat, boatLon, month) {
  const cells = new Map();
  const add = (lat, lon, m, dest) => {
    if (!Number.isFinite(Number(lat)) || !Number.isFinite(Number(lon))) return;
    const key = cellKey(lat, lon, m);
    if (!cells.has(key)) cells.set(key, { lat, lon, month: m, dest });
  };
  const months = monthsAround(t0);
  const pts = points || [];
  const step = Math.max(1, Math.ceil(pts.length / 48));
  for (let i = 0; i < pts.length; i += step) {
    const p = pts[i];
    if (p?.jump || p?.nonMaritime) continue;
    months.forEach((m) => add(p.lat, p.lon, m));
  }
  if (Number.isFinite(Number(boatLat))) {
    add(boatLat, boatLon, month || months[0]);
  }
  return [...cells.values()];
}

async function fetchPoint(spec, signal) {
  const url = atlasPointUrl(spec);
  const r = await fetch(url, { signal });
  if (!r.ok) throw new Error(`atlas ${r.status}`);
  return r.json();
}

async function fetchCrossings(spec, signal) {
  const url = atlasCrossingsUrl(spec);
  const r = await fetch(url, { signal });
  if (!r.ok) throw new Error(`crossings ${r.status}`);
  return r.json();
}

async function runPool(jobs, limit) {
  const pending = [...jobs];
  const workers = Array.from({ length: Math.min(limit, pending.length) }, async () => {
    while (pending.length) {
      const job = pending.shift();
      if (job) await job();
    }
  });
  await Promise.all(workers);
}

/**
 * Session cache of /climatology/point. Sync lookup for the clock;
 * async fill replaces zone_fallback as cells arrive.
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
  const boatKeyRef = useRef("");

  const windAt = useCallback((lat, lon, m) => {
    const hit = CACHE.get(cellKey(lat, lon, m));
    return atlasOrZone(lat, lon, m, hit?.point || null);
  }, []);

  const lookup = useCallback((lat, lon, m) => {
    return CACHE.get(cellKey(lat, lon, m)) || null;
  }, []);

  useEffect(() => {
    if (!enabled) return undefined;
    const ctrl = new AbortController();
    const cells = sampleCells(points, t0, boatLat, boatLon, month);
    const jobs = cells.map((cell) => async () => {
      const key = cellKey(cell.lat, cell.lon, cell.month);
      if (CACHE.has(key) || INFLIGHT.has(key)) return;
      const work = fetchPoint(cell, ctrl.signal)
        .then((point) => {
          const wind = windFromAtlasPoint(point);
          CACHE.set(key, { point, wind, source: wind ? "atlas" : "empty" });
          setAlive(true);
          setRevision((n) => n + 1);
        })
        .catch((err) => {
          if (ctrl.signal.aborted) return;
          if (!CACHE.has(key)) CACHE.set(key, { point: null, wind: null, source: "zone_fallback" });
          const msg = String(err.message || err);
          if (/Failed to fetch|NetworkError|atlas 5\d\d/.test(msg)) setAlive(false);
        })
        .finally(() => {
          INFLIGHT.delete(key);
        });
      INFLIGHT.set(key, work);
      await work;
    });
    runPool(jobs, CONCURRENCY).catch(() => {});
    return () => ctrl.abort();
  }, [enabled, t0, points, boatLat, boatLon, month, alive]);

  useEffect(() => {
    if (!enabled || !Number.isFinite(Number(boatLat))) return undefined;
    const m = clampMonth(month || monthOfT0(t0, 0));
    const key = `${cellKey(boatLat, boatLon, m)}:${destLat ?? ""}:${destLon ?? ""}`;
    if (boatKeyRef.current === key && boatPoint) return undefined;
    const ctrl = new AbortController();
    const spec = { lat: boatLat, lon: boatLon, month: m, destLat, destLon };
    Promise.all([
      fetchPoint(spec, ctrl.signal),
      Number.isFinite(Number(destLat))
        ? fetchCrossings({
          lat1: boatLat, lon1: boatLon, lat2: destLat, lon2: destLon, month: m,
        }, ctrl.signal).catch(() => null)
        : Promise.resolve(null),
    ]).then(([point, crossings]) => {
      if (ctrl.signal.aborted) return;
      const packed = crossings ? { ...point, crossings } : point;
      if (packed.cyclone && crossings && !packed.cyclone.crossings_if_leg) {
        packed.cyclone = { ...packed.cyclone, crossings_if_leg: crossings };
      }
      CACHE.set(cellKey(boatLat, boatLon, m), {
        point: packed,
        wind: windFromAtlasPoint(packed),
        source: windFromAtlasPoint(packed) ? "atlas" : "empty",
      });
      boatKeyRef.current = key;
      setBoatPoint(packed);
      setAlive(true);
      setRevision((n) => n + 1);
    }).catch(() => {
      if (!ctrl.signal.aborted) setAlive((prev) => (prev == null ? false : prev));
    });
    return () => ctrl.abort();
  }, [enabled, boatLat, boatLon, destLat, destLon, month, t0, boatPoint]);

  return {
    windAt,
    lookup,
    boatPoint,
    revision,
    alive,
  };
}

export function resetAtlasCache() {
  CACHE.clear();
  INFLIGHT.clear();
}
