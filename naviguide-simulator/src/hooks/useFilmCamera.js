import { useEffect, useRef } from "react";

function zoomForRemaining(nm) {
  if (nm > 1800) return 3;
  if (nm > 500) return 4;
  if (nm > 120) return 5;
  if (nm > 30) return 6;
  return 7;
}

/** Suit le bateau sans coller zoom 8 à chaque pas. */
export function useFilmCamera({ mapRef, mapReady, enabled, lat, lon, remainingNm, playing, jumpToken }) {
  const lastFollow = useRef(0);
  const lastJump = useRef(0);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !enabled || lat == null || lon == null) return;
    if (jumpToken && jumpToken !== lastJump.current) {
      lastJump.current = jumpToken;
      const z = zoomForRemaining(remainingNm);
      map.flyTo([lat, lon], z, { duration: 1.05 });
      lastFollow.current = Date.now();
    }
  }, [mapRef, mapReady, enabled, lat, lon, remainingNm, jumpToken]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !enabled || !playing || lat == null) return;
    const now = Date.now();
    if (now - lastFollow.current < 700) return;
    lastFollow.current = now;
    const want = zoomForRemaining(remainingNm);
    const cur = map.getZoom();
    const zoom = Math.abs(cur - want) >= 1.25 ? want : cur;
    map.setView([lat, lon], zoom, { animate: true, duration: 0.55 });
  }, [mapRef, mapReady, enabled, playing, lat, lon, remainingNm]);
}
