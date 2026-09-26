import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import {
  atlasLayerUrl,
  atlasPointUrl,
  atlasTileUrl,
  clampMonth,
  visibleClimoTiles,
} from "../utils/atlasPoint.js";
import { wrapLon } from "../utils/geo.js";
import { POPUP_OPTS } from "./points.js";
import {
  CLIMO_COLOR,
  currentArrowHtml,
  layerPopupHtml,
  pointPopupHtml,
  roseSvg,
  waveColor,
} from "./climatologyPaint.js";
import { climoPointLngs, cycloneLatLngCopies, groupCycloneFeatures } from "./climatologyWorld.js";

function currentIcon(p) {
  return L.divIcon({
    className: "bi-climo-arrow",
    html: currentArrowHtml(p.direction_to_deg),
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
}

async function fetchJson(url, signal) {
  const r = await fetch(url, { signal });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

function paintWindProps(p) {
  return {
    ...p,
    wind_speed_knots: p.wind_speed_knots ?? p.speed_knots,
    wind_direction_from_deg: p.wind_direction_from_deg ?? p.dir_from_deg,
  };
}

function paintWaveProps(p) {
  return {
    ...p,
    dir_deg: p.dir_deg ?? p.dir,
  };
}

function mergeTileFeatures(collections, paintProps) {
  const merged = [];
  const seen = new Set();
  for (const feats of collections) {
    if (!feats) continue;
    for (const f of feats) {
      const [lon, lat] = f.geometry?.coordinates || [];
      if (lat == null || lon == null) continue;
      const k = `${lat}:${lon}`;
      if (seen.has(k)) continue;
      seen.add(k);
      merged.push({ ...f, properties: paintProps(f.properties || {}) });
    }
  }
  return merged;
}

const EMPTY_LAYERS = { wind: null, waveP50: null, waveP90: null, waveMean: null, current: null, cyclones: null };

/**
 * Four atlas maps (wind / wave / current / cyclones), each optional.
 * Wind, wave and current load XYZ tiles of the visible area; cyclones stay global.
 * Points and IBTrACS tracks are painted on the three world copies.
 */
export function useClimatologyLayer({
  mapRef,
  mapReady = 0,
  showWind = false,
  showWave = false,
  showCurrent = false,
  showCyclones = false,
  month = 1,
  drawing = false,
  t = (k) => k,
  onPoint,
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [counts, setCounts] = useState(null);
  const layersRef = useRef({ ...EMPTY_LAYERS });
  const tRef = useRef(t);
  tRef.current = t;
  const onPointRef = useRef(onPoint);
  onPointRef.current = onPoint;
  const drawingRef = useRef(drawing);
  drawingRef.current = drawing;
  const m = clampMonth(month);
  const anyOn = showWind || showWave || showCurrent || showCyclones;

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return undefined;

    Object.values(layersRef.current).forEach((lyr) => {
      if (lyr && map.hasLayer(lyr)) map.removeLayer(lyr);
    });
    layersRef.current = { ...EMPTY_LAYERS };

    if (!anyOn) {
      setLoading(false);
      setError(null);
      setCounts(null);
      return undefined;
    }

    let cancelled = false;
    const ctrl = new AbortController();
    const tileAbort = { ctrl: new AbortController() };
    const cache = new Map();
    const popupOpts = { ...POPUP_OPTS, maxWidth: 300 };
    const countsRef = { wind: 0, waveP50: 0, waveP90: 0, waveMean: 0, current: 0, cyclones: 0 };

    const loadSafe = (name, fn) => fn().catch((err) => {
      console.error(`[climatology] ${name} layer failed`, err);
      return 0;
    });

    const addPointMarkers = (data, makeLayer) => {
      const group = L.layerGroup();
      (data?.features || []).forEach((f) => {
        const [lon, lat] = f.geometry?.coordinates || [];
        if (lat == null || lon == null) return;
        const p = f.properties || {};
        for (const lng of climoPointLngs(lon)) {
          const lyr = makeLayer([lat, lng], p);
          if (lyr) group.addLayer(lyr);
        }
      });
      return group;
    };

    const replaceGroup = (key, group) => {
      const prev = layersRef.current[key];
      layersRef.current[key] = group;
      group.addTo(map);
      if (prev && prev !== group && map.hasLayer(prev)) map.removeLayer(prev);
    };

    const evict = (kind, keep) => {
      const prefix = `${kind}:${m}:`;
      for (const k of [...cache.keys()]) {
        if (k.startsWith(prefix) && !keep.has(k)) cache.delete(k);
      }
    };

    const loadTiles = async (kind, extra, makeLayer, layerKey, paintProps) => {
      const signal = tileAbort.ctrl.signal;
      const zTile = Math.max(0, Math.min(6, Math.round(map.getZoom())));
      const tiles = visibleClimoTiles(map.getBounds(), zTile, { margin: 1, zMax: 6 });
      const keep = new Set(tiles.map((tile) => `${kind}:${m}:${tile.z}/${tile.x}/${tile.y}`));
      evict(kind, keep);
      const collections = await Promise.all(tiles.map(async (tile) => {
        const key = `${kind}:${m}:${tile.z}/${tile.x}/${tile.y}`;
        const hit = cache.get(key);
        if (hit?.features) return hit.features;
        try {
          const data = await fetchJson(atlasTileUrl(kind, m, tile.z, tile.x, tile.y, extra), signal);
          const features = data.features || [];
          cache.set(key, { features });
          return features;
        } catch (err) {
          if (err?.name === "AbortError") return null;
          return [];
        }
      }));
      if (cancelled || signal.aborted) return 0;
      const features = mergeTileFeatures(collections, paintProps);
      replaceGroup(layerKey, addPointMarkers({ features }, makeLayer));
      return features.length;
    };

    const makeWind = (ll, p) => {
      const marker = L.marker(ll, {
        icon: L.divIcon({
          className: "bi-climo-rose",
          html: roseSvg(p),
          iconSize: [32, 32],
          iconAnchor: [16, 16],
        }),
        pane: "climatology-vector",
        interactive: false,
      });
      marker.bindPopup(() => layerPopupHtml("wind", p, tRef.current), popupOpts);
      return marker;
    };

    const makeWave = (stat) => (ll, p) => {
      const c = L.circleMarker(ll, {
        pane: "climatology-raster",
        radius: stat === "p50" ? 2.8 : 3.6,
        color: waveColor(Number(p.hs_m) || 0, p.stat || stat),
        fillColor: waveColor(Number(p.hs_m) || 0, p.stat || stat),
        fillOpacity: stat === "p50" ? 0.4 : 0.55,
        weight: 0,
        interactive: false,
      });
      c.bindPopup(() => layerPopupHtml("wave", p, tRef.current), popupOpts);
      return c;
    };

    const makeCurrent = (ll, p) => {
      if (p.below_threshold) return null;
      const marker = L.marker(ll, {
        icon: currentIcon(p),
        pane: "climatology-vector",
        interactive: false,
      });
      marker.bindPopup(() => layerPopupHtml("current", p, tRef.current), popupOpts);
      return marker;
    };

    const publishCounts = () => {
      if (cancelled) return;
      setCounts({ ...countsRef });
      const painted = Object.values(countsRef).some(Boolean);
      if (!painted) setError("atlas_empty");
      else setError(null);
    };

    const refreshVectors = async () => {
      tileAbort.ctrl.abort();
      tileAbort.ctrl = new AbortController();
      const jobs = [];
      if (showWind) {
        jobs.push(loadSafe("wind", () => loadTiles("wind", {}, makeWind, "wind", paintWindProps))
          .then((n) => { countsRef.wind = n || 0; }));
      }
      if (showWave) {
        jobs.push(loadSafe("wave-p50", () => loadTiles("wave", { stat: "p50" }, makeWave("p50"), "waveP50", paintWaveProps))
          .then((n) => { countsRef.waveP50 = n || 0; }));
        jobs.push(loadSafe("wave-p90", () => loadTiles("wave", { stat: "p90" }, makeWave("p90"), "waveP90", paintWaveProps))
          .then((n) => { countsRef.waveP90 = n || 0; }));
      }
      if (showCurrent) {
        jobs.push(loadSafe("current", () => loadTiles("current", {}, makeCurrent, "current", (p) => p))
          .then((n) => { countsRef.current = n || 0; }));
      }
      await Promise.all(jobs);
      if (cancelled) return;
      if (showWave && !countsRef.waveP50 && !countsRef.waveP90) {
        countsRef.waveMean = await loadSafe("wave-mean", () => (
          loadTiles("wave", { stat: "mean" }, makeWave("mean"), "waveMean", paintWaveProps)
        ));
      }
      publishCounts();
    };

    const loadCyclones = async () => {
      const data = await fetchJson(atlasLayerUrl("cyclones", m), ctrl.signal);
      if (cancelled) return 0;
      const group = L.layerGroup();
      groupCycloneFeatures(data.features || []).forEach((storm) => {
        const copies = cycloneLatLngCopies(storm.coords);
        const p = storm.properties || {};
        copies.forEach((latlngs) => {
          if (latlngs.length < 2) return;
          const line = L.polyline(latlngs, {
            pane: "climatology-vector",
            color: p.color || CLIMO_COLOR,
            weight: 1.6,
            opacity: 0.75,
            interactive: false,
          });
          line.bindPopup(() => layerPopupHtml("cyclones", p, tRef.current), popupOpts);
          group.addLayer(line);
        });
      });
      replaceGroup("cyclones", group);
      return (data.features || []).length;
    };

    setLoading(true);
    setError(null);
    const first = [refreshVectors()];
    if (showCyclones) {
      first.push(loadSafe("cyclones", loadCyclones).then((n) => { countsRef.cyclones = n || 0; }));
    }
    Promise.all(first).finally(() => {
      if (!cancelled) setLoading(false);
    });

    let debounceTimer = 0;
    const onView = () => {
      clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(() => { refreshVectors(); }, 200);
    };
    map.on("moveend", onView);
    map.on("zoomend", onView);

    const onClick = (ev) => {
      if (drawingRef.current) return;
      const { lat, lng } = ev.latlng || {};
      if (lat == null) return;
      fetchJson(atlasPointUrl({ lat, lon: wrapLon(lng), month: m }))
        .then((data) => {
          onPointRef.current?.(data);
          L.popup({ ...popupOpts, className: "bi-climatology-popup" })
            .setLatLng(ev.latlng)
            .setContent(pointPopupHtml(data, tRef.current))
            .openOn(map);
        })
        .catch(() => {});
    };
    map.on("click", onClick);

    return () => {
      cancelled = true;
      clearTimeout(debounceTimer);
      tileAbort.ctrl.abort();
      ctrl.abort();
      map.off("click", onClick);
      map.off("moveend", onView);
      map.off("zoomend", onView);
      Object.values(layersRef.current).forEach((lyr) => {
        if (lyr && map.hasLayer(lyr)) map.removeLayer(lyr);
      });
      layersRef.current = { ...EMPTY_LAYERS };
    };
  }, [mapRef, mapReady, anyOn, showWind, showWave, showCurrent, showCyclones, m]);

  return { loading, error, counts };
}
