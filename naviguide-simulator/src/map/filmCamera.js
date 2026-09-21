import {
  FILM_FLY_SECONDS,
  FILM_PAN_MAX_SCREEN,
  FILM_ZOOM_MAX,
  FILM_ZOOM_MIN,
} from "../engine/replay.js";
import { haversineNm } from "../utils/geo.js";

/** Jambe plus courte que ça : on plafonne pour montrer l'archipel d'un coup. */
export const FILM_ARCHIPELAGO_NM = 180;
export const FILM_ZOOM_ARCHIPELAGO_MAX = 5;

function toLatLngPair(v) {
  if (!v) return null;
  if (Array.isArray(v)) {
    const lat = Number(v[0]);
    const lon = Number(v[1]);
    return Number.isFinite(lat) && Number.isFinite(lon) ? [lat, lon] : null;
  }
  const lat = Number(v.lat);
  const lon = Number(v.lng ?? v.lon);
  return Number.isFinite(lat) && Number.isFinite(lon) ? [lat, lon] : null;
}

/** Borne un déplacement de caméra à 2 % de la largeur d'écran. */
export function clampFilmPan(from, to, map, { maxFrac = FILM_PAN_MAX_SCREEN } = {}) {
  const a = toLatLngPair(from);
  const b = toLatLngPair(to);
  if (!a || !b) return to;
  const size = typeof map?.getSize === "function" ? map.getSize() : { x: 1280, y: 800 };
  const maxPx = Math.max(1, (Number(size?.x) || 1280) * maxFrac);
  if (typeof map?.latLngToContainerPoint === "function" && typeof map?.containerPointToLatLng === "function") {
    const p0 = map.latLngToContainerPoint(a);
    const p1 = map.latLngToContainerPoint(b);
    const dx = (p1.x ?? 0) - (p0.x ?? 0);
    const dy = (p1.y ?? 0) - (p0.y ?? 0);
    const dist = Math.hypot(dx, dy);
    if (!(dist > maxPx)) return b;
    const s = maxPx / dist;
    const ll = map.containerPointToLatLng({ x: p0.x + dx * s, y: p0.y + dy * s });
    return [ll.lat, ll.lng ?? ll.lon];
  }
  if (typeof map?.getBounds === "function") {
    try {
      const bounds = map.getBounds();
      const widthDeg = Math.abs(bounds.getEast() - bounds.getWest()) || 1;
      const maxDeg = widthDeg * maxFrac;
      const dLat = b[0] - a[0];
      const dLon = b[1] - a[1];
      const dist = Math.hypot(dLat, dLon);
      if (!(dist > maxDeg)) return b;
      const s = maxDeg / dist;
      return [a[0] + dLat * s, a[1] + dLon * s];
    } catch { /* fake map */ }
  }
  return b;
}

/** Zoom fixe d'un chapitre : la jambe tient dans ~70 % de la fenêtre, borné [3 ; 7]. */
function finiteCoord(v) {
  return v != null && v !== "" && Number.isFinite(Number(v));
}

export function filmLegSpanNm(leg) {
  const aLat = Number(leg?.fromLat);
  const aLon = Number(leg?.fromLon);
  const bLat = Number(leg?.toLat);
  const bLon = Number(leg?.toLon);
  if (![aLat, aLon, bLat, bLon].every(Number.isFinite)) return null;
  return haversineNm(aLat, aLon, bLat, bLon);
}

export function filmChapterZoom(map, leg, { min = FILM_ZOOM_MIN, max = FILM_ZOOM_MAX } = {}) {
  const aLat = Number(leg?.fromLat);
  const aLon = Number(leg?.fromLon);
  const bLat = Number(leg?.toLat);
  const bLon = Number(leg?.toLon);
  if (!map || ![leg?.fromLat, leg?.fromLon, leg?.toLat, leg?.toLon].every(finiteCoord)) {
    return Math.max(min, Math.min(max, 5));
  }
  const spanNm = filmLegSpanNm(leg);
  const shortHop = Number.isFinite(spanNm) && spanNm > 0 && spanNm <= FILM_ARCHIPELAGO_NM;
  const cap = shortHop ? Math.min(max, FILM_ZOOM_ARCHIPELAGO_MAX) : max;
  let z = 5;
  try {
    let bounds = [[aLat, aLon], [bLat, bLon]];
    if (shortHop) {
      const padDeg = 2.5;
      const midLat = (aLat + bLat) / 2;
      const midLon = (aLon + bLon) / 2;
      bounds = [
        [midLat - padDeg, midLon - padDeg],
        [midLat + padDeg, midLon + padDeg],
      ];
    }
    const size = typeof map.getSize === "function" ? map.getSize() : null;
    const pad = size && Number.isFinite(size.x)
      ? [size.y * 0.15, size.x * 0.15]
      : [72, 96];
    if (typeof map.getBoundsZoom === "function") {
      z = map.getBoundsZoom(bounds, false, pad);
    }
  } catch { /* fake map in tests */ }
  if (!Number.isFinite(z)) z = 5;
  return Math.max(min, Math.min(cap, z));
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
 * Caméra du film : premier mouvement = bateau du chapitre 1 (`setView`) ;
 * un seul `flyTo` 1,2 s au changement de chapitre ; sinon `setView` chaque
 * frame, bateau au tiers avant, déplacement borné à 2 % de l'écran.
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
  lastCenter = null,
} = {}) {
  const desiredBoat = [lat, lon];
  const center = filmViewCenter(lat, lon, heading, map);
  if (lastChapterIdx == null) {
    map.setView(desiredBoat, zoom, { animate: false });
    return {
      lastChapterIdx: chapterIdx,
      lastSetViewAt: now,
      flyingUntil: 0,
      action: "setView",
      lastCenter: desiredBoat,
    };
  }
  if (chapterIdx !== lastChapterIdx) {
    map.flyTo(center, zoom, { duration: FILM_FLY_SECONDS });
    return {
      lastChapterIdx: chapterIdx,
      lastSetViewAt: now,
      flyingUntil: now + FILM_FLY_SECONDS * 1000,
      action: "flyTo",
      lastCenter: center,
    };
  }
  if (flyingUntil && now < flyingUntil) {
    return { lastChapterIdx, lastSetViewAt, flyingUntil, action: "fly-wait", lastCenter };
  }
  const from = lastCenter || (typeof map.getCenter === "function"
    ? [map.getCenter().lat, map.getCenter().lng]
    : center);
  const clamped = clampFilmPan(from, center, map);
  map.setView(clamped, zoom, { animate: false });
  return {
    lastChapterIdx: chapterIdx,
    lastSetViewAt: now,
    flyingUntil: 0,
    action: "setView",
    lastCenter: clamped,
  };
}
