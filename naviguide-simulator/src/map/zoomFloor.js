/**
 * Suivre (27 sept.) : plancher de dézoom tel que le monde tienne AU PLUS une fois dans l'écran —
 * largeur du monde 256·2^z px ≥ plus grand côté de la carte. La navigation gauche/droite reste
 * libre (±540°, une répétition de chaque côté) ; Tracer / accueil gardent le plancher d'origine.
 */
export const WORLD_TILE_PX = 256;

export function followMinZoom(size, snap = 0.25, floor = 0) {
  const w = Number(size?.x) || 0;
  const h = Number(size?.y) || 0;
  const side = Math.max(w, h);
  const base = Number.isFinite(Number(floor)) ? Number(floor) : 0;
  if (!(side > 0)) return base;
  const exact = Math.log2(side / WORLD_TILE_PX);
  const step = Number(snap) > 0 ? Number(snap) : 0.25;
  return Math.max(base, Math.ceil(exact / step - 1e-9) * step);
}

/** Largeur du monde en pixels au zoom donné (Web Mercator, tuiles 256 px). */
export function worldWidthPx(zoom) {
  return WORLD_TILE_PX * 2 ** Number(zoom || 0);
}
