import { useEffect, useRef } from "react";
import L from "leaflet";
import { markerWorldLngs } from "../utils/waypointFlags.js";

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
  const markersRef = useRef([]);

  useEffect(() => {
    const map = mapRef.current;
    const clear = () => {
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
    };
    if (!map || !mapReady || !visible || lat == null || lon == null) {
      clear();
      return undefined;
    }

    const makeIcon = () => L.divIcon({
      className: "plane-divicon",
      html: planeHtml(bearing),
      iconSize: [64, 64],
      iconAnchor: [32, 32],
    });

    const sync = () => {
      const cam = map.getCenter()?.lng;
      const lngs = markerWorldLngs(lon, cam);
      if (markersRef.current.length !== lngs.length) {
        clear();
        markersRef.current = lngs.map((lng) => L.marker([lat, lng], {
          icon: makeIcon(),
          draggable: false,
          interactive: false,
          pane: "boat",
        }).addTo(map));
      } else {
        markersRef.current.forEach((m, i) => {
          m.setLatLng([lat, lngs[i]]);
          m.setIcon(makeIcon());
        });
      }
    };

    sync();
    map.on("moveend", sync);
    return () => {
      map.off("moveend", sync);
    };
  }, [mapRef, mapReady, visible, lat, lon, bearing]);

  useEffect(() => () => {
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];
  }, []);
}
