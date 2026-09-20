import { useCallback, useRef, useState } from "react";
import { coordsFromRoutePayload } from "../utils/berryLegs.js";

const API_URL = import.meta.env.VITE_API_URL ?? "";

/**
 * The drawn route itself (lot J: moved out of App.jsx, behaviour unchanged):
 * points and searoute segments, undo / redo, the GeoJSON handed to the plan.
 * App keeps the orchestration around it (entering / leaving the mode, camera,
 * cinema, plan reset) — this hook never touches the scene or the view.
 */
export function useRouteDrawing() {
  const [drawingMode, setDrawingMode] = useState(false);
  const [drawnPoints, setDrawnPoints] = useState([]);
  const [drawnSegments, setDrawnSegments] = useState([]);
  const [drawingLoading, setDrawingLoading] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  const pointsRef = useRef([]);
  const segmentsRef = useRef([]);
  const undonePointsRef = useRef([]);
  const undoneSegmentsRef = useRef([]);
  const fetchIdRef = useRef(0);

  const reset = useCallback(() => {
    setDrawnPoints([]);
    setDrawnSegments([]);
    setCanRedo(false);
    pointsRef.current = [];
    segmentsRef.current = [];
    undonePointsRef.current = [];
    undoneSegmentsRef.current = [];
    fetchIdRef.current = 0;
  }, []);

  const fetchSegment = useCallback(async (from, to) => {
    const myFetchId = ++fetchIdRef.current;
    setDrawingLoading(true);
    try {
      const params = new URLSearchParams({ start_lat: from.lat, start_lon: from.lon, end_lat: to.lat, end_lon: to.lon });
      const res = await fetch(`${API_URL}/route?${params}`);
      const data = await res.json();
      let coords = coordsFromRoutePayload(data);
      let failed = false;
      if (!coords.length) {
        coords = [[from.lon, from.lat], [to.lon, to.lat]];
        failed = true;
      }
      if (fetchIdRef.current === myFetchId) {
        const updated = [...segmentsRef.current, { coords, failed }];
        segmentsRef.current = updated;
        setDrawnSegments([...updated]);
      }
    } catch {
      if (fetchIdRef.current === myFetchId) {
        const updated = [...segmentsRef.current, { coords: [[from.lon, from.lat], [to.lon, to.lat]], failed: true }];
        segmentsRef.current = updated;
        setDrawnSegments([...updated]);
      }
    } finally {
      if (fetchIdRef.current === myFetchId) setDrawingLoading(false);
    }
  }, []);

  const addPoint = useCallback((lat, lon) => {
    const newPoint = { lat, lon };
    const updated = [...pointsRef.current, newPoint];
    pointsRef.current = updated;
    undonePointsRef.current = [];
    undoneSegmentsRef.current = [];
    setCanRedo(false);
    setDrawnPoints([...updated]);
    if (updated.length >= 2) fetchSegment(updated[updated.length - 2], newPoint);
  }, [fetchSegment]);

  const undo = useCallback(() => {
    if (!pointsRef.current.length) return;
    fetchIdRef.current += 1;
    undonePointsRef.current = [...undonePointsRef.current, pointsRef.current.at(-1)];
    pointsRef.current = pointsRef.current.slice(0, -1);
    if (segmentsRef.current.length) {
      undoneSegmentsRef.current = [...undoneSegmentsRef.current, segmentsRef.current.at(-1)];
      segmentsRef.current = segmentsRef.current.slice(0, -1);
    }
    setDrawnPoints([...pointsRef.current]);
    setDrawnSegments([...segmentsRef.current]);
    setDrawingLoading(false);
    setCanRedo(true);
  }, []);

  const redo = useCallback(() => {
    if (!undonePointsRef.current.length) return;
    const restoredPoint = undonePointsRef.current.at(-1);
    undonePointsRef.current = undonePointsRef.current.slice(0, -1);
    pointsRef.current = [...pointsRef.current, restoredPoint];
    if (undoneSegmentsRef.current.length) {
      segmentsRef.current = [...segmentsRef.current, undoneSegmentsRef.current.at(-1)];
      undoneSegmentsRef.current = undoneSegmentsRef.current.slice(0, -1);
    }
    setDrawnPoints([...pointsRef.current]);
    setDrawnSegments([...segmentsRef.current]);
    setCanRedo(undonePointsRef.current.length > 0);
  }, []);

  /** Rename / flag a placed point (satellite popup « point info »). */
  const updatePoint = useCallback((index, patch) => {
    const updated = [...pointsRef.current];
    if (!updated[index]) return;
    updated[index] = { ...updated[index], ...patch };
    pointsRef.current = updated;
    setDrawnPoints([...updated]);
  }, []);

  /** The drawn route as the GeoJSON the plan endpoint expects. */
  const toGeoJson = useCallback(() => {
    const lineFeatures = segmentsRef.current.filter((s) => s.coords?.length > 0).map((s) => ({
      type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: s.coords },
    }));
    const pointFeatures = pointsRef.current.map((p, i) => ({
      type: "Feature",
      properties: { name: p.name || `Point ${i + 1}`, flags: p.flags || [], naviguide_type: "drawn_waypoint" },
      geometry: { type: "Point", coordinates: [p.lon, p.lat] },
    }));
    return { type: "FeatureCollection", features: [...lineFeatures, ...pointFeatures] };
  }, []);

  return {
    drawingMode, setDrawingMode,
    drawnPoints, drawnSegments, drawingLoading, canRedo,
    reset, addPoint, undo, redo, updatePoint, toGeoJson,
  };
}
