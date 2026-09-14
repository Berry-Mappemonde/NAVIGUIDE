import { useEffect, useRef } from "react";
import { haversineNm, unwrapLon } from "../utils/geo.js";

const TELEPORT_NM = 80;

function zoomForRemaining(nm) {
  if (nm > 1800) return 3;
  if (nm > 500) return 4;
  if (nm > 120) return 5;
  if (nm > 30) return 6;
  return 7;
}

/** Suit le bateau sans traverser le globe à l’antiméridien ni à un saut aérien. */
export function useFilmCamera({ mapRef, mapReady, enabled, lat, lon, remainingNm, playing, jumpToken }) {
  const lastFollow = useRef(0);
  const lastJump = useRef(0);
  const lastPos = useRef(null);
  const followLon = useRef(null);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !enabled || lat == null || lon == null) return;

    const lonCam = unwrapLon(followLon.current, lon);
    followLon.current = lonCam;
    const prev = lastPos.current;
    const movedNm = prev ? haversineNm(prev.lat, prev.lon, lat, lon) : 0;
    lastPos.current = { lat, lon };
    const z = zoomForRemaining(remainingNm);
    const tokenJump = jumpToken && jumpToken !== lastJump.current;
    if (tokenJump) lastJump.current = jumpToken;
    const teleport = tokenJump || movedNm >= TELEPORT_NM;

    if (teleport) {
      map.flyTo([lat, lonCam], z, { duration: movedNm >= TELEPORT_NM ? 0.55 : 1.05 });
      lastFollow.current = Date.now();
      return;
    }

    if (!playing) return;
    const now = Date.now();
    if (now - lastFollow.current < 700) return;
    lastFollow.current = now;
    const cur = map.getZoom();
    const zoom = Math.abs(cur - z) >= 1.25 ? z : cur;
    map.setView([lat, lonCam], zoom, { animate: true, duration: 0.55 });
  }, [mapRef, mapReady, enabled, lat, lon, remainingNm, playing, jumpToken]);
}
