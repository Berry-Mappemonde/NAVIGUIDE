/** Rayon terrestre en milles nautiques. */
export const R_NM = 3440.065;

export function toRad(deg) {
  return (deg * Math.PI) / 180;
}

export function wrapLon(lon) {
  if (!Number.isFinite(lon)) return lon;
  let x = lon;
  while (x > 180) x -= 360;
  while (x < -180) x += 360;
  return x;
}

/** Unwrap longitudes so the track does not cross the map at 180°. */
export function unwrapLon(prevLon, lon) {
  if (!Number.isFinite(lon)) return lon;
  if (!Number.isFinite(prevLon)) return lon;
  let x = lon;
  while (x - prevLon > 180) x -= 360;
  while (x - prevLon < -180) x += 360;
  return x;
}

function isLonLat(coordinate) {
  return Array.isArray(coordinate)
    && coordinate.length >= 2
    && Number.isFinite(Number(coordinate[0]))
    && Number.isFinite(Number(coordinate[1]));
}

/**
 * Déplie une ligne GeoJSON pour que 179° → −179° reste un petit trait Pacifique.
 * La géométrie résultante peut dépasser ±180° : Leaflet peut alors la peindre
 * sans traverser le globe.
 */
export function unwrapLineCoords(coords, firstLon = null) {
  const out = [];
  for (const coordinate of coords || []) {
    if (!isLonLat(coordinate)) continue;
    const lon = Number(coordinate[0]);
    const lat = Number(coordinate[1]);
    const previousLon = out.at(-1)?.[0] ?? firstLon;
    out.push([unwrapLon(previousLon, lon), lat]);
  }
  return out;
}

export function haversineNm(lat1, lon1, lat2, lon2) {
  const dLat = toRad(lat2 - lat1);
  let dLonDeg = lon2 - lon1;
  while (dLonDeg > 180) dLonDeg -= 360;
  while (dLonDeg < -180) dLonDeg += 360;
  const dLon = toRad(dLonDeg);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R_NM * Math.asin(Math.sqrt(a));
}

/** Split a [lon,lat] polyline at ±180° (otherwise Leaflet draws across the globe). */
export function splitAntimeridianCoords(coords) {
  const parts = [[]];
  for (const c of coords || []) {
    if (!c || !Number.isFinite(c[0]) || !Number.isFinite(c[1])) continue;
    const part = parts[parts.length - 1];
    if (part.length) {
      const prev = part[part.length - 1];
      if (Math.abs(c[0] - prev[0]) > 180) {
        parts.push([c]);
        continue;
      }
    }
    part.push(c);
  }
  return parts.filter((p) => p.length >= 2);
}

/** Copies ±360° pour que le tour du monde reste visible (Afrique + Pacifique). */
export function worldCopyCoords(coords) {
  if (!coords || coords.length < 2) return [];
  return [
    coords,
    coords.map(([lon, lat]) => [lon + 360, lat]),
    coords.map(([lon, lat]) => [lon - 360, lat]),
  ];
}

/** Trois copies monde d'une ligne continue, y compris au franchissement de 180°. */
export function worldCopyLineCoords(coords) {
  return worldCopyCoords(unwrapLineCoords(coords));
}

/**
 * Trois copies d'un polygone GeoJSON. Chaque anneau est aligné sur l’anneau
 * extérieur avant décalage, afin de préserver trous et surfaces au Pacifique.
 */
export function worldCopyPolygonCoords(rings) {
  const outer = unwrapLineCoords(rings?.[0]);
  if (outer.length < 3) return [];
  const referenceLon = outer[0][0];
  const unwrappedRings = [
    outer,
    ...(rings || []).slice(1).map((ring) => unwrapLineCoords(ring, referenceLon)),
  ].filter((ring) => ring.length >= 3);
  return [0, 360, -360].map((offset) => (
    unwrappedRings.map((ring) => ring.map(([lon, lat]) => [lon + offset, lat]))
  ));
}

export function worldCopyLngs(lon) {
  const value = Number(lon);
  if (!Number.isFinite(value)) return [];
  return [value, value + 360, value - 360];
}

