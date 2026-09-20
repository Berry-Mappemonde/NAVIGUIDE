import {
  FILM_FLY_SECONDS,
  FILM_VIEW_HZ,
  FILM_ZOOM_MAX,
  FILM_ZOOM_MIN,
} from "../engine/replay.js";

const FILM_VIEW_MS = 1000 / FILM_VIEW_HZ;

/** Zoom fixe d'un chapitre : la jambe tient dans ~70 % de la fenêtre, borné [3 ; 7]. */
export function filmChapterZoom(map, leg, { min = FILM_ZOOM_MIN, max = FILM_ZOOM_MAX } = {}) {
  const aLat = Number(leg?.fromLat);
  const aLon = Number(leg?.fromLon);
  const bLat = Number(leg?.toLat);
  const bLon = Number(leg?.toLon);
  if (!map || ![aLat, aLon, bLat, bLon].every(Number.isFinite)) {
    return Math.max(min, Math.min(max, 5));
  }
  let z = 5;
  try {
    const bounds = [[aLat, aLon], [bLat, bLon]];
    const size = typeof map.getSize === "function" ? map.getSize() : null;
    const pad = size && Number.isFinite(size.x)
      ? [size.y * 0.15, size.x * 0.15]
      : [72, 96];
    if (typeof map.getBoundsZoom === "function") {
      z = map.getBoundsZoom(bounds, false, pad);
    }
  } catch { /* fake map in tests */ }
  if (!Number.isFinite(z)) z = 5;
  return Math.max(min, Math.min(max, z));
}

/** Centre carte pour placer le bateau au tiers avant (2/3 d'écran devant le cap). */
export function filmViewCenter(lat, lon, headingDeg, map) {
  const heading = Number(headingDeg);
  const h = Number.isFinite(heading) ? heading : 0;
  const rad = (h * Math.PI) / 180;
  if (!map || typeof map.getBounds !== "function") return [lat, lon];
  try {
    const b = map.getBounds();
    const latSpan = b.getNorth() - b.getSouth();
    const lngSpan = b.getEast() - b.getWest();
    if (!Number.isFinite(latSpan) || !Number.isFinite(lngSpan)) return [lat, lon];
    return [
      lat + Math.cos(rad) * latSpan / 6,
      lon + Math.sin(rad) * lngSpan / 6,
    ];
  } catch {
    return [lat, lon];
  }
}

/**
 * Caméra du film : `flyTo` uniquement au changement de chapitre ;
 * sinon `setView` à 30 Hz, zoom inchangé.
 */
export function applyFilmCamera(map, {
  chapterIdx,
  lastChapterIdx,
  lat,
  lon,
  heading,
  zoom,
  now = Date.now(),
  lastSetViewAt = 0,
  flyingUntil = 0,
} = {}) {
  const center = filmViewCenter(lat, lon, heading, map);
  if (chapterIdx !== lastChapterIdx) {
    map.flyTo(center, zoom, { duration: FILM_FLY_SECONDS });
    return {
      lastChapterIdx: chapterIdx,
      lastSetViewAt: now,
      flyingUntil: now + FILM_FLY_SECONDS * 1000,
      action: "flyTo",
    };
  }
  if (flyingUntil && now < flyingUntil) {
    return { lastChapterIdx, lastSetViewAt, flyingUntil, action: "fly-wait" };
  }
  if (now - lastSetViewAt < FILM_VIEW_MS) {
    return { lastChapterIdx, lastSetViewAt, flyingUntil, action: "skip" };
  }
  map.setView(center, zoom, { animate: false });
  return { lastChapterIdx: chapterIdx, lastSetViewAt: now, flyingUntil: 0, action: "setView" };
}
