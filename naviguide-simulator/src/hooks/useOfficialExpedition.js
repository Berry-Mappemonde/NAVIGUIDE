import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DEFAULT_T0_ISO, OFFICIAL_VOYAGE_ID, sampleClockAtTime } from "../engine/voyageClock.js";
import { pickOfficialLiveClock } from "../utils/sceneGate.js";
import { adminHeaders } from "../utils/adminSecret.js";
import { officialGribQuery, officialGribStatus, officialGribWarning } from "./gribStatus.js";

const API = import.meta.env?.VITE_API_URL ?? "";

/** A client clock is "official" when it starts on the expedition's fixed t0. */
export function isOfficialClock(clock) {
  const t0 = Date.parse(clock?.t0 ?? "");
  return Number.isFinite(t0) && t0 === Date.parse(DEFAULT_T0_ISO);
}

/**
 * Voyage officiel unique. Pas de localStorage visiteur.
 * Position = horloge serveur à maintenant (1 s = 1 s), avec repli figé
 * sur le premier snapshot client si le PUT officiel n’a pas encore répondu
 * (404 après redémarrage, 502 de deploy, calcul _climo_clock lent).
 * Dernier GRIB = overlay vent, jamais un nouveau trait, jamais de climatologie.
 */
export function useOfficialExpedition({
  enabled,
  points,
  marks,
  expeditionId,
  clock,
}) {
  const [meta, setMeta] = useState(null);
  const [serverClock, setServerClock] = useState(null);
  const [grib, setGrib] = useState(null);
  const [gribPending, setGribPending] = useState(false);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const [clockStatus, setClockStatus] = useState("pending");
  const putRef = useRef("");
  const serverClockRef = useRef(serverClock);
  const frozenClientRef = useRef(null);
  serverClockRef.current = serverClock;

  useEffect(() => {
    if (!enabled) return undefined;
    const id = setInterval(() => setNowMs(Date.now()), 1000);
    return () => clearInterval(id);
  }, [enabled]);

  useEffect(() => {
    if (!enabled || !points?.length) frozenClientRef.current = null;
  }, [enabled, points]);

  const liveClock = useMemo(() => {
    // Only an official clock (t0 = 15 May) may stand in for the server. A
    // Simulation clock (t0 = today) frozen here put the boat back at
    // Saint-Maur on day 0 — never freeze while Suivre is off.
    if (!enabled) {
      frozenClientRef.current = null;
      return null;
    }
    const officialClient = isOfficialClock(clock) ? clock : null;
    if (serverClock) {
      frozenClientRef.current = frozenClientRef.current || officialClient;
      return serverClock;
    }
    // Pas de cache client tant que le serveur n'a pas répondu : sinon saut Nouméa → Panama.
    if (clockStatus !== "absent") return null;
    const picked = pickOfficialLiveClock(null, officialClient, frozenClientRef.current);
    frozenClientRef.current = picked.frozenClient;
    return picked.liveClock;
  }, [enabled, serverClock, clock, clockStatus]);

  const putOfficial = useCallback(async () => {
    if (!points?.length) return null;
    const fp = `${points.length}|${points[0]?.lat}|${points[points.length - 1]?.lat}|${expeditionId || ""}`;
    if (putRef.current === fp && meta?.voyageId === OFFICIAL_VOYAGE_ID) return meta;
    // Anonymous: the server only creates a missing official voyage, never
    // edits it. With the admin key (X-Naviguide-Admin) it may update the route.
    const res = await fetch(`${API}/voyage/official`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...adminHeaders() },
      body: JSON.stringify({
        t0: DEFAULT_T0_ISO,
        expedition_id: expeditionId || "berry-mappemonde-2026",
        routeKind: "berry",
        follow: true,
        forecast: false,
        startAt: "la-rochelle",
        official: true,
        points: points.map((p) => ({
          lat: p.lat,
          lon: p.lon,
          cumNm: p.cumNm,
          filmCum: p.filmCum,
          jump: Boolean(p.jump),
          nonMaritime: Boolean(p.nonMaritime),
          air: Boolean(p.air),
        })),
        marks: (marks || []).map((m) => ({
          name: m.name,
          nm: m.nm,
          filmNm: m.filmNm,
          lat: m.lat,
          lon: m.lon,
          index: m.index,
          flag: true,
        })),
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return null;
    putRef.current = fp;
    setMeta(data);
    if (data.clock) {
      setServerClock(data.clock);
      setClockStatus("ready");
    }
    return data;
  }, [points, marks, expeditionId, meta]);

  useEffect(() => {
    if (!enabled || !points?.length) return undefined;
    let cancelled = false;
    const readClock = () => fetch(`${API}/voyage/official/clock`)
      .then((r) => {
        if (r.ok) return r.json();
        if (!cancelled && (r.status === 404 || r.status >= 500)) setClockStatus("absent");
        return null;
      })
      .then((ck) => {
        if (ck?.t0 && !cancelled) {
          setServerClock(ck);
          setClockStatus("ready");
        }
      })
      .catch(() => { if (!cancelled) setClockStatus("absent"); });
    const kick = () => {
      // The server clock is the truth for the boat's position: read it even
      // when the PUT is refused (rate limit, payload rule, 5xx) — a refused
      // self-repair must never leave the visitor on a client clock.
      putOfficial()
        .catch(() => null)
        .then(() => { if (!cancelled) return readClock(); return undefined; });
    };
    kick();
    const retry = setInterval(() => {
      if (!putRef.current || !serverClockRef.current) kick();
    }, 5000);
    return () => {
      cancelled = true;
      clearInterval(retry);
    };
  }, [enabled, points, putOfficial]);

  const refreshGrib = useCallback(async ({ force = false } = {}) => {
    const q = officialGribQuery(serverClockRef.current);
    if (!q) return null;
    const qs = `?lat=${encodeURIComponent(q.lat)}&lon=${encodeURIComponent(q.lon)}`;
    const url = force ? `${API}/voyage/official/grib/refresh${qs}` : `${API}/voyage/official/grib${qs}`;
    const res = await fetch(url, force ? { method: "POST", headers: adminHeaders() } : undefined);
    const data = await res.json().catch(() => null);
    if (res.ok && data) {
      setGrib(data);
      setGribPending(data.status === "pending" || Boolean(data.refreshing));
    }
    return data;
  }, []);

  useEffect(() => {
    if (!enabled) return undefined;
    const q = officialGribQuery(serverClock);
    if (!q) {
      setGribPending(true);
      return undefined;
    }
    let cancelled = false;
    let retry = null;
    setGribPending(true);
    const refresh = () => {
      refreshGrib()
        .then((data) => {
          if (!cancelled && (data?.status === "pending" || data?.refreshing)) {
            clearTimeout(retry);
            retry = setTimeout(refresh, 4000);
          }
        })
        .catch(() => {
          if (!cancelled) setGribPending(false);
        });
    };
    refresh();
    const id = setInterval(() => {
      refresh();
    }, 60_000);
    return () => {
      cancelled = true;
      clearTimeout(retry);
      clearInterval(id);
    };
  }, [enabled, refreshGrib, meta?.voyageId, serverClock]);

  const live = useMemo(() => {
    if (!enabled || !liveClock) return null;
    const sample = sampleClockAtTime(liveClock, new Date(nowMs));
    if (!sample) return null;
    const wind = grib?.wind;
    const regime = sample.regime || sample.kind || "climatology";
    if (grib?.status === "ready" && wind) {
      const models = (grib.products || [])
        .filter((p) => p.status === "ready")
        .map((p) => p.model);
      return {
        ...sample,
        regime,
        sources: sample.sources || [],
        spread: sample.spread ?? null,
        kind: "forecast",
        model: models[0] || grib.model || wind.model || "GFS",
        waveModel: grib.waveModel || wind.waveModel || null,
        currentModel: grib.currentModel || wind.currentModel || null,
        windKnots: wind.windKnots,
        dirFromDeg: wind.dirFromDeg,
        pressHpa: wind.pressHpa,
        rainMm: wind.rainMm,
        hs: wind.hs,
        gribStatus: "ready",
        gribWarning: null,
      };
    }
    return {
      ...sample,
      regime,
      sources: sample.sources || [],
      spread: sample.spread ?? null,
      kind: "absent",
      model: null,
      windKnots: null,
      dirFromDeg: null,
      gribStatus: grib?.status === "ready" ? "ready" : (gribPending || !grib ? "pending" : "absent"),
      gribWarning: null,
    };
  }, [enabled, liveClock, nowMs, grib, gribPending]);

  const positioned = Boolean(
    liveClock
    && sampleClockAtTime(liveClock, new Date(nowMs))?.lat != null,
  );
  const gribStatus = officialGribStatus({
    enabled,
    grib,
    pending: gribPending,
    positioned,
  });

  return {
    voyageId: OFFICIAL_VOYAGE_ID,
    voyage: meta,
    clock: serverClock,
    live,
    grib,
    gribStatus,
    gribModel: (grib?.products || [])
      .filter((p) => p.status === "ready")
      .map((p) => p.model)
      .filter(Boolean)
      .join(" · ") || grib?.model || null,
    gribWarning: officialGribWarning({ enabled, status: gribStatus }),
    refreshGrib,
  };
}
