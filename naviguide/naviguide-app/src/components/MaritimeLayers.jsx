/**
 * MaritimeLayers — maritime data layers for MapLibre GL JS
 *
 *  1. EEZ         — Exclusive Economic Zones (VLIZ / Marine Regions, via WFS proxy)
 *  2. WPI Ports   — World Port Index (NGA/MSI REST, via proxy, DMS→decimal coords)
 *  3. Marks       — maritime marks via OpenSeaMap raster tiles (public, no auth)
 *                   NOTE: SHOM WFS replaced because it requires authentication (401).
 *  4. Blue Intelligence — the 5 blueintelligence.online modes as GeoJSON points
 *     (Projects, Marinas, Harbour masters, Ports of Entry, MPAs), loaded on demand
 *     via the same-origin "/bi" proxy → Blue Intelligence /api/export/*.
 *
 * Exports:
 *  - useMaritimeLayers()        → hook (state + data fetching)
 *  - MaritimeLayers(props)      → Sources/Layers to place INSIDE <Map>
 *  - MaritimeLayersPanel(props) → floating toggle panel (OUTSIDE <Map>)
 *  - BI_LAYER_CONFIG            → Blue Intelligence toggle config (Sidebar)
 */

import { useEffect, useState } from "react";
import { Source, Layer } from "react-map-gl/maplibre";
import { useLang } from "../i18n/LangContext.jsx";

// Always an absolute URL for tiles (avoids Vite / preview proxy issues).
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
// Blue Intelligence exports — same-origin by default: vite proxy in dev,
// nginx (VPS) ou proxy_server.py (complete.dev) en production.
const BI_BASE = import.meta.env.VITE_BI_API_URL || "/bi";
const EMPTY_FC = { type: "FeatureCollection", features: [] };

// ── Layer paint styles ────────────────────────────────────────────────────────

// EEZ via WMS — eez_boundaries layer = boundaries only (polylines, no polygons)
// 512×512 tiles for a sharper render at minimum zoom (less blur/thickness)
const ZEE_WMS_TILES = [
  `${API_BASE}/proxy/zee/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=eez_boundaries&FORMAT=image/png&TRANSPARENT=true&SRS=EPSG:3857&WIDTH=512&HEIGHT=512&BBOX={bbox-epsg-3857}`,
];
const PORTS_CIRCLE_PAINT = {
  "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 2, 6, 4, 10, 7],
  "circle-color": "#f59e0b",
  "circle-stroke-width": 1,
  "circle-stroke-color": "#fff",
  "circle-opacity": 0.85,
};

// Blue Intelligence mode colors (see Blue Intelligence README)
export const BI_COLORS = {
  biProjects:      "#06b6d4", // cyan  — marine conservation projects
  biMarinas:       "#ef4444", // red   — OSM marinas
  biCapitaineries: "#7dd3fc", // sky   — harbour masters
  biPoe:           "#d97706", // amber — Ports of Entry (formalities)
  biAmp:           "#22c55e", // green — Marine Protected Areas (centroids)
};

// Dense layers (marinas ≈ tens of thousands of points) → finer circles
const biCirclePaint = (color) => ({
  "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 1.5, 6, 3.5, 10, 6.5],
  "circle-color": color,
  "circle-stroke-width": 1,
  "circle-stroke-color": "#fff",
  "circle-opacity": 0.85,
});
// OpenSeaMap tiles — raster overlay, opacity controlled via show flag
const OPENSEAMAP_RASTER_PAINT = {
  "raster-opacity": 0.85,
};

// ── Fetchers ──────────────────────────────────────────────────────────────────

