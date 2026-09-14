import { useEffect, useRef } from "react";
import L from "leaflet";

function planeHtml(bearing) {
  const deg = Number(bearing) || 0;
  return `<div class="plane-icon" style="width:44px;height:44px;transform:rotate(${deg}deg);filter:drop-shadow(0 0 6px rgba(103,232,249,0.85));">
    <svg viewBox="0 0 24 24" width="44" height="44" aria-label="avion">
      <path fill="#e0f2fe" stroke="#0891b2" stroke-width="0.6"
        d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5L21 16z"/>
    </svg>
  </div>`;
}

export function usePlaneMarker(mapRef, { visible, lat, lon, bearing, mapReady }) {
  const markerRef = useRef(null);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !visible || lat == null || lon == null) {
      if (markerRef.current) {
        markerRef.current.remove();
        markerRef.current = null;
      }
      return undefined;
    }
    const icon = L.divIcon({
      className: "plane-divicon",
      html: planeHtml(bearing),
      iconSize: [44, 44],
      iconAnchor: [22, 22],
    });
    if (!markerRef.current) {
      markerRef.current = L.marker([lat, lon], {
        icon,
        draggable: false,
        interactive: false,
        pane: "boat",
      }).addTo(map);
    } else {
      markerRef.current.setLatLng([lat, lon]);
      markerRef.current.setIcon(icon);
    }
    return undefined;
  }, [mapRef, mapReady, visible, lat, lon, bearing]);

  useEffect(() => () => {
    markerRef.current?.remove();
    markerRef.current = null;
  }, []);
}
