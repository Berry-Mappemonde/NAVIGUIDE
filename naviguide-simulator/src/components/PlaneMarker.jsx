import { useEffect, useRef } from "react";
import L from "leaflet";

function planeHtml(bearing) {
  const deg = Number(bearing) || 0;
  return `<div class="plane-icon" style="width:64px;height:64px;transform:rotate(${deg}deg);filter:drop-shadow(0 0 8px rgba(250,250,255,0.95));">
    <svg viewBox="0 0 24 24" width="64" height="64" aria-label="avion">
      <path fill="#f8fafc" stroke="#22d3ee" stroke-width="0.8"
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
      iconSize: [64, 64],
      iconAnchor: [32, 32],
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
