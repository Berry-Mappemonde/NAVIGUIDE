import { useEffect, useRef } from "react";
import L from "leaflet";
import catamaranImg from "../assets/img/catamaran.jpg";

function buildIconHtml(bearing, southern, png) {
  const bearingRad = (bearing * Math.PI) / 180;
  const goingEast = Math.sin(bearingRad) >= 0;
  const tilt = goingEast ? bearing - 90 : bearing - 270;
  const parts = [];
  if (!goingEast) parts.push("scaleX(-1)");
  parts.push(`rotate(${tilt}deg)`);
  if (southern) parts.push("scaleY(-1)");
  const src = png || catamaranImg;
  return `<img src="${src}" alt="catamaran" style="width:56px;height:56px;object-fit:contain;transform:${parts.join(" ")};transition:transform 0.35s ease;" />`;
}

export function useCatamaranMarker(mapRef, { visible, lat, lon, bearing, onDrag, mapReady }) {
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
      className: "catamaran-divicon",
      html: buildIconHtml(bearing, lat < 0),
      iconSize: [56, 56],
      iconAnchor: [28, 28],
    });
    if (!markerRef.current) {
      const m = L.marker([lat, lon], { icon, draggable: true, pane: "boat" }).addTo(map);
      m.on("drag", (e) => {
        const ll = e.target.getLatLng();
        onDrag?.({ lat: ll.lat, lon: ll.lng });
      });
      markerRef.current = m;
    } else {
      markerRef.current.setLatLng([lat, lon]);
      markerRef.current.setIcon(icon);
    }
    return undefined;
  }, [mapRef, mapReady, visible, lat, lon, bearing, onDrag]);

  useEffect(() => () => {
    markerRef.current?.remove();
    markerRef.current = null;
  }, []);
}
