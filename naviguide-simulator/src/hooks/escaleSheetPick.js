import { haversineNm } from "../utils/geo.js";

const ALONGSIDE_NM = 5;

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
 * Auto-open only the nearest alongside stop in Suivre.
 * A user-opened sheet (flag) is never replaced by another stop
 * (KO #309: list click left clockSample on the live alongside stop,
 * so the effect overwrote the designated name with Fort-de-France).
 */
export function pickAutoEscaleStop({
  filmActive = false,
  hold = false,
  userPicked = false,
  isSuivre = false,
  atQuay = false,
  clockSample = null,
  marks = [],
} = {}) {
  if (filmActive || hold || userPicked || !isSuivre || !atQuay) return null;
  return nearestAlongside(clockSample, marks);
}
