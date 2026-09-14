/** Expedition cruise speed (knots): downwind BS, else 7 kt. */
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
 * True-wind angle (0–180): boat heading vs direction the wind comes from.
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
 * Fast: Atlantic (La Rochelle → Fort-de-France) in 20 s.
 * Real: boat knots (1 s on screen = 1 s at sea).
 */
export function nmPerSecond(profile, { boatKnots, atlanticNm }) {
  const knots = Number(boatKnots) > 0 ? Number(boatKnots) : FALLBACK_EXPEDITION_KNOTS;
  if (profile === "real") return knots / 3600;
  const atl = Number(atlanticNm) > 100 ? Number(atlanticNm) : 3500;
  if (profile === "fast") return atl / 20;
  if (profile === "read") return atl / 240;
  return atl / 70;
}

/** Screen duration of an air hop, so the plane stays visible on every profile. */
export function airHopSeconds(profile) {
  if (profile === "real") return 8;
  if (profile === "read") return 4.5;
  if (profile === "fast") return 3.2;
  return 3.6;
}
