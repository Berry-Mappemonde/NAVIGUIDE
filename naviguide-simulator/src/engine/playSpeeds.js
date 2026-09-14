/** Vitesse de croisière de l’expédition (nœuds) : BS portant, sinon 7 kt. */
export const FALLBACK_EXPEDITION_KNOTS = 7;

export function expeditionBoatKnots(polarData) {
  const vmg = polarData?.vmg_summary;
  if (!vmg || typeof vmg !== "object") return FALLBACK_EXPEDITION_KNOTS;
  const samples = [];
  for (const key of ["12", "16", "10", "8"]) {
    const dw = vmg[key]?.downwind;
    const bs = Number(dw?.speed ?? dw?.vmg);
    if (Number.isFinite(bs) && bs > 0) samples.push(bs);
  }
  if (!samples.length) return FALLBACK_EXPEDITION_KNOTS;
  return samples.reduce((a, b) => a + b, 0) / samples.length;
}

/**
 * Angle du vent vrai (0–180) : cap bateau vs direction d’où vient le vent.
 */
export function trueWindAngle(headingDeg, windFromDeg) {
  if (!Number.isFinite(headingDeg) || !Number.isFinite(windFromDeg)) return null;
  let d = Math.abs(headingDeg - windFromDeg) % 360;
  if (d > 180) d = 360 - d;
  return d;
}

export const PLAY_PROFILES = ["real", "read", "normal", "fast"];

/**
 * nm/s selon le profil.
 * Accéléré : Atlantique (La Rochelle → Fort-de-France) en 20 s.
 * Réelle : nœuds du bateau (1 s écran = 1 s en mer).
 */
export function nmPerSecond(profile, { boatKnots, atlanticNm }) {
  const knots = Number(boatKnots) > 0 ? Number(boatKnots) : FALLBACK_EXPEDITION_KNOTS;
  if (profile === "real") return knots / 3600;
  const atl = Number(atlanticNm) > 100 ? Number(atlanticNm) : 3500;
  if (profile === "fast") return atl / 20;
  if (profile === "read") return atl / 240;
  return atl / 70;
}

/** Durée écran d’un hop aérien, pour que l’avion reste visible à chaque profil. */
export function airHopSeconds(profile) {
  if (profile === "real") return 8;
  if (profile === "read") return 4.5;
  if (profile === "fast") return 3.2;
  return 3.6;
}
