/**
 * Lots LY1 / LY2 — chauffer les cellules AMP et les perles minces le long
 * d'un trait. Fire-and-forget : le dessin n'attend pas. Pas de texte d'aide.
 * LY2 : dès le premier segment du brouillon, pas seulement au Terminer.
 */

import { wrapLon } from "../utils/geo.js";
import {
  MAX_PEARLS_SIM,
  flatFromCustomRoute,
  pearlKey,
  sampleLeg,
} from "./iciAlong.js";

const API_URL = import.meta.env?.VITE_API_URL ?? "";
const PEARL_PARALLEL = 4;

export const DRAFT_WARM_DEBOUNCE_MS = 1500;
export const LAYER_WARM_MAX_CELLS = 80;

function pushLonLat(out, pair) {
  if (!Array.isArray(pair) || pair.length < 2) return;
  const lon = Number(pair[0]);
  const lat = Number(pair[1]);
  if (Number.isFinite(lat) && Number.isFinite(lon) && lat >= -90 && lat <= 90) {
    out.push([lat, lon]);
  }
}

function walkGeometry(geom, out) {
  if (!geom) return;
  const t = geom.type;
  const c = geom.coordinates;
  if (t === "Point") {
    pushLonLat(out, c);
  } else if (t === "MultiPoint" || t === "LineString") {
    for (const p of c || []) pushLonLat(out, p);
  } else if (t === "MultiLineString") {
    for (const line of c || []) {
      for (const p of line || []) pushLonLat(out, p);
    }
  } else if (t === "GeometryCollection") {
    for (const g of geom.geometries || []) walkGeometry(g, out);
  }
}

/** Points [lat, lon] du GeoJSON dessiné / importé, dans l'ordre du trait. */
export function pointsFromCustomRoute(geojson) {
  const out = [];
  for (const f of geojson?.features || []) walkGeometry(f?.geometry, out);
  return out;
}

/** GeoJSON du brouillon (mêmes LineString + points que useRouteDrawing.toGeoJson). */
export function geojsonFromDrawn(points = [], segments = []) {
  const lineFeatures = (segments || []).filter((s) => s.coords?.length > 0).map((s) => ({
    type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: s.coords },
  }));
  const pointFeatures = (points || []).map((p, i) => ({
    type: "Feature",
    properties: { name: p.name || `Point ${i + 1}` },
    geometry: { type: "Point", coordinates: [p.lon, p.lat] },
  }));
  return { type: "FeatureCollection", features: [...lineFeatures, ...pointFeatures] };
}

/** Clé de cellule AMP 1° — même repli que le serveur. */
export function cellKey(lat, lon) {
  const la = Number(lat);
  const lo = wrapLon(Number(lon));
  if (!Number.isFinite(la) || !Number.isFinite(lo)) return "";
  return `${Math.floor(la)}:${Math.floor(lo)}`;
}

/** Lance le chauffage des couches. Jamais d'exception vers l'UI. */
export function kickLayerWarm(geojson, fetchImpl = fetch, opts = {}) {
  const points = opts.points || pointsFromCustomRoute(geojson);
  if (!points.length) return false;
  try {
    const init = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ points }),
    };
    if (opts.signal) init.signal = opts.signal;
    Promise.resolve(fetchImpl(`${API_URL}/ici/layers/warm`, init)).catch(() => {});
    return true;
  } catch {
    return false;
  }
}

/** Perles minces du brouillon (12 nm, cap simulation). Pas Berry, pas le monde. */
export function kickDraftPearls(geojson, fetchImpl = fetch, opts = {}) {
  const flat = flatFromCustomRoute(geojson);
  if (!flat?.points?.length) return false;
  const seen = opts.seen || new Set();
  const maxPearls = Number.isFinite(opts.maxPearls) ? opts.maxPearls : MAX_PEARLS_SIM;
  const pearls = sampleLeg(flat, {
    fromNm: 0,
    toNm: flat.totalNm,
    boatNm: 0,
    maxPearls,
  });
  const missing = pearls.filter((p) => {
    const key = pearlKey(p.lat, p.lon, opts.month);
    return key && !seen.has(key);
  });
  if (!missing.length) return false;
  const signal = opts.signal;
  let next = 0;
  const fetchOne = async (p) => {
    if (signal?.aborted) return;
    const key = pearlKey(p.lat, p.lon, opts.month);
    seen.add(key);
    const q = new URLSearchParams({
      lat: String(p.lat),
      lon: String(wrapLon(Number(p.lon))),
      thin: "1",
    });
    try {
      await fetchImpl(`${API_URL}/ici?${q.toString()}`, signal ? { signal } : {});
    } catch {
      /* abort ou réseau — le sac n'est pas affiché */
    }
  };
  const worker = async () => {
    while (!signal?.aborted && next < missing.length) {
      const p = missing[next];
      next += 1;
      await fetchOne(p);
    }
  };
  Promise.all(Array.from({ length: Math.min(PEARL_PARALLEL, missing.length) }, worker)).catch(() => {});
  return true;
}

/**
 * Chauffage du brouillon pendant le dessin : debounce, cellules nouvelles,
 * AbortController. Annuler coupe les vols ; le cache serveur n'est pas vidé.
 */
export function createDraftWarmer({
  fetchImpl = fetch,
  debounceMs = DRAFT_WARM_DEBOUNCE_MS,
} = {}) {
  let timer = null;
  let gen = 0;
  let controller = null;
  const seenCells = new Set();
  const seenPearls = new Set();

  function abortFlight() {
    if (!controller) return;
    controller.abort();
    controller = null;
  }

  function cancel() {
    gen += 1;
    if (timer != null) {
      clearTimeout(timer);
      timer = null;
    }
    abortFlight();
    seenPearls.clear();
    seenCells.clear();
  }

  function run(geojson, my) {
    if (my !== gen) return;
    const allPoints = pointsFromCustomRoute(geojson);
    const fresh = [];
    for (const pair of allPoints) {
      const key = cellKey(pair[0], pair[1]);
      if (!key || seenCells.has(key)) continue;
      if (seenCells.size + fresh.length >= LAYER_WARM_MAX_CELLS) break;
      fresh.push(pair);
    }
    controller = new AbortController();
    const signal = controller.signal;
    if (fresh.length) {
      for (const pair of fresh) seenCells.add(cellKey(pair[0], pair[1]));
      kickLayerWarm(null, fetchImpl, { signal, points: fresh });
    }
    kickDraftPearls(geojson, fetchImpl, { signal, seen: seenPearls });
  }

  function schedule(geojson) {
    const my = gen;
    if (timer != null) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      if (my !== gen) return;
      run(geojson, my);
    }, debounceMs);
  }

  return { schedule, cancel, seenCells, seenPearls };
}
