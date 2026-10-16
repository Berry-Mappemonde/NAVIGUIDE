/**
 * Lot LY1 — chauffer les cellules AMP le long d'un trait dessiné.
 * Fire-and-forget : Terminer n'attend pas. Pas de texte d'aide.
 */

const API_URL = import.meta.env?.VITE_API_URL ?? "";

function pushLonLat(out, pair) {
  if (!Array.isArray(pair) || pair.length < 2) return;
  const lon = Number(pair[0]);
  const lat = Number(pair[1]);
  if (Number.isFinite(lat) && Number.isFinite(lon) && lat >= -90 && lat <= 90) {
    out.push([lat, lon]);
  }
}

function walkGeometry(geom, out) {
  if (!geom) return;
  const t = geom.type;
  const c = geom.coordinates;
  if (t === "Point") {
    pushLonLat(out, c);
  } else if (t === "MultiPoint" || t === "LineString") {
    for (const p of c || []) pushLonLat(out, p);
  } else if (t === "MultiLineString") {
    for (const line of c || []) {
      for (const p of line || []) pushLonLat(out, p);
    }
  } else if (t === "GeometryCollection") {
    for (const g of geom.geometries || []) walkGeometry(g, out);
  }
}

/** Points [lat, lon] du GeoJSON dessiné / importé, dans l'ordre du trait. */
export function pointsFromCustomRoute(geojson) {
  const out = [];
  for (const f of geojson?.features || []) walkGeometry(f?.geometry, out);
  return out;
}

/** Lance le chauffage des couches. Jamais d'exception vers l'UI. */
export function kickLayerWarm(geojson, fetchImpl = fetch) {
  const points = pointsFromCustomRoute(geojson);
  if (!points.length) return false;
  try {
    Promise.resolve(
      fetchImpl(`${API_URL}/ici/layers/warm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ points }),
      }),
    ).catch(() => {});
    return true;
  } catch {
    return false;
  }
}
