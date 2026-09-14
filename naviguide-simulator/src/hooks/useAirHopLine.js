import { useEffect, useRef } from "react";
import L from "leaflet";
import { unwrapLon } from "../utils/geo.js";

/** Trait pointillé du hop aérien, seulement pendant que l’avion est en vol. */
export function useAirHopLine(mapRef, { mapReady, visible, from, to }) {
  const lineRef = useRef(null);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !visible || !from || !to) {
      lineRef.current?.remove();
      lineRef.current = null;
      return undefined;
    }
    const lonB = unwrapLon(from.lon, to.lon);
    const latlngs = [
      [from.lat, from.lon],
      [to.lat, lonB],
    ];
    if (!lineRef.current) {
      lineRef.current = L.polyline(latlngs, {
        color: "#67e8f9",
        weight: 2,
        dashArray: "7 9",
        opacity: 0.8,
        pane: "route",
        interactive: false,
      }).addTo(map);
    } else {
      lineRef.current.setLatLngs(latlngs);
    }
    return undefined;
  }, [mapRef, mapReady, visible, from?.lat, from?.lon, to?.lat, to?.lon]);

  useEffect(() => () => {
    lineRef.current?.remove();
    lineRef.current = null;
  }, []);
}
