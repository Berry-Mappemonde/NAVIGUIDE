import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { atlasLayerUrl, atlasPointUrl, clampMonth } from "../utils/atlasPoint.js";
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

const EMPTY_LAYERS = { wind: null, waveP50: null, waveP90: null, waveMean: null, current: null, cyclones: null };

/**
 * Four atlas maps (wind / wave / current / cyclones), each optional.
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
    const popupOpts = { ...POPUP_OPTS, maxWidth: 300 };

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

    const loadWind = async () => {
      const data = await fetchJson(atlasLayerUrl("wind", m, { spacing_deg: "4" }), ctrl.signal);
      if (cancelled) return 0;
      const group = addPointMarkers(data, (ll, p) => {
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
      });
      layersRef.current.wind = group;
      group.addTo(map);
      return (data.features || []).length;
    };

    const loadWave = async (stat) => {
      const data = await fetchJson(atlasLayerUrl("wave", m, { stat, spacing_deg: "4" }), ctrl.signal);
      if (cancelled) return 0;
      const group = addPointMarkers(data, (ll, p) => {
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
      });
      const key = stat === "p50" ? "waveP50" : stat === "p90" ? "waveP90" : "waveMean";
      layersRef.current[key] = group;
      group.addTo(map);
      return (data.features || []).length;
    };

    const loadCurrent = async () => {
      const data = await fetchJson(atlasLayerUrl("current", m, { spacing_deg: "4" }), ctrl.signal);
      if (cancelled) return 0;
      const group = addPointMarkers(data, (ll, p) => {
        if (p.below_threshold) return null;
        const marker = L.marker(ll, {
          icon: currentIcon(p),
          pane: "climatology-vector",
          interactive: false,
        });
        marker.bindPopup(() => layerPopupHtml("current", p, tRef.current), popupOpts);
        return marker;
      });
      layersRef.current.current = group;
      group.addTo(map);
      return (data.features || []).length;
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
      layersRef.current.cyclones = group;
      group.addTo(map);
      return (data.features || []).length;
    };

    setLoading(true);
    setError(null);
    const jobs = [];
    if (showWind) jobs.push(loadSafe("wind", loadWind));
    if (showWave) {
      jobs.push(loadSafe("wave-p50", () => loadWave("p50")));
      jobs.push(loadSafe("wave-p90", () => loadWave("p90")));
    }
    if (showCurrent) jobs.push(loadSafe("current", loadCurrent));
    if (showCyclones) jobs.push(loadSafe("cyclones", loadCyclones));

    Promise.all(jobs).then(async (nums) => {
      if (cancelled) return;
      const next = { wind: 0, waveP50: 0, waveP90: 0, waveMean: 0, current: 0, cyclones: 0 };
      let i = 0;
      if (showWind) next.wind = nums[i++] || 0;
      if (showWave) {
        next.waveP50 = nums[i++] || 0;
        next.waveP90 = nums[i++] || 0;
        if (!next.waveP50 && !next.waveP90) {
          next.waveMean = await loadSafe("wave-mean", () => loadWave("mean"));
        }
      }
      if (showCurrent) next.current = nums[i++] || 0;
      if (showCyclones) next.cyclones = nums[i++] || 0;
      setCounts(next);
      const painted = Object.values(next).some(Boolean);
      if (!painted) setError("atlas_empty");
    }).catch((err) => {
      if (!cancelled) setError(String(err.message || err));
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });

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
      ctrl.abort();
      map.off("click", onClick);
      Object.values(layersRef.current).forEach((lyr) => {
        if (lyr && map.hasLayer(lyr)) map.removeLayer(lyr);
      });
      layersRef.current = { ...EMPTY_LAYERS };
    };
  }, [mapRef, mapReady, anyOn, showWind, showWave, showCurrent, showCyclones, m]);

  return { loading, error, counts };
}
