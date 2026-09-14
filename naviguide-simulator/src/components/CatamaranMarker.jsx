import { useEffect, useRef } from "react";
import L from "leaflet";
import catamaranImg from "../assets/img/catamaran.jpg";
import { catamaranTransform } from "../engine/catamaranIcon.js";

function buildIconHtml(bearing, png) {
  const src = png || catamaranImg;
  return `<img src="${src}" alt="catamaran" style="width:56px;height:56px;object-fit:contain;transform:${catamaranTransform(bearing)};transition:transform 0.35s ease;" />`;
}

export function useCatamaranMarker(mapRef, {
  visible,
  lat,
  lon,
  bearing,
  onDrag,
  onDragStart,
  mapReady,
  draggable = true,
  className = "catamaran-divicon",
}) {
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
      className,
      html: buildIconHtml(bearing),
      iconSize: [56, 56],
      iconAnchor: [28, 28],
    });
    if (!markerRef.current) {
      const m = L.marker([lat, lon], {
        icon,
        draggable: Boolean(draggable),
        pane: "boat",
        interactive: Boolean(draggable),
      }).addTo(map);
      if (draggable) {
        m.on("dragstart", () => onDragStart?.());
        m.on("drag", (e) => {
          const ll = e.target.getLatLng();
          onDrag?.({ lat: ll.lat, lon: ll.lng });
        });
      }
      markerRef.current = m;
    } else {
      markerRef.current.setLatLng([lat, lon]);
      markerRef.current.setIcon(icon);
    }
    return undefined;
  }, [mapRef, mapReady, visible, lat, lon, bearing, onDrag, onDragStart, draggable, className]);

  useEffect(() => () => {
    markerRef.current?.remove();
    markerRef.current = null;
  }, []);
}
