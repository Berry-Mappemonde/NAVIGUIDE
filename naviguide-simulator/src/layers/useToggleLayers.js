import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import { ampStyle } from "./styles.js";
import { circleOpts, makePointGroup } from "./points.js";
import { filterScienceFeatures } from "./scienceSource.js";
import { SCIENCE_WMS_LAYERS } from "./scienceWms.js";
import {
  aggregatePointFeatures,
  POINT_RENDER_BUDGET,
  visibleFeatureCollection,
} from "./spatialFeatures.js";
import { DEFAULT_SHOW_GRIB, DEFAULT_SHOW_ZEE } from "../constants/layers.js";
import { recetteClimoFlags } from "../utils/recetteQuery.js";

const BI_BASE = import.meta.env.VITE_BI_BASE ?? "/bi";
const EMPTY = { type: "FeatureCollection", features: [] };

function useFetchLayer(url, { lazy = true } = {}) {
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const fetched = useRef(false);

  const toggle = useCallback((fn) => {
    setShow((v) => {
      const next = typeof fn === "function" ? fn(v) : !v;
      return next;
    });
  }, []);

  useEffect(() => {
    if (!show || !url || fetched.current) return undefined;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((json) => {
        if (cancelled) return;
        fetched.current = true;
        setData(json);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err.message || err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [show, url, lazy]);

  return { show, setShow: toggle, loading, error, data };
}

function useLazyJson(enabled, url) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const fetched = useRef(false);

  useEffect(() => {
    if (!enabled || !url || fetched.current) return undefined;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((json) => {
        if (cancelled) return;
        fetched.current = true;
        setData(json);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err.message || err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [enabled, url]);

  return { data, loading, error };
}

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
  return [floor(bounds.getWest()), floor(bounds.getSouth()), ceil(bounds.getEast()), ceil(bounds.getNorth())]
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
    const requestUrl = `${url}${url.includes("?") ? "&" : "?"}bbox=${encodeURIComponent(bbox)}`;
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

function addPointLayer(map, fc, color, kind, onFeature) {
  const group = makePointGroup();
  const zoom = map.getZoom();
  const renderer = group._biRenderer;
  const visible = visibleFeatureCollection(fc, map.getBounds().pad(0.18));
  const features = aggregatePointFeatures(
    visible.features,
    (lon, lat) => map.latLngToContainerPoint([lat, lon]),
    { budget: POINT_RENDER_BUDGET },
  );
  features.forEach((f) => {
    if (f.geometry?.type !== "Point") return;
    const [lon, lat] = f.geometry.coordinates;
    const clusterCount = Number(f.properties?.clusterCount) || 1;
    const m = L.circleMarker([lat, lon], circleOpts(color, {
      zoom,
      bump: clusterCount > 1 ? Math.min(6, Math.log2(clusterCount)) : 0,
      renderer,
    }));
    m.on("click", (e) => {
      L.DomEvent.stopPropagation(e);
      onFeature?.({ lon, lat, kind, props: f.properties || {} });
    });
    group.addLayer(m);
  });
  group.addTo(map);
  return group;
}

function addScienceSourceLayer(map, fc, source, color, onFeature) {
  const filtered = visibleFeatureCollection(
    filterScienceFeatures(fc, source),
    map.getBounds().pad(0.18),
  );
  const group = makePointGroup();
  const zoom = map.getZoom();
  const renderer = group._biRenderer;
  const points = aggregatePointFeatures(
    filtered.features,
    (lon, lat) => map.latLngToContainerPoint([lat, lon]),
    { budget: POINT_RENDER_BUDGET },
  );
  const lines = filtered.features.filter((f) => f.geometry?.type === "LineString");
  [...lines, ...points].forEach((f) => {
    const props = f.properties || {};
    const geom = f.geometry || {};
    if (geom.type === "LineString") {
      const latlngs = (geom.coordinates || [])
        .filter((pt) => Array.isArray(pt) && pt.length >= 2)
        .map(([lon, lat]) => [lat, lon]);
      if (latlngs.length < 2) return;
      const line = L.polyline(latlngs, {
        color,
        weight: 2.5,
        opacity: 0.85,
        pane: "science-tracks",
      });
      line.on("click", (e) => {
        L.DomEvent.stopPropagation(e);
        onFeature?.({ lon: e.latlng.lng, lat: e.latlng.lat, kind: "science", props });
      });
      group.addLayer(line);
      return;
    }
    if (geom.type !== "Point") return;
    const [lon, lat] = geom.coordinates;
    const fill = props.kind === "argo_float" ? 0.25 : props.kind === "cruise" ? 0.45 : 0.85;
    const clusterCount = Number(props.clusterCount) || 1;
    const m = L.circleMarker([lat, lon], circleOpts(color, {
      zoom,
      bump: clusterCount > 1 ? Math.min(6, Math.log2(clusterCount)) : 0,
      fillOpacity: fill,
      renderer,
    }));
    m.on("click", (e) => {
      L.DomEvent.stopPropagation(e);
      onFeature?.({ lon, lat, kind: "science", props });
    });
    group.addLayer(m);
  });
  group.addTo(map);
  return group;
}

export function useToggleLayers(
  mapRef,
  onFeature,
  mapReady = 0,
  gateRef,
  { cameraFollowing = false } = {},
) {
  const zee = useFetchLayer(null);
  const [showZee, setShowZee] = useState(DEFAULT_SHOW_ZEE);
  const [loadingZee] = useState(false);
  const [errorZee, setErrorZee] = useState(null);
  const [showGrib, setShowGrib] = useState(DEFAULT_SHOW_GRIB);
  const [viewportRevision, setViewportRevision] = useState(0);

  const ports = useViewportFetchLayer("/proxy/ports", mapRef, mapReady, viewportRevision);
  const projects = useFetchLayer(`${BI_BASE}/export/geojson`);
  const marinas = useFetchLayer(`${BI_BASE}/export/marinas.geojson`);
  const capitaineries = useFetchLayer(`${BI_BASE}/export/capitaineries.geojson`);
  const poe = useFetchLayer(`${BI_BASE}/export/poe.geojson`);

  const [showSextant, setShowSextant] = useState(false);
  const [showArgo, setShowArgo] = useState(false);
  const [showOdatis, setShowOdatis] = useState(false);
  const [showEdmed, setShowEdmed] = useState(false);
  const [showCsr, setShowCsr] = useState(false);
  const [showBathymetry, setShowBathymetryRaw] = useState(false);
  const [showFonds, setShowFondsRaw] = useState(false);
  const [showCables, setShowCablesRaw] = useState(false);
  const scienceCatalogOn = showSextant || showArgo || showOdatis || showEdmed || showCsr;
  const scienceCatalog = useLazyJson(scienceCatalogOn, `${BI_BASE}/export/science.geojson`);

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
  const [showAmp, setShowAmp] = useState(false);
  const [loadingAmp, setLoadingAmp] = useState(false);
  const [errorAmp, setErrorAmp] = useState(null);
  const [ampData, setAmpData] = useState(EMPTY);
  const recetteClimo = recetteClimoFlags();
  const [showClimoWind, setShowClimoWind] = useState(recetteClimo.wind);
  const [showClimoWave, setShowClimoWave] = useState(recetteClimo.wave);
  const [showClimoCurrent, setShowClimoCurrent] = useState(recetteClimo.current);
  const [showClimoCyclones, setShowClimoCyclones] = useState(recetteClimo.cyclones);

  const layersRef = useRef({});
  const ampRequestRef = useRef({ id: 0, controller: null });
  const ampCacheRef = useRef(new Map());

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
    if (!map || !mapReady || !ports.show || !ports.data) return undefined;
    const g = addPointLayer(map, ports.data, "#f59e0b", "port", onFeature);
    return () => map.removeLayer(g);
  }, [mapRef, mapReady, ports.show, ports.data, onFeature, viewportRevision]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !projects.show || !projects.data) return undefined;
    const g = addPointLayer(map, projects.data, "#06b6d4", "project", onFeature);
    return () => map.removeLayer(g);
  }, [mapRef, mapReady, projects.show, projects.data, onFeature, viewportRevision]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !marinas.show || !marinas.data) return undefined;
    const g = addPointLayer(map, marinas.data, "#ef4444", "marina", onFeature);
    return () => map.removeLayer(g);
  }, [mapRef, mapReady, marinas.show, marinas.data, onFeature, viewportRevision]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !capitaineries.show || !capitaineries.data) return undefined;
    const g = addPointLayer(map, capitaineries.data, "#7dd3fc", "capitainerie", onFeature);
    return () => map.removeLayer(g);
  }, [mapRef, mapReady, capitaineries.show, capitaineries.data, onFeature, viewportRevision]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !poe.show || !poe.data) return undefined;
    const g = addPointLayer(map, poe.data, "#d97706", "poe", onFeature);
    return () => map.removeLayer(g);
  }, [mapRef, mapReady, poe.show, poe.data, onFeature, viewportRevision]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !scienceCatalog.data) return undefined;
    const added = [];
    const specs = [
      [showSextant, "sextant", "#a78bfa"],
      [showArgo, "argo", "#c4b5fd"],
      [showOdatis, "odatis", "#8b5cf6"],
      [showEdmed, "edmed", "#7c3aed"],
      [showCsr, "csr", "#6d28d9"],
    ];
    specs.forEach(([on, source, color]) => {
      if (!on) return;
      added.push(addScienceSourceLayer(map, scienceCatalog.data, source, color, onFeature));
    });
    return () => added.forEach((g) => map.removeLayer(g));
  }, [mapRef, mapReady, scienceCatalog.data, showSextant, showArgo, showOdatis, showEdmed, showCsr, onFeature, viewportRevision]);

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

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !showAmp || cameraFollowing) return undefined;
    let debounce = null;
    const load = () => {
      const bbox = viewportBbox(map);
      const cached = ampCacheRef.current.get(bbox);
      if (cached) {
        ampCacheRef.current.delete(bbox);
        ampCacheRef.current.set(bbox, cached);
        setAmpData(cached);
        setLoadingAmp(false);
        setErrorAmp(null);
        return;
      }
      const previous = ampRequestRef.current;
      if (previous.bbox === bbox && previous.controller) return;
      previous.controller?.abort();
      const controller = new AbortController();
      const id = previous.id + 1;
      ampRequestRef.current = { id, controller, bbox };
      setLoadingAmp(true);
      setErrorAmp(null);
      fetch(`${BI_BASE}/amp?bbox=${bbox}`, { signal: controller.signal })
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then((json) => {
          if (ampRequestRef.current.id === id) {
            lruSet(ampCacheRef.current, bbox, json, 8);
            setAmpData(json);
          }
        })
        .catch((err) => {
          if (!controller.signal.aborted && ampRequestRef.current.id === id) {
            setErrorAmp(String(err.message || err));
          }
        })
        .finally(() => {
          if (ampRequestRef.current.id === id) {
            ampRequestRef.current.controller = null;
            setLoadingAmp(false);
          }
        });
    };
    const onMove = () => {
      clearTimeout(debounce);
      debounce = setTimeout(load, 420);
    };
    debounce = setTimeout(load, 420);
    map.on("moveend", onMove);
    return () => {
      clearTimeout(debounce);
      map.off("moveend", onMove);
      ampRequestRef.current.id += 1;
      ampRequestRef.current.controller?.abort();
      ampRequestRef.current.controller = null;
      setLoadingAmp(false);
    };
  }, [mapRef, mapReady, showAmp, cameraFollowing]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !showAmp || !ampData) return undefined;
    const layer = L.geoJSON(ampData, {
      pane: "amp",
      style: (f) => ampStyle(f.properties?.lfp),
      pointToLayer: (f, latlng) => L.circleMarker(latlng, { radius: 5, color: "#22c55e" }),
      onEachFeature: (f, lyr) => {
        lyr.on("click", (e) => {
          L.DomEvent.stopPropagation(e);
          const ll = e.latlng;
          onFeature?.({ lon: ll.lng, lat: ll.lat, kind: "amp", props: f.properties || {} });
        });
      },
    }).addTo(map);
    return () => map.removeLayer(layer);
  }, [mapRef, mapReady, showAmp, ampData, onFeature]);

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
    showBiAmp: showAmp,
    setShowBiAmp: setShowAmp,
    loadingBiAmp: loadingAmp,
    errorBiAmp: errorAmp,
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
    loadingScienceCatalog: scienceCatalog.loading,
    errorScienceCatalog: scienceCatalog.error,
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
    zee: {
      show: zee.show,
      setShow: zee.setShow,
      loading: zee.loading,
      error: zee.error,
      data: zee.data,
    },
  }), [
    showGrib, showZee, loadingZee, errorZee,
    ports.show, ports.setShow, ports.loading, ports.error,
    showBalisage, setShowBalisage,
    projects.show, projects.setShow, projects.loading, projects.error,
    marinas.show, marinas.setShow, marinas.loading, marinas.error,
    capitaineries.show, capitaineries.setShow, capitaineries.loading, capitaineries.error,
    poe.show, poe.setShow, poe.loading, poe.error,
    showAmp, loadingAmp, errorAmp,
    showSextant, showArgo, showOdatis, showEdmed, showCsr,
    scienceCatalog.loading, scienceCatalog.error,
    showBathymetry, setShowBathymetry,
    showFonds, setShowFonds,
    showCables, setShowCables,
    showClimoWind, showClimoWave, showClimoCurrent, showClimoCyclones,
    zee.show, zee.setShow, zee.loading, zee.error, zee.data,
  ]);
}
