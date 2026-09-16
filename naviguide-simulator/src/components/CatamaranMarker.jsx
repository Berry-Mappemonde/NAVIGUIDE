import { useEffect, useRef } from "react";
import L from "leaflet";
import catamaranImg from "../assets/img/catamaran.jpg";
import { catamaranTransform } from "../engine/catamaranIcon.js";
import { wrapLon } from "../utils/geo.js";
import { worldCopyLngs } from "../utils/gribSymbols.js";

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
    const icon = L.divIcon({
      className,
      html: buildIconHtml(bearing),
      iconSize: [56, 56],
      iconAnchor: [28, 28],
    });
    const lngs = worldCopyLngs(lon);
    if (markersRef.current.length !== lngs.length) {
      clear();
      markersRef.current = lngs.map((lng) => {
        const m = L.marker([lat, lng], {
          icon,
          draggable: Boolean(draggable),
          pane: "boat",
          interactive: Boolean(draggable),
        }).addTo(map);
        if (draggable) {
          m.on("dragstart", () => onDragStart?.());
          m.on("drag", (e) => {
            const ll = e.target.getLatLng();
            onDrag?.({ lat: ll.lat, lon: wrapLon(ll.lng) });
          });
        }
        return m;
      });
    } else {
      markersRef.current.forEach((m, i) => {
        m.setLatLng([lat, lngs[i]]);
        m.setIcon(icon);
      });
    }
    return undefined;
  }, [mapRef, mapReady, visible, lat, lon, bearing, onDrag, onDragStart, draggable, className]);

  useEffect(() => () => {
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];
  }, []);
}
