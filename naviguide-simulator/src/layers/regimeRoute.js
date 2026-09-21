/** Teinte de la route parcourue (lot C3). */
export const REGIME_COLORS = Object.freeze({
  hindcast: "#2dd4bf",
  forecast: "#38bdf8",
  climatology: "#c084fc",
});

function mergeRegimeCoords(segs) {
  const out = [];
  for (const s of segs) {
    const last = out.at(-1);
    if (last && last.regime === s.regime) {
      last.coords.push(s.coords[1]);
    } else {
      out.push({ regime: s.regime, coords: s.coords.slice() });
    }
  }
  return out;
}

/**
 * Tronçons de la route déjà parcourus, colorés par régime du pas courant.
 */
export function traveledRegimeSegments(vertices, traveledNm) {
  const limit = Number(traveledNm);
  const verts = Array.isArray(vertices) ? vertices : [];
  if (!Number.isFinite(limit) || limit <= 0 || verts.length < 2) return [];
  const raw = [];
  for (let i = 0; i < verts.length - 1; i++) {
    const a = verts[i];
    const b = verts[i + 1];
    if (!Number.isFinite(a?.lat) || !Number.isFinite(a?.lon)
      || !Number.isFinite(b?.lat) || !Number.isFinite(b?.lon)) continue;
    const aNm = Number(a.sailNm ?? a.filmNm ?? 0);
    const bNm = Number(b.sailNm ?? b.filmNm ?? 0);
    if (!(bNm > aNm + 1e-6)) continue;
    if (aNm >= limit) break;
    const endNm = Math.min(bNm, limit);
    const t = (endNm - aNm) / (bNm - aNm);
    const lat = a.lat + (b.lat - a.lat) * t;
    const lon = a.lon + (b.lon - a.lon) * t;
    raw.push({
      regime: b.regime || b.kind || a.regime || a.kind || "climatology",
      coords: [[a.lon, a.lat], [lon, lat]],
    });
  }
  return mergeRegimeCoords(raw);
}
