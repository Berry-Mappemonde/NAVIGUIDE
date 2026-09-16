import { useState, useEffect, useCallback, useRef } from "react";
import { computeMarkerOffsets, projectRouteSegments } from "../utils/markerOffsets";

const DEBOUNCE_MS = 120;
export const CAMERA_IDLE_MS = 950;

export function markerOffsetDelay(cameraFollowing) {
  return cameraFollowing ? CAMERA_IDLE_MS : DEBOUNCE_MS;
}

export function useMarkerOffsets(points, mapRef, routeCoords = [], { cameraFollowing = false } = {}) {
  const [offsets, setOffsets] = useState(() => points.map(() => [0, 0]));
  const timerRef = useRef(null);

  const compute = useCallback(() => {
    const map = mapRef.current;
    if (!map || !points.length) return;
    const project = (lon, lat) => {
      const pt = map.latLngToLayerPoint([lat, lon]);
      return { x: pt.x, y: pt.y };
    };
    const routeSegs = projectRouteSegments(routeCoords, project);
    setOffsets(computeMarkerOffsets(points, project, routeSegs));
  }, [points, mapRef, routeCoords]);

  useEffect(() => {
    if (!points.length) return undefined;
    const schedule = (delay) => {
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(compute, delay);
    };
    const afterCameraStop = () => schedule(markerOffsetDelay(cameraFollowing));
    const afterZoom = () => schedule(DEBOUNCE_MS);
    const attach = () => {
      const map = mapRef.current;
      if (!map) return false;
      map.on("zoomend", afterZoom);
      map.on("moveend", afterCameraStop);
      compute();
      return true;
    };
    if (!attach()) {
      const poll = setInterval(() => {
        if (attach()) clearInterval(poll);
      }, 200);
      return () => {
        clearInterval(poll);
        clearTimeout(timerRef.current);
      };
    }
    return () => {
      clearTimeout(timerRef.current);
      const map = mapRef.current;
      if (map) {
        map.off("zoomend", afterZoom);
        map.off("moveend", afterCameraStop);
      }
    };
  }, [compute, mapRef, points, cameraFollowing]);

  return offsets;
}
