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
