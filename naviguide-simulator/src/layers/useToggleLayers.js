import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import { ampStyle } from "./styles.js";
import { SCIENCE_WMS_LAYERS } from "./scienceWms.js";
import { SpatialCatalogLayer } from "./spatialCatalogLayer.js";
import { DEFAULT_SHOW_GRIB, DEFAULT_SHOW_ZEE } from "../constants/layers.js";
import { recetteClimoFlags } from "../utils/recetteQuery.js";

const EMPTY = { type: "FeatureCollection", features: [] };

function lruSet(cache, key, value, maxEntries = 8) {
  if (cache.has(key)) cache.delete(key);
  cache.set(key, value);
  if (cache.size > maxEntries) cache.delete(cache.keys().next().value);
}

function viewportBbox(map) {
  const bounds = map.getBounds().pad(0.18);
  const step = Math.max(0.25, 90 / (2 ** Math.max(0, map.getZoom() - 2)));
  const floor = (value) => Math.floor(value / step) * step;
  const ceil = (value) => Math.ceil(value / step) * step;
  const south = Math.max(-90, bounds.getSouth());
  const north = Math.min(90, bounds.getNorth());
  return [floor(bounds.getWest()), floor(south), ceil(bounds.getEast()), ceil(north)]
    .map((value) => value.toFixed(3))
    .join(",");
}

