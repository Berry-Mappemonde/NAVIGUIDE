import { haversineNm } from "../utils/geo.js";

const ALONGSIDE_NM = 5;
const PARKED_VEHICLES = new Set(["plane", "side", "quay"]);

/**
 * Catamaran parked at Cayenne during the SPM episode (vehicle plane|side|quay).
 * The crew sample may sit at Halifax; the boat the skipper clicks is at park.
 */
export function parkedCatamaranSample(clockSample) {
  if (!clockSample) return null;
  if (!PARKED_VEHICLES.has(clockSample.vehicle)) return null;
  const lat = Number(clockSample.parkLat);
  const lon = Number(clockSample.parkLon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  return { lat, lon };
}

/**
 * Nearest stop ≤ 5 nm of the clock sample (lot C / RE2).
 */
export function nearestAlongside(clockSample, marks) {
  if (!clockSample || !Number.isFinite(clockSample.lat) || !Number.isFinite(clockSample.lon)) {
    return null;
  }
  let best = null;
  let bestD = Infinity;
  for (const m of marks || []) {
    if (!Number.isFinite(m.lat) || !Number.isFinite(m.lon)) continue;
    const d = haversineNm(clockSample.lat, clockSample.lon, m.lat, m.lon);
    if (d < bestD) { bestD = d; best = m; }
  }
  if (!best || bestD > ALONGSIDE_NM) return null;
  return best;
}

/**
 * Auto-open the nearest alongside stop of the clock sample that the
 * caller passed — Suivre (live officiel) or Tracer (playhead du tracé).
 * Lot DM7 : plus de garde isSuivre ; c'est le sample qui cloisonne.
 * A user-opened sheet (flag) is never replaced by another stop
 * (KO #309: list click left clockSample on the live alongside stop,
 * so the effect overwrote the designated name with Fort-de-France).
 */
export function pickAutoEscaleStop({
  filmActive = false,
  hold = false,
  userPicked = false,
  isSuivre: _isSuivre = false,
  atQuay = false,
  clockSample = null,
  marks = [],
} = {}) {
  if (filmActive || hold || userPicked) return null;
  const parked = parkedCatamaranSample(clockSample);
  if (parked) return nearestAlongside(parked, marks);
  if (!atQuay) return null;
  return nearestAlongside(clockSample, marks);
}