async function fetchPorts() {
  const url = `${API_BASE}/proxy/ports`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Ports HTTP ${res.status}`);
  return res.json();
}

// ── Hook ──────────────────────────────────────────────────────────────────────

/**
 * useBiLayer — one Blue Intelligence layer: OFF by default,
 * fetch on the first switch to ON (exports can be large).
 */
function useBiLayer(path) {
  const [show, setShow] = useState(false);
  const [data, setData] = useState(EMPTY_FC);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!show || data.features.length > 0) return;
    setLoading(true);
    setError(null);
    fetch(`${BI_BASE}${path}`)
      .then((res) => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json(); })
      .then((fc) => setData(fc?.type === "FeatureCollection" ? fc : EMPTY_FC))
      .catch((e) => {
        console.warn("[MaritimeLayers] Blue Intelligence", path, e.message || e);
        setError(e.message || String(e));
      })
      .finally(() => setLoading(false));
  }, [show]);

  return { show, setShow, data, loading, error };
}

/**
 * useMaritimeLayers
 * Manages ON/OFF state, GeoJSON data and loading states
 * for maritime layers and Blue Intelligence layers.
 */
/**
 * MPA polygons via GET /amp?bbox= (not the centroid export).
 */
function useAmpPolygons(mapRef) {
  const [show, setShow] = useState(false);
  const [data, setData] = useState(EMPTY_FC);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!show) return undefined;
    let cancelled = false;
    let timer = null;

    const load = () => {
      const map = mapRef?.current?.getMap?.();
      if (!map) return;
      const b = map.getBounds();
      const bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(",");
      setLoading(true);
      setError(null);
      fetch(`${BI_BASE}/amp?bbox=${encodeURIComponent(bbox)}`)
        .then((res) => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json(); })
        .then((fc) => {
          if (!cancelled) setData(fc?.type === "FeatureCollection" ? fc : EMPTY_FC);
        })
        .catch((e) => {
          if (!cancelled) {
            console.warn("[MaritimeLayers] AMP", e.message || e);
            setError(e.message || String(e));
          }
        })
        .finally(() => { if (!cancelled) setLoading(false); });
    };

    const schedule = () => {
      clearTimeout(timer);
      timer = setTimeout(load, 420);
    };

    const attach = () => {
      const map = mapRef?.current?.getMap?.();
      if (!map) return false;
      map.on("moveend", schedule);
      map.on("zoomend", schedule);
      load();
      return true;
    };

    if (!attach()) {
      const poll = setInterval(() => { if (attach()) clearInterval(poll); }, 250);
      return () => {
        cancelled = true;
        clearInterval(poll);
        clearTimeout(timer);
      };
    }

    return () => {
      cancelled = true;
      clearTimeout(timer);
      const map = mapRef?.current?.getMap?.();
      if (map) {
        map.off("moveend", schedule);
        map.off("zoomend", schedule);
      }
    };
  }, [show, mapRef]);

  return { show, setShow, data, loading, error };
}

export function useMaritimeLayers(mapRef) {
  // Layers on by default — deferred load so the first paint is not blocked
  const [showZee,      setShowZee]      = useState(false);
  const [showPorts,    setShowPorts]    = useState(false);
  const [showBalisage, setShowBalisage] = useState(true);

  const [portsData, setPortsData] = useState(EMPTY_FC);

  const [loadingPorts, setLoadingPorts] = useState(false);

  const [errorPorts, setErrorPorts] = useState(null);

  // Ports load — immediate
  useEffect(() => {
    if (!showPorts || portsData.features.length > 0) return;
    setLoadingPorts(true);
    setErrorPorts(null);
    fetchPorts()
      .then((data) => { setPortsData(data); })
      .catch((e) => { console.warn("[MaritimeLayers] Ports:", e.message || e); setErrorPorts(e.message || String(e)); })
      .finally(() => setLoadingPorts(false));
  }, [showPorts]);

  // Blue Intelligence layers — the 5 blueintelligence.online modes
  const biProjects      = useBiLayer("/export/geojson");
  const biMarinas       = useBiLayer("/export/marinas.geojson");
  const biCapitaineries = useBiLayer("/export/capitaineries.geojson");
  const biPoe           = useBiLayer("/export/poe.geojson");
  const biAmp           = useAmpPolygons(mapRef);

  return {
    // Toggles
    showZee,      setShowZee,
    showPorts,    setShowPorts,
    showBalisage, setShowBalisage,
    // Data
    portsData,
    // Loading flags
    loadingZee: false,   // ZEE WMS = tuiles, pas de fetch
    loadingPorts,
    loadingBalisage: false,
    // Error messages
    errorZee: null,
    errorPorts,
    errorBalisage: null,
    // Blue Intelligence — Projets
    showBiProjects: biProjects.show,           setShowBiProjects: biProjects.setShow,
    biProjectsData: biProjects.data,
    loadingBiProjects: biProjects.loading,     errorBiProjects: biProjects.error,
    // Blue Intelligence — Marinas
    showBiMarinas: biMarinas.show,             setShowBiMarinas: biMarinas.setShow,
    biMarinasData: biMarinas.data,
    loadingBiMarinas: biMarinas.loading,       errorBiMarinas: biMarinas.error,
    // Blue Intelligence — Capitaineries
    showBiCapitaineries: biCapitaineries.show, setShowBiCapitaineries: biCapitaineries.setShow,
    biCapitaineriesData: biCapitaineries.data,
    loadingBiCapitaineries: biCapitaineries.loading, errorBiCapitaineries: biCapitaineries.error,
    // Blue Intelligence — Ports of Entry (formalities)
    showBiPoe: biPoe.show,                     setShowBiPoe: biPoe.setShow,
    biPoeData: biPoe.data,
    loadingBiPoe: biPoe.loading,               errorBiPoe: biPoe.error,
    // Blue Intelligence — AMP
    showBiAmp: biAmp.show,                     setShowBiAmp: biAmp.setShow,
    biAmpData: biAmp.data,
    loadingBiAmp: biAmp.loading,               errorBiAmp: biAmp.error,
  };
}

// ── Map layers (render inside <Map>) ─────────────────────────────────────────

/**
 * MaritimeLayers
 * Place MapLibre GL JS Sources/Layers in the <Map> component tree.
 *
 * IMPORTANT: every source is ALWAYS mounted (no conditional render).
 * Visibility is controlled via layout.visibility to avoid MapLibre
 * source mount/unmount errors ("Source already exists", race conditions).
 *
 *  - EEZ       : GeoJSON polygons via backend proxy
 *  - WPI Ports : GeoJSON points via backend proxy
 *  - Marks     : OpenSeaMap raster tiles (loaded directly from the browser)
 */
export function MaritimeLayers({
  showZee,
  showPorts, portsData,
  showBiProjects,      biProjectsData,
  showBiMarinas,       biMarinasData,
  showBiCapitaineries, biCapitaineriesData,
  showBiPoe,           biPoeData,
  showBiAmp,           biAmpData,
}) {
  const vis = (flag) => ({ visibility: flag ? "visible" : "none" });

  return (
    <>
      {/* ── EEZ via WMS (tiles on demand, instant) ────────────────── */}
      <Source
        id="zee-source"
        type="raster"
        tiles={ZEE_WMS_TILES}
        tileSize={512}
        minzoom={1}
        maxzoom={18}
      >
        <Layer
          id="zee-layer"
          type="raster"
          layout={vis(showZee)}
          paint={{
            "raster-opacity": ["interpolate", ["linear"], ["zoom"], 1, 0.25, 3, 0.45, 6, 0.7, 10, 0.9],
            "raster-fade-duration": 0,
            "raster-resampling": "nearest",
          }}
        />
      </Source>

      {/* ── WPI ports circles ───────────────────────────────────────────── */}
      <Source id="ports-source" type="geojson" data={portsData}>
        <Layer id="ports-circle" type="circle" layout={vis(showPorts)} paint={PORTS_CIRCLE_PAINT} />
      </Source>

      {/* ── Blue Intelligence — 5 modes en points (couleurs du site BI) ──── */}
      <Source id="bi-amp-source" type="geojson" data={biAmpData ?? EMPTY_FC}>
        <Layer
          id="bi-amp-fill"
          type="fill"
          layout={vis(showBiAmp)}
          filter={["match", ["geometry-type"], ["Polygon", "MultiPolygon"], true, false]}
          paint={{ "fill-color": BI_COLORS.biAmp, "fill-opacity": 0.28 }}
        />
        <Layer
          id="bi-amp-line"
          type="line"
          layout={vis(showBiAmp)}
          filter={["match", ["geometry-type"], ["Polygon", "MultiPolygon"], true, false]}
          paint={{ "line-color": "#15803d", "line-width": 1.2 }}
        />
        <Layer
          id="bi-amp-circle"
          type="circle"
          layout={vis(showBiAmp)}
          filter={["==", ["geometry-type"], "Point"]}
          paint={biCirclePaint(BI_COLORS.biAmp)}
        />
      </Source>
      <Source id="bi-projects-source" type="geojson" data={biProjectsData ?? EMPTY_FC}>
        <Layer id="bi-projects-circle" type="circle" layout={vis(showBiProjects)} paint={biCirclePaint(BI_COLORS.biProjects)} />
      </Source>
      <Source id="bi-marinas-source" type="geojson" data={biMarinasData ?? EMPTY_FC}>
        <Layer id="bi-marinas-circle" type="circle" layout={vis(showBiMarinas)} paint={biCirclePaint(BI_COLORS.biMarinas)} />
      </Source>
      <Source id="bi-capitaineries-source" type="geojson" data={biCapitaineriesData ?? EMPTY_FC}>
        <Layer id="bi-capitaineries-circle" type="circle" layout={vis(showBiCapitaineries)} paint={biCirclePaint(BI_COLORS.biCapitaineries)} />
      </Source>
      <Source id="bi-poe-source" type="geojson" data={biPoeData ?? EMPTY_FC}>
        <Layer id="bi-poe-circle" type="circle" layout={vis(showBiPoe)} paint={biCirclePaint(BI_COLORS.biPoe)} />
      </Source>
    </>
  );
}

/** Marks — raster above everything (routes, markers). Place LAST inside <Map>. */
const SEAMARK_TILES = [
  `${API_BASE}/proxy/seamark/{z}/{x}/{y}.png`,
  "https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png",
];

export function BalisageLayer({ show }) {
  return (
    <Source
      id="openseamap-source"
      type="raster"
      tiles={SEAMARK_TILES}
      tileSize={256}
      minzoom={1}
      maxzoom={19}
      attribution="© OpenSeaMap"
    >
      <Layer
        id="openseamap-layer"
        type="raster"
        layout={{ visibility: show ? "visible" : "none" }}
        paint={{
          "raster-opacity": 1,
          "raster-fade-duration": 0,
        }}
      />
    </Source>
  );
}

// ── Toggle panel (render outside <Map>) ──────────────────────────────────────

const LAYER_CONFIG = [
  { key: "balisage", labelKey: "layerBalisage", titleKey: "layerBalisageTitle", color: "#10b981", showKey: "showBalisage", toggleKey: "setShowBalisage", loadingKey: "loadingBalisage", errorKey: "errorBalisage" },
];

/** Every map layer — a single grid of chips in the Sidebar. */
export const ALL_LAYER_CONFIG = [
  ...LAYER_CONFIG,
  { key: "biProjects",      labelKey: "layerBiProjects",      titleKey: "layerBiProjectsTitle",      color: BI_COLORS.biProjects,      showKey: "showBiProjects",      toggleKey: "setShowBiProjects",      loadingKey: "loadingBiProjects",      errorKey: "errorBiProjects" },
  { key: "biMarinas",       labelKey: "layerBiMarinas",       titleKey: "layerBiMarinasTitle",       color: BI_COLORS.biMarinas,       showKey: "showBiMarinas",       toggleKey: "setShowBiMarinas",       loadingKey: "loadingBiMarinas",       errorKey: "errorBiMarinas" },
  { key: "biCapitaineries", labelKey: "layerBiCapitaineries", titleKey: "layerBiCapitaineriesTitle", color: BI_COLORS.biCapitaineries, showKey: "showBiCapitaineries", toggleKey: "setShowBiCapitaineries", loadingKey: "loadingBiCapitaineries", errorKey: "errorBiCapitaineries" },
  { key: "biPoe",           labelKey: "layerBiPoe",           titleKey: "layerBiPoeTitle",           color: BI_COLORS.biPoe,           showKey: "showBiPoe",           toggleKey: "setShowBiPoe",           loadingKey: "loadingBiPoe",           errorKey: "errorBiPoe" },
  { key: "biAmp",           labelKey: "layerBiAmp",           titleKey: "layerBiAmpTitle",           color: BI_COLORS.biAmp,           showKey: "showBiAmp",           toggleKey: "setShowBiAmp",           loadingKey: "loadingBiAmp",           errorKey: "errorBiAmp" },
];

/** @deprecated — utiliser ALL_LAYER_CONFIG */
export const BI_LAYER_CONFIG = [
  { key: "biProjects",      labelKey: "layerBiProjects",      titleKey: "layerBiProjectsTitle",      color: BI_COLORS.biProjects,      showKey: "showBiProjects",      toggleKey: "setShowBiProjects",      loadingKey: "loadingBiProjects",      errorKey: "errorBiProjects" },
  { key: "biMarinas",       labelKey: "layerBiMarinas",       titleKey: "layerBiMarinasTitle",       color: BI_COLORS.biMarinas,       showKey: "showBiMarinas",       toggleKey: "setShowBiMarinas",       loadingKey: "loadingBiMarinas",       errorKey: "errorBiMarinas" },
  { key: "biCapitaineries", labelKey: "layerBiCapitaineries", titleKey: "layerBiCapitaineriesTitle", color: BI_COLORS.biCapitaineries, showKey: "showBiCapitaineries", toggleKey: "setShowBiCapitaineries", loadingKey: "loadingBiCapitaineries", errorKey: "errorBiCapitaineries" },
  { key: "biPoe",           labelKey: "layerBiPoe",           titleKey: "layerBiPoeTitle",           color: BI_COLORS.biPoe,           showKey: "showBiPoe",           toggleKey: "setShowBiPoe",           loadingKey: "loadingBiPoe",           errorKey: "errorBiPoe" },
  { key: "biAmp",           labelKey: "layerBiAmp",           titleKey: "layerBiAmpTitle",           color: BI_COLORS.biAmp,           showKey: "showBiAmp",           toggleKey: "setShowBiAmp",           loadingKey: "loadingBiAmp",           errorKey: "errorBiAmp" },
];

/**
 * MaritimeLayersPanel
 * Floating panel with toggle buttons for each maritime layer.
 * Place OUTSIDE the <Map> component, in the application root div.
 */
export function MaritimeLayersPanel(props) {
  const { t } = useLang();
  return (
    /* Centered at the bottom, between the two sidebars (320px each) — always visible */
    <div
      className="absolute bottom-5 left-1/2 -translate-x-1/2 z-25 flex flex-row items-center gap-1.5
                 bg-slate-900/80 backdrop-blur-sm border border-white/10 rounded-full px-3 py-1.5 shadow-xl"
      style={{ pointerEvents: "auto", zIndex: 25 }}
    >
      {/* Label */}
      <span className="text-white/35 text-[9px] font-semibold uppercase tracking-widest mr-1 select-none">
        {t("layersLabel")}
      </span>

      {LAYER_CONFIG.map(({ key, labelKey, titleKey, color, showKey, toggleKey, loadingKey, errorKey }) => {
        const active  = props[showKey];
        const loading = props[loadingKey];
        const error   = props[errorKey];

        return (
          <button
            key={key}
            onClick={() => props[toggleKey]((v) => !v)}
            title={t(titleKey)}
            className={[
              "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold",
              "transition-all duration-150 select-none",
              active
                ? "bg-slate-700/90 text-white border border-white/20"
                : "bg-transparent text-white/45 border border-white/10 hover:text-white/80 hover:bg-slate-700/50",
              error ? "border-red-500/50" : "",
            ].join(" ")}
          >
            {loading ? (
              <div className="w-2 h-2 rounded-full border-2 border-white/30 border-t-white animate-spin flex-shrink-0" />
            ) : (
              <div
                className="w-2 h-2 rounded-full flex-shrink-0 transition-colors"
                style={{
                  backgroundColor: active ? color : "transparent",
                  border: `1.5px solid ${error ? "#ef4444" : color}`,
                }}
              />
            )}
            <span>{t(labelKey)}</span>
            {error && !loading && (
              <span className="text-red-400 text-[10px]" title={error}>⚠</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
