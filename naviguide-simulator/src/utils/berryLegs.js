export const SEGMENT_BATCH_SIZE = 4;

/** 1 mille nautique = 1,852 km (étape terrestre, lot R5). */
export const NM_TO_KM = 1.852;

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

function canonStopName(name) {
  const s = String(name || "").trim();
  if (/^saint-maur\b/i.test(s) && !/Berry/i.test(s)) return "Saint-Maur (Berry, Indre)";
  return s;
}

/** Jambe terrestre (Berry : Saint-Maur ↔ La Rochelle), noms courts ou complets. */
export function isLandLegNames(fromName, toName) {
  return isNonMaritimeLeg(fromName, toName)
    || isNonMaritimeLeg(canonStopName(fromName), canonStopName(toName));
}

function airStopKey(name) {
  const s = String(name || "");
  if (/cayenne/i.test(s)) return "cayenne";
  if (/halifax/i.test(s)) return "halifax";
  return "";
}

/** Jambe avion : uniquement Cayenne ↔ Halifax (aller et retour). Halifax ↔ Saint-Pierre est mer. */
export function isAirLegNames(fromName, toName) {
  const a = airStopKey(fromName);
  const b = airStopKey(toName);
  return (a === "cayenne" && b === "halifax") || (a === "halifax" && b === "cayenne");
}

export function isAirSegment(segment) {
  if (!segment) return false;
  if (segment.air || segment.jump || segment.kind === "air") return true;
  return isAirLegNames(segment.from?.name, segment.to?.name);
}

export function legKind(fromName, toName) {
  if (isAirLegNames(fromName, toName)) return "air";
  if (isLandLegNames(fromName, toName)) return "land";
  return "sea";
}

/** Style du trait officiel : mer = sillage ; terre = orange ; air = noir pointillé. */
export function officialRouteLineStyle(segment) {
  if (isAirSegment(segment)) {
    return { color: "#111111", weight: 2.5, dash: "7 7", interactive: false };
  }
  if (segment?.nonMaritime) {
    return { color: "orange", weight: 4, dash: "6 6", interactive: true };
  }
  return null;
}

/** Liseré clair sous le noir : le dash reste visible sur le fond sombre. */
export function officialAirRouteStyles(segment) {
  const main = officialRouteLineStyle(segment);
  if (!main || main.color !== "#111111") return main ? [main] : [];
  return [
    { ...main, color: "#e5e7eb", weight: 4.5 },
    main,
  ];
}

export function nmToRoundedKm(nm) {
  const n = Number(nm);
  if (!Number.isFinite(n)) return null;
  return Math.round(n * NM_TO_KM);
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
