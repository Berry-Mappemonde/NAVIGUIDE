export const SEGMENT_BATCH_SIZE = 4;

const NON_MARITIME_NAMES = new Set([
  "Saint-Maur (Berry, Indre)|La Rochelle",
  "La Rochelle|Saint-Maur (Berry, Indre)",
]);

const SKIP_FROM_NAMES = new Set([
  "Marigot (Saint-Martin)",
  "Cayenne (Guyane)",
  "Halifax (Nouvelle-Écosse)",
  "Saint-Pierre (Saint-Pierre-et-Miquelon)",
]);

export function buildBerryLegs(points) {
  const byName = (name) => points.find((p) => p.name === name);
  const legs = [];
  for (let i = 0; i < points.length - 1; i++) {
    if (SKIP_FROM_NAMES.has(points[i].name)) continue;
    legs.push({ from: points[i], to: points[i + 1] });
  }
  const marigotIdx = legs.findIndex((l) => l.to.name === "Marigot (Saint-Martin)");
  if (marigotIdx >= 0 && byName("Marigot (Saint-Martin)") && byName("Cayenne (Guyane)")) {
    legs.splice(marigotIdx + 1, 0, {
      from: byName("Marigot (Saint-Martin)"),
      to: byName("Cayenne (Guyane)"),
    });
  }
  const cayenneIdx = legs.findIndex((l) => l.to.name === "Cayenne (Guyane)");
  if (cayenneIdx >= 0) {
    const halifax = byName("Halifax (Nouvelle-Écosse)");
    const spm = byName("Saint-Pierre (Saint-Pierre-et-Miquelon)");
    const papeete = byName("Papeete (Polynésie française)");
    const cayenne = byName("Cayenne (Guyane)");
    const extra = [];
    if (halifax && spm) extra.push({ from: halifax, to: spm }, { from: spm, to: halifax });
    if (cayenne && papeete) extra.push({ from: cayenne, to: papeete });
    legs.splice(cayenneIdx + 1, 0, ...extra);
  }
  return legs.filter((l) => l.from && l.to);
}

export function isNonMaritimeLeg(fromName, toName) {
  return NON_MARITIME_NAMES.has(`${fromName}|${toName}`);
}

export function orientCoords(coords, from, to) {
  if (!coords || coords.length < 2) return coords;
  const sq = (coord, point) => {
    const dLon = coord[0] - point.lon;
    const dLat = coord[1] - point.lat;
    return dLon * dLon + dLat * dLat;
  };
  return sq(coords[0], to) < sq(coords[0], from) ? [...coords].reverse() : coords;
}

export function coordsFromRoutePayload(data) {
  if (data?.type === "FeatureCollection" && data.features?.[0]?.geometry?.coordinates) {
    return data.features[0].geometry.coordinates;
  }
  if (data?.geometry?.coordinates) return data.geometry.coordinates;
  return [];
}
