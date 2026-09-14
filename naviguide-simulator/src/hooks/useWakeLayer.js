import { useEffect, useRef } from "react";
import L from "leaflet";
import { wakeParts } from "../engine/filmWake.js";

const WAKE_STYLE = {
  color: "#67e8f9",
  weight: 4,
  opacity: 0.88,
  pane: "route",
  interactive: false,
};

/**
 * Already-sailed track, lighter than the route. Leaflet only — no deck.gl.
 */
export function useWakeLayer(mapRef, { flat, sailNm, enabled, mapReady }) {
  const groupRef = useRef(null);
  const linesRef = useRef([]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !enabled) {
      groupRef.current?.remove();
      groupRef.current = null;
      linesRef.current = [];
      return undefined;
    }
    const group = L.layerGroup().addTo(map);
    groupRef.current = group;
    return () => {
      group.remove();
      groupRef.current = null;
      linesRef.current = [];
    };
  }, [mapRef, mapReady, enabled]);

  useEffect(() => {
    const group = groupRef.current;
    if (!group || !enabled) return;
    const parts = wakeParts(flat, sailNm);
    while (linesRef.current.length < parts.length) {
      const line = L.polyline([], WAKE_STYLE).addTo(group);
      linesRef.current.push(line);
    }
    while (linesRef.current.length > parts.length) {
      const line = linesRef.current.pop();
      group.removeLayer(line);
    }
    parts.forEach((coords, i) => {
      linesRef.current[i].setLatLngs(coords.map(([lon, lat]) => [lat, lon]));
    });
  }, [flat, sailNm, enabled]);
}
