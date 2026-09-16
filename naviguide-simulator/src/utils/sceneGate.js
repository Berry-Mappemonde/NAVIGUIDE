import { haversineNm } from "./geo.js";

/** Porte d’affichage : rien n’est peint tant que route + horloge + caméra ne sont pas prêts. */

export function playheadAligned({
  isSuivre,
  previewing,
  playbackNm,
  liveFilmNm,
  slack = 2,
} = {}) {
  if (!isSuivre || previewing) return true;
  if (liveFilmNm == null || !Number.isFinite(Number(liveFilmNm))) return false;
  return Math.abs((Number(playbackNm) || 0) - Number(liveFilmNm)) <= slack;
}

export function isSceneReady({
  routeReady,
  hasRoute,
  cameraPlaced,
  playheadReady,
  isSuivre,
  hasLive,
  previewing,
} = {}) {
  if (!routeReady || !hasRoute || !cameraPlaced) return false;
  if (isSuivre && !hasLive && !previewing) return false;
  if (isSuivre && !playheadReady) return false;
  return true;
}

/** Une navigation manuelle pendant le chargement garde la vue choisie par la personne. */
export function shouldPlaceInitialCamera({ userNavigated = false } = {}) {
  return !userNavigated;
}

/** Premier snap, ou téléport (horloge serveur wrappée → horloge client dépliée). */
export function shouldResnapCamera(prev, next, nm = 80) {
  if (next?.lat == null || next?.lon == null) return false;
  if (!prev || prev.lat == null || prev.lon == null) return true;
  return haversineNm(prev.lat, prev.lon, next.lat, next.lon) >= nm;
}
