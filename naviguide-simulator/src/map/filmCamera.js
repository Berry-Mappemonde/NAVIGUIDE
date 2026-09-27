import {
  FILM_FLY_SECONDS,
  FILM_PAN_MAX_SCREEN,
  FILM_ZOOM_MAX,
  FILM_ZOOM_MIN,
} from "../engine/replay.js";
import { haversineNm, unwrapLon } from "../utils/geo.js";

/** Horloge UI React : assez pour la barre, trop rare pour faire sauter la caméra. */
export const FILM_UI_MS = 80;
/** La pose affichée est en retard d'un cran : on interpole entre deux échantillons. */
export const FILM_INTERP_DELAY_MS = 80;
/** Au-delà, une tuile manquante ralentit le pan (évite le damier gris). */
export const FILM_TILE_READY_MIN = 0.7;
export const FILM_TILE_SLOW = 0.35;

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

export function lerpHeading(a, b, t) {
  const x = Number(a);
  const y = Number(b);
  if (!Number.isFinite(x)) return Number.isFinite(y) ? y : 0;
  if (!Number.isFinite(y)) return x;
  let d = y - x;
  while (d > 180) d -= 360;
  while (d < -180) d += 360;
  return x + d * t;
}

export function lerpFilmSample(a, b, u) {
  const t = Math.max(0, Math.min(1, Number(u) || 0));
  if (!a) return b || null;
  if (!b) return a;
  const lon0 = Number(a.lon);
  const lon1 = unwrapLon(lon0, Number(b.lon));
  const filmA = Number(a.filmNm);
  const filmB = Number(b.filmNm);
  return {
    lat: Number(a.lat) + (Number(b.lat) - Number(a.lat)) * t,
    lon: lon0 + (lon1 - lon0) * t,
    heading: lerpHeading(a.heading, b.heading, t),
    chapterIdx: t < 1 ? a.chapterIdx : b.chapterIdx,
    filmNm: Number.isFinite(filmA) && Number.isFinite(filmB) ? filmA + (filmB - filmA) * t : (Number.isFinite(filmB) ? filmB : filmA),
    t: (Number(a.t) || 0) + ((Number(b.t) || 0) - (Number(a.t) || 0)) * t,
  };
}

/** Échantillons horodatés (horloge murale). On n'en garde que les derniers. */
export function pushFilmSample(samples, sample, { max = 8 } = {}) {
  const list = samples || [];
  if (!sample || !Number.isFinite(Number(sample.lat)) || !Number.isFinite(Number(sample.lon))) {
    return list;
  }
  const next = {
    t: Number(sample.t),
    lat: Number(sample.lat),
    lon: Number(sample.lon),
    heading: Number.isFinite(Number(sample.heading)) ? Number(sample.heading) : 0,
    chapterIdx: Number.isFinite(Number(sample.chapterIdx)) ? Number(sample.chapterIdx) : 0,
    filmNm: Number(sample.filmNm),
  };
  if (!Number.isFinite(next.t)) return list;
  const last = list[list.length - 1];
  if (last && last.t === next.t && last.lat === next.lat && last.lon === next.lon) return list;
  list.push(next);
  if (list.length > max) list.splice(0, list.length - max);
  return list;
}

/** Pose entre deux échantillons : le bateau glisse même si React n'a pas rendu. */
export function interpolateFilmSamples(samples, now) {
  if (!samples?.length) return null;
  const t = Number(now);
  if (!Number.isFinite(t)) return { ...samples[samples.length - 1] };
  if (samples.length === 1 || t <= samples[0].t) return { ...samples[0] };
  const last = samples[samples.length - 1];
  if (t >= last.t) return { ...last };
  let i = 0;
  while (i < samples.length - 1 && samples[i + 1].t < t) i += 1;
  const a = samples[i];
  const b = samples[i + 1];
  if (!b) return { ...a };
  const span = b.t - a.t;
  return lerpFilmSample(a, b, span > 0 ? (t - a.t) / span : 1);
}