function useViewportFetchLayer(url, mapRef, mapReady, viewportRevision) {
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const cacheRef = useRef(new Map());
  const toggle = useCallback((fn) => {
    setShow((value) => (typeof fn === "function" ? fn(value) : !value));
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!show || !url || !map || !mapReady) return undefined;
    const bbox = viewportBbox(map);
    const params = new URLSearchParams({
      bbox,
      zoom: String(map.getZoom()),
      limit: "420",
    });
    const requestUrl = `${url}${url.includes("?") ? "&" : "?"}${params}`;
    const hit = cacheRef.current.get(requestUrl);
    if (hit) {
      cacheRef.current.delete(requestUrl);
      cacheRef.current.set(requestUrl, hit);
      setData(hit);
      setLoading(false);
      return undefined;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetch(requestUrl, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((json) => {
        if (controller.signal.aborted) return;
        lruSet(cacheRef.current, requestUrl, json);
        setData(json);
      })
      .catch((err) => {
        if (!controller.signal.aborted) setError(String(err.message || err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [show, url, mapRef, mapReady, viewportRevision]);

  return { show, setShow: toggle, loading, error, data };
}

function usePersistentCatalogLayer(mapRef, mapReady, data, enabled, options) {
  const layerRef = useRef(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return undefined;
    const layer = new SpatialCatalogLayer(map, optionsRef.current);
    layerRef.current = layer;
    return () => {
      layer.remove();
      layerRef.current = null;
    };
  }, [mapRef, mapReady]);

  useEffect(() => {
    const layer = layerRef.current;
    if (!layer) return;
    layer.configure(options);
  }, [options]);

  useEffect(() => {
    const layer = layerRef.current;
    if (!layer) return;
    layer.update(enabled ? data || EMPTY : EMPTY);
  }, [data, enabled]);
}

export function useToggleLayers(
  mapRef,
  onFeature,
  mapReady = 0,
  gateRef,
  { cameraFollowing = false } = {},
) {
  const [showZee, setShowZee] = useState(DEFAULT_SHOW_ZEE);
  const [loadingZee] = useState(false);
  const [errorZee, setErrorZee] = useState(null);
  const [showGrib, setShowGrib] = useState(DEFAULT_SHOW_GRIB);
  const [viewportRevision, setViewportRevision] = useState(0);

  const ports = useViewportFetchLayer("/proxy/ports", mapRef, mapReady, viewportRevision);
  const projects = useViewportFetchLayer("/proxy/catalog/projects", mapRef, mapReady, viewportRevision);
  const marinas = useViewportFetchLayer("/proxy/catalog/marinas", mapRef, mapReady, viewportRevision);
  const capitaineries = useViewportFetchLayer("/proxy/catalog/capitaineries", mapRef, mapReady, viewportRevision);
  const poe = useViewportFetchLayer("/proxy/catalog/poe", mapRef, mapReady, viewportRevision);
  const amp = useViewportFetchLayer("/proxy/catalog/amp", mapRef, mapReady, viewportRevision);
  const sextant = useViewportFetchLayer("/proxy/catalog/science?source=sextant", mapRef, mapReady, viewportRevision);
  const argo = useViewportFetchLayer("/proxy/catalog/science?source=argo", mapRef, mapReady, viewportRevision);
  const odatis = useViewportFetchLayer("/proxy/catalog/science?source=odatis", mapRef, mapReady, viewportRevision);
  const edmed = useViewportFetchLayer("/proxy/catalog/science?source=edmed", mapRef, mapReady, viewportRevision);
  const csr = useViewportFetchLayer("/proxy/catalog/science?source=csr", mapRef, mapReady, viewportRevision);

  const { show: showSextant, setShow: setShowSextant } = sextant;
  const { show: showArgo, setShow: setShowArgo } = argo;
  const { show: showOdatis, setShow: setShowOdatis } = odatis;
  const { show: showEdmed, setShow: setShowEdmed } = edmed;
  const { show: showCsr, setShow: setShowCsr } = csr;
  const [showBathymetry, setShowBathymetryRaw] = useState(false);
  const [showFonds, setShowFondsRaw] = useState(false);
  const [showCables, setShowCablesRaw] = useState(false);

  const [showBalisage, setShowBalisageRaw] = useState(false);
  const gatedSet = useCallback((setter, kind) => (fn) => {
    setter((v) => {
      const next = typeof fn === "function" ? fn(v) : !!fn;
      if (next && gateRef && !gateRef.current?.allowed) {
        gateRef.current?.onNeed?.(kind);
        return v;
      }
      return next;
    });
  }, [gateRef]);
  const setShowBalisage = gatedSet(setShowBalisageRaw, "balisage");
  const setShowBathymetry = gatedSet(setShowBathymetryRaw, "bathymetry");
  const setShowFonds = gatedSet(setShowFondsRaw, "fonds");
  const setShowCables = gatedSet(setShowCablesRaw, "cables");
  const recetteClimo = recetteClimoFlags();
  const [showClimoWind, setShowClimoWind] = useState(recetteClimo.wind);
  const [showClimoWave, setShowClimoWave] = useState(recetteClimo.wave);
  const [showClimoCurrent, setShowClimoCurrent] = useState(recetteClimo.current);
  const [showClimoCyclones, setShowClimoCyclones] = useState(recetteClimo.cyclones);

  const layersRef = useRef({});
  const pointOptions = useMemo(() => ({
    pointFillOpacity: 0.8,
    onFeature,
  }), [onFeature]);
  const sciencePointOptions = useMemo(() => ({
    ...pointOptions,
    pane: "science-tracks",
  }), [pointOptions]);
  const ampOptions = useMemo(() => ({
    pane: "amp",
    pointFillOpacity: 0.72,
    styleFor: (properties) => ampStyle(properties?.lfp),
    onFeature,
  }), [onFeature]);

  usePersistentCatalogLayer(mapRef, mapReady, ports.data, ports.show, {
    ...pointOptions, color: "#f59e0b", kind: "port",
  });
  usePersistentCatalogLayer(mapRef, mapReady, projects.data, projects.show, {
    ...pointOptions, color: "#06b6d4", kind: "project",
  });
  usePersistentCatalogLayer(mapRef, mapReady, marinas.data, marinas.show, {
    ...pointOptions, color: "#ef4444", kind: "marina",
  });
  usePersistentCatalogLayer(mapRef, mapReady, capitaineries.data, capitaineries.show, {
    ...pointOptions, color: "#7dd3fc", kind: "capitainerie",
  });
  usePersistentCatalogLayer(mapRef, mapReady, poe.data, poe.show, {
    ...pointOptions, color: "#d97706", kind: "poe",
  });
  usePersistentCatalogLayer(mapRef, mapReady, amp.data, amp.show, {
    ...ampOptions, color: "#22c55e", kind: "amp",
  });
  usePersistentCatalogLayer(mapRef, mapReady, sextant.data, sextant.show, {
    ...sciencePointOptions, color: "#a78bfa", kind: "science",
  });
  usePersistentCatalogLayer(mapRef, mapReady, argo.data, argo.show, {
    ...sciencePointOptions, color: "#c4b5fd", kind: "science", pointFillOpacity: 0.25,
  });
  usePersistentCatalogLayer(mapRef, mapReady, odatis.data, odatis.show, {
    ...sciencePointOptions, color: "#8b5cf6", kind: "science",
  });
  usePersistentCatalogLayer(mapRef, mapReady, edmed.data, edmed.show, {
    ...sciencePointOptions, color: "#7c3aed", kind: "science",
  });
  usePersistentCatalogLayer(mapRef, mapReady, csr.data, csr.show, {
    ...sciencePointOptions, color: "#6d28d9", kind: "science", pointFillOpacity: 0.45,
  });

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return undefined;
    let timer = null;
    const schedule = () => {
      clearTimeout(timer);
      timer = setTimeout(
        () => setViewportRevision((revision) => revision + 1),
        cameraFollowing ? 950 : 120,
      );
    };
    map.on("moveend", schedule);
    map.on("zoomend", schedule);
    return () => {
      clearTimeout(timer);
      map.off("moveend", schedule);
      map.off("zoomend", schedule);
    };
  }, [mapRef, mapReady, cameraFollowing]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return undefined;
    if (layersRef.current.zee) {
      map.removeLayer(layersRef.current.zee);
      layersRef.current.zee = null;
    }
    if (!showZee) return undefined;
    try {
      const wms = L.tileLayer.wms("/proxy/zee/wms", {
        layers: "eez_boundaries",
        format: "image/png",
        transparent: true,
        version: "1.1.1",
        pane: "zee-wms",
      });
      wms.addTo(map);
      layersRef.current.zee = wms;
    } catch (err) {
      setErrorZee(String(err.message || err));
    }
    return () => {
      if (layersRef.current.zee) {
        map.removeLayer(layersRef.current.zee);
        layersRef.current.zee = null;
      }
    };
  }, [mapRef, mapReady, showZee]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return undefined;
    if (layersRef.current.balisage) {
      map.removeLayer(layersRef.current.balisage);
      layersRef.current.balisage = null;
    }
    if (!showBalisage) return undefined;
    const tiles = L.tileLayer("https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png", {
      pane: "balisage",
      opacity: 0.85,
      errorTileUrl: "",
      attribution: "© OpenSeaMap contributors",
    });
    tiles.on("tileerror", () => {
      if (!layersRef.current.balisageFallback) {
        map.removeLayer(tiles);
        if (layersRef.current.balisage === tiles) {
          layersRef.current.balisage = null;
        }
        layersRef.current.balisageFallback = L.tileLayer("/proxy/seamark/{z}/{x}/{y}.png", {
          pane: "balisage",
          opacity: 0.85,
          attribution: "© OpenSeaMap contributors",
        }).addTo(map);
      }
    });
    tiles.addTo(map);
    layersRef.current.balisage = tiles;
    return () => {
      map.removeLayer(tiles);
      if (layersRef.current.balisageFallback) {
        map.removeLayer(layersRef.current.balisageFallback);
        layersRef.current.balisageFallback = null;
      }
    };
  }, [mapRef, mapReady, showBalisage]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return undefined;
    const enabled = { bathymetry: showBathymetry, substrate: showFonds, cables: showCables };
    const added = [];
    SCIENCE_WMS_LAYERS.forEach((spec) => {
      if (!enabled[spec.id]) return;
      const lyr = L.tileLayer.wms(spec.url, {
        layers: spec.layers,
        format: "image/png",
        transparent: true,
        version: "1.1.1",
        opacity: spec.opacity,
        pane: spec.pane,
        attribution: spec.attribution,
        maxZoom: 18,
      });
      lyr.addTo(map);
      added.push(lyr);
    });
    return () => added.forEach((lyr) => map.removeLayer(lyr));
  }, [mapRef, mapReady, showBathymetry, showFonds, showCables]);

  const scienceLoading = sextant.loading || argo.loading || odatis.loading || edmed.loading || csr.loading;
  const scienceError = sextant.error || argo.error || odatis.error || edmed.error || csr.error || null;

  return useMemo(() => ({
    showGrib,
    setShowGrib,
    loadingGrib: false,
    errorGrib: null,
    showZee,
    setShowZee,
    loadingZee,
    errorZee,
    showPorts: ports.show,
    setShowPorts: ports.setShow,
    loadingPorts: ports.loading,
    errorPorts: ports.error,
    showBalisage,
    setShowBalisage,
    loadingBalisage: false,
    errorBalisage: null,
    showBiProjects: projects.show,
    setShowBiProjects: projects.setShow,
    loadingBiProjects: projects.loading,
    errorBiProjects: projects.error,
    showBiMarinas: marinas.show,
    setShowBiMarinas: marinas.setShow,
    loadingBiMarinas: marinas.loading,
    errorBiMarinas: marinas.error,
    showBiCapitaineries: capitaineries.show,
    setShowBiCapitaineries: capitaineries.setShow,
    loadingBiCapitaineries: capitaineries.loading,
    errorBiCapitaineries: capitaineries.error,
    showBiPoe: poe.show,
    setShowBiPoe: poe.setShow,
    loadingBiPoe: poe.loading,
    errorBiPoe: poe.error,
    showBiAmp: amp.show,
    setShowBiAmp: amp.setShow,
    loadingBiAmp: amp.loading,
    errorBiAmp: amp.error,
    showSextant,
    setShowSextant,
    showArgo,
    setShowArgo,
    showOdatis,
    setShowOdatis,
    showEdmed,
    setShowEdmed,
    showCsr,
    setShowCsr,
    loadingScienceCatalog: scienceLoading,
    errorScienceCatalog: scienceError,
    showBathymetry,
    setShowBathymetry,
    loadingBathymetry: false,
    errorBathymetry: null,
    showFonds,
    setShowFonds,
    loadingFonds: false,
    errorFonds: null,
    showCables,
    setShowCables,
    loadingCables: false,
    errorCables: null,
    showClimoWind,
    setShowClimoWind,
    showClimoWave,
    setShowClimoWave,
    showClimoCurrent,
    setShowClimoCurrent,
    showClimoCyclones,
    setShowClimoCyclones,
    errorClimatology: null,
  }), [
    showGrib, showZee, loadingZee, errorZee,
    ports.show, ports.setShow, ports.loading, ports.error,
    showBalisage, setShowBalisage,
    projects.show, projects.setShow, projects.loading, projects.error,
    marinas.show, marinas.setShow, marinas.loading, marinas.error,
    capitaineries.show, capitaineries.setShow, capitaineries.loading, capitaineries.error,
    poe.show, poe.setShow, poe.loading, poe.error,
    amp.show, amp.setShow, amp.loading, amp.error,
    showSextant, showArgo, showOdatis, showEdmed, showCsr,
    scienceLoading, scienceError,
    showBathymetry, setShowBathymetry,
    showFonds, setShowFonds,
    showCables, setShowCables,
    showClimoWind, showClimoWave, showClimoCurrent, showClimoCyclones,
  ]);
}
