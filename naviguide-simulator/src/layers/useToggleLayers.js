import { useCallback, useEffect, useRef, useState } from "react";
import L from "leaflet";
import { ampStyle } from "./styles.js";
import { circleOpts, makePointGroup } from "./points.js";
import { EMODNET_WMS } from "../constants/layers.js";

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

function addPointLayer(map, fc, color, kind, onFeature) {
  const group = makePointGroup();
  const zoom = map.getZoom();
  const renderer = group._biRenderer;
  (fc?.features || []).forEach((f) => {
    if (f.geometry?.type !== "Point") return;
    const [lon, lat] = f.geometry.coordinates;
    const m = L.circleMarker([lat, lon], circleOpts(color, { zoom, renderer }));
    m.on("click", (e) => {
      L.DomEvent.stopPropagation(e);
      onFeature?.({ lon, lat, kind, props: f.properties || {} });
    });
    group.addLayer(m);
  });
  group.addTo(map);
  return group;
}

function ensureSimWmsPanes(map) {
  EMODNET_WMS.forEach((spec) => {
    if (!map.getPane(spec.pane)) map.createPane(spec.pane);
    const pane = map.getPane(spec.pane);
    pane.style.zIndex = String(spec.zIndex);
    pane.style.pointerEvents = "none";
  });
}

export function useToggleLayers(mapRef, onFeature, mapReady = 0, gateRef) {
  const zee = useFetchLayer(null);
  const [showZee, setShowZee] = useState(true);
  const [loadingZee] = useState(false);
  const [errorZee, setErrorZee] = useState(null);

  const ports = useFetchLayer("/proxy/ports");
  const projects = useFetchLayer(`${BI_BASE}/export/geojson`);
  const marinas = useFetchLayer(`${BI_BASE}/export/marinas.geojson`);
  const capitaineries = useFetchLayer(`${BI_BASE}/export/capitaineries.geojson`);
  const poe = useFetchLayer(`${BI_BASE}/export/poe.geojson`);
  const science = useFetchLayer(`${BI_BASE}/export/science.geojson`);

  const [showBalisage, setShowBalisageRaw] = useState(false);
  const [showWmsBathy, setShowWmsBathyRaw] = useState(false);
  const [showWmsSubstrate, setShowWmsSubstrateRaw] = useState(false);
  const [showWmsCables, setShowWmsCablesRaw] = useState(false);

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
  const setShowWmsBathy = gatedSet(setShowWmsBathyRaw, "wmsBathy");
  const setShowWmsSubstrate = gatedSet(setShowWmsSubstrateRaw, "wmsSubstrate");
  const setShowWmsCables = gatedSet(setShowWmsCablesRaw, "wmsCables");
  const [showAmp, setShowAmp] = useState(false);
  const [loadingAmp, setLoadingAmp] = useState(false);
  const [errorAmp, setErrorAmp] = useState(null);
  const [ampData, setAmpData] = useState(EMPTY);
  const [showClimatology, setShowClimatology] = useState(false);

  const layersRef = useRef({});

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
    });
    tiles.on("tileerror", () => {
      if (!layersRef.current.balisageFallback) {
        layersRef.current.balisageFallback = L.tileLayer("/proxy/seamark/{z}/{x}/{y}.png", {
          pane: "balisage",
          opacity: 0.85,
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
    ensureSimWmsPanes(map);
    const specs = [
      [showWmsBathy, EMODNET_WMS[0]],
      [showWmsSubstrate, EMODNET_WMS[1]],
      [showWmsCables, EMODNET_WMS[2]],
    ];
    const added = [];
    specs.forEach(([on, spec]) => {
      if (!on) return;
      const lyr = L.tileLayer.wms(spec.url, {
        layers: spec.layers,
        format: "image/png",
        transparent: true,
        version: "1.1.1",
        opacity: spec.opacity,
        pane: spec.pane,
        attribution: spec.attribution,
      });
      lyr.addTo(map);
      added.push(lyr);
    });
    return () => {
      added.forEach((lyr) => {
        if (map.hasLayer(lyr)) map.removeLayer(lyr);
      });
    };
  }, [mapRef, mapReady, showWmsBathy, showWmsSubstrate, showWmsCables]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !ports.show || !ports.data) return undefined;
    const g = addPointLayer(map, ports.data, "#f59e0b", "port", onFeature);
    return () => map.removeLayer(g);
  }, [mapRef, mapReady, ports.show, ports.data, onFeature]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !projects.show || !projects.data) return undefined;
    const g = addPointLayer(map, projects.data, "#06b6d4", "project", onFeature);
    return () => map.removeLayer(g);
  }, [mapRef, mapReady, projects.show, projects.data, onFeature]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !marinas.show || !marinas.data) return undefined;
    const g = addPointLayer(map, marinas.data, "#ef4444", "marina", onFeature);
    return () => map.removeLayer(g);
  }, [mapRef, mapReady, marinas.show, marinas.data, onFeature]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !capitaineries.show || !capitaineries.data) return undefined;
    const g = addPointLayer(map, capitaineries.data, "#7dd3fc", "capitainerie", onFeature);
    return () => map.removeLayer(g);
  }, [mapRef, mapReady, capitaineries.show, capitaineries.data, onFeature]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !poe.show || !poe.data) return undefined;
    const g = addPointLayer(map, poe.data, "#d97706", "poe", onFeature);
    return () => map.removeLayer(g);
  }, [mapRef, mapReady, poe.show, poe.data, onFeature]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !science.show || !science.data) return undefined;
    const g = addPointLayer(map, science.data, "#a78bfa", "science", onFeature);
    return () => map.removeLayer(g);
  }, [mapRef, mapReady, science.show, science.data, onFeature]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !showAmp) return undefined;
    let cancelled = false;
    let debounce = null;
    const load = () => {
      const b = map.getBounds();
      const bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(",");
      setLoadingAmp(true);
      setErrorAmp(null);
      fetch(`${BI_BASE}/amp?bbox=${bbox}`)
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then((json) => {
          if (!cancelled) setAmpData(json);
        })
        .catch((err) => {
          if (!cancelled) setErrorAmp(String(err.message || err));
        })
        .finally(() => {
          if (!cancelled) setLoadingAmp(false);
        });
    };
    const onMove = () => {
      clearTimeout(debounce);
      debounce = setTimeout(load, 420);
    };
    debounce = setTimeout(load, 420);
    map.on("moveend", onMove);
    return () => {
      cancelled = true;
      clearTimeout(debounce);
      map.off("moveend", onMove);
    };
  }, [mapRef, mapReady, showAmp]);

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

  return {
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
    showWmsBathy,
    setShowWmsBathy,
    loadingWmsBathy: false,
    errorWmsBathy: null,
    showWmsSubstrate,
    setShowWmsSubstrate,
    loadingWmsSubstrate: false,
    errorWmsSubstrate: null,
    showWmsCables,
    setShowWmsCables,
    loadingWmsCables: false,
    errorWmsCables: null,
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
    showScience: science.show,
    setShowScience: science.setShow,
    loadingScience: science.loading,
    errorScience: science.error,
    showClimatology,
    setShowClimatology,
    loadingClimatology: false,
    errorClimatology: null,
    zee,
  };
}