export function lonLatToTile(lon, lat, z) {
  const zoom = Math.round(Number(z));
  const n = 2 ** zoom;
  const x = Math.floor(((Number(lon) + 180) / 360) * n);
  const latRad = (Number(lat) * Math.PI) / 180;
  const y = Math.floor((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2 * n);
  return { x, y, z: zoom };
}

/** Tuiles le long de la jambe au zoom du chapitre (plus les voisines). */
export function tilesAlongLeg(leg, zoom, { pad = 1, samples = 24 } = {}) {
  const aLat = Number(leg?.fromLat);
  const aLon = Number(leg?.fromLon);
  const bLat = Number(leg?.toLat);
  const bLon = Number(leg?.toLon);
  const z = Math.round(Number(zoom));
  if (![aLat, aLon, bLat, bLon, z].every(Number.isFinite) || z < 0) return [];
  const lon1 = unwrapLon(aLon, bLon);
  const out = new Map();
  const n = Math.max(2, Number(samples) || 24);
  for (let i = 0; i <= n; i++) {
    const u = i / n;
    const lat = aLat + (bLat - aLat) * u;
    const lon = aLon + (lon1 - aLon) * u;
    const tile = lonLatToTile(lon, lat, z);
    for (let dy = -pad; dy <= pad; dy++) {
      for (let dx = -pad; dx <= pad; dx++) {
        const x = tile.x + dx;
        const y = tile.y + dy;
        const key = `${z}/${x}/${y}`;
        if (!out.has(key)) out.set(key, { z, x, y });
      }
    }
  }
  return [...out.values()];
}

export function filmTileUrl(template, tile) {
  if (!template || !tile) return "";
  return String(template)
    .replace(/\{z\}/g, String(tile.z))
    .replace(/\{y\}/g, String(tile.y))
    .replace(/\{x\}/g, String(tile.x));
}

export function preloadFilmTiles(template, tiles, { ImageCtor = globalThis.Image } = {}) {
  if (!template || !ImageCtor) return [];
  const imgs = [];
  for (const tile of tiles || []) {
    const url = filmTileUrl(template, tile);
    if (!url) continue;
    const img = new ImageCtor();
    if ("decoding" in img) img.decoding = "async";
    img.src = url;
    imgs.push(img);
  }
  return imgs;
}

/** 1 si les tuiles visibles sont là ; 0 si le fond est encore un damier. */
export function filmTilesReady(map, layer) {
  if (!layer) return true;
  try {
    const hasIsLoading = typeof layer.isLoading === "function";
    const tiles = layer._tiles;
    if (!hasIsLoading && (tiles == null || typeof tiles !== "object")) return true;
    if (hasIsLoading && layer.isLoading()) return false;
    if (!tiles) return false;
    const vals = Object.values(tiles);
    if (!vals.length) return false;
    let loaded = 0;
    for (const t of vals) {
      if (t?.loaded || t?.el?.complete) loaded += 1;
    }
    return loaded / vals.length >= FILM_TILE_READY_MIN;
  } catch {
    return true;
  }
}

export function filmPanMaxFrac(tilesReady = true) {
  return FILM_PAN_MAX_SCREEN * (tilesReady ? 1 : FILM_TILE_SLOW);
}

/**
 * Caméra du film : premier mouvement = bateau du chapitre 1 (`setView`) ;
 * un seul `flyTo` 1,2 s au changement de chapitre ; sinon `setView` chaque
 * pas de la boucle carte, bateau au tiers avant, déplacement borné à 2 %
 * de l'écran (ralentit si les tuiles ne sont pas prêtes).
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
  maxFrac = FILM_PAN_MAX_SCREEN,
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
  const clamped = clampFilmPan(from, center, map, { maxFrac });
  map.setView(clamped, zoom, { animate: false });
  return {
    lastChapterIdx: chapterIdx,
    lastSetViewAt: now,
    flyingUntil: 0,
    action: "setView",
    lastCenter: clamped,
  };
}

/**
 * Un pas de la boucle impérative : interpole la pose, puis applique la caméra.
 * Cadence dégradée des échantillons → pas toujours ≤ 2 % d'écran (pas de saut).
 */
export function stepFilmCamera(map, {
  samples,
  now,
  lastChapterIdx,
  lastSetViewAt = 0,
  flyingUntil = 0,
  lastCenter = null,
  zoom,
  tilesReady = true,
  chapterIdx: chapterOverride,
} = {}) {
  const pose = interpolateFilmSamples(samples, Number(now) - FILM_INTERP_DELAY_MS);
  if (!pose || !Number.isFinite(pose.lat) || !Number.isFinite(pose.lon)) {
    return {
      lastChapterIdx,
      lastSetViewAt,
      flyingUntil,
      lastCenter,
      action: "idle",
      pose: null,
    };
  }
  const chapterIdx = Number.isFinite(Number(chapterOverride)) ? Number(chapterOverride) : pose.chapterIdx;
  const next = applyFilmCamera(map, {
    chapterIdx,
    lastChapterIdx,
    lat: pose.lat,
    lon: pose.lon,
    heading: pose.heading,
    zoom,
    now,
    lastSetViewAt,
    flyingUntil,
    lastCenter,
    maxFrac: filmPanMaxFrac(tilesReady),
  });
  return { ...next, pose };
}
