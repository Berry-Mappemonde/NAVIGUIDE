/**
 * Nœuds fond le long du trait : polaire brute × vent de mois.
 * kind: climatology. Pas de GRIB, pas de POST /wind.
 */

import { trueWindAngle } from "./playSpeeds.js";
import { hasPolarRaw, polarBoatSpeed } from "./polarSpeed.js";
import { boatSpeedFromWind, zoneWindAt } from "../utils/climatologyWind.js";

function roundKt(k) {
  const n = Number(k);
  if (!Number.isFinite(n)) return null;
  return Math.round(n * 10) / 10;
}

/**
 * @param {{
 *   lat: number,
 *   lon: number,
 *   bearing: number,
 *   month: number,
 *   polarRaw?: object | null,
 * }} args
 * @returns {{
 *   speedKnots: number,
 *   windKnots: number,
 *   twa: number | null,
 *   dirFromDeg: number,
 *   kind: "climatology",
 *   source: string,
 *   month: number,
 * }}
 */
export function alongTrackSpeed({ lat, lon, bearing, month, polarRaw = null }) {
  const wind = zoneWindAt(lat, lon, month);
  const twa = trueWindAngle(bearing, wind.dirFromDeg);
  let speed = null;
  if (hasPolarRaw(polarRaw) && twa != null) {
    speed = polarBoatSpeed(polarRaw, twa, wind.speedKnots);
  }
  if (speed == null || !Number.isFinite(speed) || speed < 0) {
    speed = boatSpeedFromWind(wind.speedKnots);
  }
  return {
    speedKnots: roundKt(speed) ?? boatSpeedFromWind(wind.speedKnots),
    windKnots: roundKt(wind.speedKnots) ?? 0,
    twa: twa == null ? null : Math.round(twa * 10) / 10,
    dirFromDeg: wind.dirFromDeg,
    kind: "climatology",
    source: wind.source,
    month: Math.max(1, Math.min(12, Number(month) || 1)),
  };
}