/** Triple chaque polyligne (monde 0 / +360 / −360). */
export function worldCopyParts(parts) {
  const out = [];
  for (const coords of parts || []) {
    out.push(...worldCopyCoords(coords));
  }
  return out;
}

/**
 * Distance nautique + nombre de segments d'une liste de polylignes
 * `segments` : [{ coords: [[lon, lat], ...] }]
 */
export function summarizeRoute(segments) {
  let nm = 0;
  let count = 0;
  if (!segments?.length) return { nm: 0, segments: 0 };
  for (const seg of segments) {
    const coords = seg?.coords;
    if (!coords || coords.length < 2) continue;
    count += 1;
    for (let i = 0; i < coords.length - 1; i++) {
      nm += haversineNm(coords[i][1], coords[i][0], coords[i + 1][1], coords[i + 1][0]);
    }
  }
  return { nm: Math.round(nm * 10) / 10, segments: count };
}

function segmentName(side) {
  return side?.name || "";
}

function segmentJoinsEscales(seg, fromName, toName) {
  const a = segmentName(seg?.from);
  const b = segmentName(seg?.to);
  return (a === fromName && b === toName) || (a === toName && b === fromName);
}

function legIsLand(from, to, segments) {
  const fromName = from?.name;
  const toName = to?.name;
  if (fromName && toName) {
    const hit = (segments || []).find((seg) => segmentJoinsEscales(seg, fromName, toName));
    if (hit) return Boolean(hit.nonMaritime);
  }
  return Boolean(from?.nonMaritime && to?.nonMaritime);
}

/**
 * Marques d'escale pour le résumé : une visite intérieure déjà vue
 * (Cayenne réinséré pour le HUD aérien) n'ajoute pas d'escale ; le
 * retour final qui reprend un nom déjà vu (La Rochelle) est gardé.
 */
export function marksForSummary(escaleMarks) {
  const named = (escaleMarks || []).filter((mark) => mark?.name);
  if (named.length <= 1) return named;
  const seen = new Set();
  const out = [];
  for (let i = 0; i < named.length; i++) {
    const name = named[i].name;
    const isLast = i === named.length - 1;
    if (seen.has(name) && !isLast) continue;
    seen.add(name);
    out.push(named[i]);
  }
  return out;
}

function vertexCount(segments) {
  return (segments || []).reduce((count, seg) => count + (seg?.coords?.length ?? 0), 0);
}

function routerWaypointCount(segments) {
  return (segments || []).filter((seg) => seg?.coords?.length >= 2).length;
}

/**
 * Étapes entre escales (pas les sommets du routeur).
 * Sans marques, une route dessinée compte pour 1 étape.
 */
export function summarizeLegs(escaleMarks, segments) {
  const segs = segments || [];
  const points = vertexCount(segs);
  const waypoints = routerWaypointCount(segs);
  const marks = marksForSummary(escaleMarks);

  if (marks.length >= 2) {
    let sea = 0;
    let land = 0;
    for (let i = 0; i < marks.length - 1; i++) {
      if (legIsLand(marks[i], marks[i + 1], segs)) land += 1;
      else sea += 1;
    }
    return {
      legs: marks.length - 1,
      sea,
      land,
      escales: marks.length,
      points,
      waypoints,
    };
  }

  const hasTrack = segs.some((seg) => seg?.coords?.length >= 2);
  if (hasTrack) {
    const landOnly = segs.every((seg) => !seg.coords?.length || seg.nonMaritime);
    return {
      legs: 1,
      sea: landOnly ? 0 : 1,
      land: landOnly ? 1 : 0,
      escales: marks.length,
      points,
      waypoints,
    };
  }

  return { legs: 0, sea: 0, land: 0, escales: marks.length, points, waypoints };
}

/** FeatureCollection LineString → segments { coords } pour summarizeRoute / export. */
export function featuresToSegments(fc) {
  if (!fc?.features) return [];
  return fc.features
    .filter((f) => f?.geometry?.type === "LineString" && f.geometry.coordinates?.length >= 2)
    .map((f) => ({
      coords: f.geometry.coordinates,
      from: { name: f.properties?.from || f.properties?.name || "" },
      to: { name: f.properties?.to || "" },
      nonMaritime: false,
    }));
}
