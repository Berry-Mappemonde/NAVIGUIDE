import { useEffect, useMemo, useRef, useState } from "react";
import { ROUTE_SAMPLE_NM } from "../engine/eventRules.js";
import {
  MAX_PEARLS_SIM,
  MAX_PEARLS_SUIVRE,
  buildAlongIndex,
  lookaheadNmFor,
  pearlKey,
  sampleLeg,
} from "../engine/iciAlong.js";

const API_URL = import.meta.env.VITE_API_URL ?? "";
const FETCH_MS = 20000;

/**
 * Preheat thin /ici pearls on THIS leg. Never blocks Play. No chat.
 */
export function useIciAlong({
  enabled,
  flat,
  fromNm,
  toNm,
  boatNm,
  mode = "simulation",
  month,
  knots,
}) {
  const [bags, setBags] = useState(() => new Map());
  const cacheRef = useRef(new Map());
  const routeKey = `${flat?.points?.length || 0}:${flat?.totalNm || 0}:${fromNm ?? ""}:${toNm ?? ""}:${mode}`;
  const lastRouteRef = useRef(routeKey);
  if (lastRouteRef.current !== routeKey) {
    lastRouteRef.current = routeKey;
    cacheRef.current = new Map();
  }

  const boatBucket = Number.isFinite(Number(boatNm))
    ? Math.floor(Number(boatNm) / ROUTE_SAMPLE_NM) * ROUTE_SAMPLE_NM
    : 0;

  const pearls = useMemo(() => {
    if (!enabled || !flat?.points?.length) return [];
    return sampleLeg(flat, {
      fromNm,
      toNm,
      boatNm: boatBucket,
      month,
      lookaheadNm: lookaheadNmFor(mode, knots),
      maxPearls: mode === "suivre" ? MAX_PEARLS_SUIVRE : MAX_PEARLS_SIM,
    });
  }, [enabled, flat, fromNm, toNm, boatBucket, month, mode, knots]);

  const pearlsSig = pearls.map((p) => pearlKey(p.lat, p.lon, month)).join("|");

  useEffect(() => {
    if (!enabled || !pearls.length) return undefined;
    let cancelled = false;
    const missing = pearls.filter((p) => !cacheRef.current.has(pearlKey(p.lat, p.lon, month)));
    if (!missing.length) {
      setBags(new Map(cacheRef.current));
      return undefined;
    }
    const run = async () => {
      for (let i = 0; i < missing.length; i += 3) {
        if (cancelled) return;
        const chunk = missing.slice(i, i + 3);
        await Promise.all(chunk.map(async (p) => {
          const key = pearlKey(p.lat, p.lon, month);
          const ctrl = new AbortController();
          const kill = setTimeout(() => ctrl.abort(), FETCH_MS);
          try {
            const q = new URLSearchParams({
              lat: String(p.lat),
              lon: String(p.lon),
              thin: "1",
            });
            if (Number.isFinite(Number(month))) q.set("month", String(month));
            const r = await fetch(`${API_URL}/ici?${q.toString()}`, { signal: ctrl.signal });
            const data = r.ok ? await r.json() : null;
            if (!cancelled) cacheRef.current.set(key, data);
          } catch {
            if (!cancelled) cacheRef.current.set(key, null);
          } finally {
            clearTimeout(kill);
          }
        }));
        if (!cancelled) setBags(new Map(cacheRef.current));
      }
    };
    run();
    return () => { cancelled = true; };
  }, [enabled, pearlsSig, month]);

  const index = useMemo(
    () => buildAlongIndex(pearls, bags, month),
    [pearls, bags, month],
  );

  return {
    index,
    pearls,
    loading: Boolean(enabled && pearls.length && pearls.some((p) => !bags.has(pearlKey(p.lat, p.lon, month)))),
  };
}
