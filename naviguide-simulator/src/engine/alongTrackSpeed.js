import { polarBoatSpeed } from "./polarSpeed.js";
import { twaDeg } from "./routeWindProfile.js";
import { boatSpeedFromWind, zoneWindAt } from "../utils/climatologyWind.js";

/**
 * Nœuds fond le long d’un cap, polaire brute × vent (fourni ou zone du mois).
 */
export function alongTrackSpeed({ lat, lon, bearing, month, polarRaw, wind } = {}) {
  const w = wind || zoneWindAt(lat, lon, month);
  const twa = twaDeg(bearing, w.dirFromDeg);
  const fromPolar = polarBoatSpeed(polarRaw, twa, w.speedKnots);
  const speedKnots = fromPolar != null ? fromPolar : boatSpeedFromWind(w.speedKnots);
  return {
    speedKnots,
    windKnots: Math.round(Number(w.speedKnots) * 10) / 10,
    twa: Math.round(twa * 10) / 10,
    dirFromDeg: w.dirFromDeg,
    kind: w.kind || "climatology",
    source: w.source || null,
    model: w.model || null,
    reason: w.reason || null,
  };
}
