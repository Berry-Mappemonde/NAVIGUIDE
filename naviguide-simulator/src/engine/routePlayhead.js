import { haversineNm, unwrapLon } from "../utils/geo.js";

/** Au-delà : jonction entre segments = saut (avion), pas de la route. */
export const AIR_JUMP_NM = 120;

export function isNamedEscale(stop) {
  return Boolean(stop?.flag);
}

/**
 * Aplati tous les segments (terre comprise) en une polyligne + miles cumulés.
 * Point 0 = premier vertex (Saint-Maur pour Berry).
 * Sauts aériens (Cayenne → Halifax / SPM) : 0 nm, bateau téléporté.
 * Longitudes déroulées pour passer l’antiméridien sans couper le film.
 */
export function flattenRoute(segments) {
  const points = [];
  let cumNm = 0;

  const add = (lon, lat, { jump = false, nonMaritime = false } = {}) => {
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    if (points.length) {
      const prev = points[points.length - 1];
      lon = unwrapLon(prev.lon, lon);
      const same = Math.abs(prev.lat - lat) < 1e-9 && Math.abs(prev.lon - lon) < 1e-6;
      if (same) return;
      if (!jump) cumNm += haversineNm(prev.lat, prev.lon, lat, lon);
    }
    points.push({
      lon,
      lat,
      cumNm,
      nonMaritime: Boolean(nonMaritime),
      jump: Boolean(jump),
    });
  };

  for (const seg of segments || []) {
    const coords = seg?.coords;
    if (!coords || coords.length < 2) continue;
    let start = 0;
    if (points.length) {
      const [lon0, lat0] = coords[0];
      const prev = points[points.length - 1];
      if (Number.isFinite(lat0) && Number.isFinite(lon0)
        && haversineNm(prev.lat, prev.lon, lat0, lon0) >= AIR_JUMP_NM) {
        add(lon0, lat0, { jump: true, nonMaritime: seg.nonMaritime });
        start = 1;
      }
    }
    for (let i = start; i < coords.length; i++) {
      add(coords[i][0], coords[i][1], { nonMaritime: seg.nonMaritime });
    }
  }
  return { points, totalNm: points.length ? points[points.length - 1].cumNm : 0 };
}

function initialBearing(lat1, lon1, lat2, lon2) {
  const toRad = (d) => (d * Math.PI) / 180;
  const lon2u = unwrapLon(lon1, lon2);
  const φ1 = toRad(lat1);
  const φ2 = toRad(lat2);
  const Δλ = toRad(lon2u - lon1);
  const y = Math.sin(Δλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

function projectOnSegment(pLat, pLon, aLat, aLon, bLat, bLon) {
  const dx = bLon - aLon;
  const dy = bLat - aLat;
  const lenSq = dx * dx + dy * dy;
  let t = 0;
  if (lenSq > 0) {
    t = ((pLon - aLon) * dx + (pLat - aLat) * dy) / lenSq;
    t = Math.max(0, Math.min(1, t));
  }
  const qLon = aLon + t * dx;
  const qLat = aLat + t * dy;
  return { lon: qLon, lat: qLat, t, distNm: haversineNm(pLat, pLon, qLat, qLon) };
}

export function interpolateAtNm(flat, nm) {
  const pts = flat?.points || [];
  if (pts.length === 0) return null;
  if (pts.length === 1) {
    return {
      lon: pts[0].lon,
      lat: pts[0].lat,
      bearing: 0,
      nonMaritime: pts[0].nonMaritime,
      nm: 0,
      jump: Boolean(pts[0].jump),
    };
  }
  const target = Math.max(0, Math.min(flat.totalNm, Number(nm) || 0));
  // ≤ : on franchit les sauts (plusieurs points au même cumNm) d’un coup.
  let i = 0;
  while (i < pts.length - 2 && pts[i + 1].cumNm <= target) i += 1;
  const a = pts[i];
  const b = pts[i + 1];
  if (b.jump) {
    const next = pts[i + 2];
    return {
      lon: b.lon,
      lat: b.lat,
      bearing: next
        ? initialBearing(b.lat, b.lon, next.lat, next.lon)
        : initialBearing(a.lat, a.lon, b.lat, b.lon),
      nonMaritime: Boolean(b.nonMaritime),
      nm: target,
      jump: true,
    };
  }
  const span = b.cumNm - a.cumNm;
  const t = span > 0 ? (target - a.cumNm) / span : 1;
  const lat = a.lat + t * (b.lat - a.lat);
  const lon = a.lon + t * (b.lon - a.lon);
  return {
    lon,
    lat,
    bearing: initialBearing(a.lat, a.lon, b.lat, b.lon),
    nonMaritime: Boolean(a.nonMaritime && b.nonMaritime),
    nm: target,
    jump: false,
  };
}

export function nearestNm(flat, lat, lon) {
  const pts = flat?.points || [];
  if (pts.length < 2) return 0;
  let bestNm = 0;
  let bestD = Infinity;
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i];
    const b = pts[i + 1];
    if (b.jump || (a.cumNm === b.cumNm && haversineNm(a.lat, a.lon, b.lat, b.lon) >= AIR_JUMP_NM)) {
      continue;
    }
    const qLon = unwrapLon(a.lon, lon);
    const res = projectOnSegment(lat, qLon, a.lat, a.lon, b.lat, b.lon);
    if (res.distNm < bestD) {
      bestD = res.distNm;
      const span = b.cumNm - a.cumNm;
      bestNm = a.cumNm + res.t * span;
    }
  }
  return bestNm;
}

/** Escales à drapeau, posées sur la route dans l’ordre chronologique. */
export function mapEscalesOnRoute(stops, flat) {
  const pts = flat?.points || [];
  if (!pts.length) return [];
  let search = 0;
  const marks = [];
  for (const stop of stops || []) {
    if (!isNamedEscale(stop)) continue;
    let best = search;
    let bestD = Infinity;
    for (let i = search; i < pts.length; i++) {
      const d = haversineNm(stop.lat, stop.lon, pts[i].lat, pts[i].lon);
      if (d < bestD) {
        bestD = d;
        best = i;
      }
    }
    marks.push({
      name: stop.name,
      lat: stop.lat,
      lon: stop.lon,
      nm: pts[best].cumNm,
      index: best,
    });
    search = best;
  }
  return marks;
}

export function chapterAtNm(marks, nm) {
  if (!marks?.length) {
    return { from: null, to: null, fromIdx: -1, toIdx: -1, finished: false };
  }
  const x = Number(nm) || 0;
  let fromIdx = 0;
  for (let i = 0; i < marks.length; i++) {
    if (marks[i].nm <= x + 0.05) fromIdx = i;
    else break;
  }
  const finished = fromIdx >= marks.length - 1;
  const toIdx = finished ? fromIdx : fromIdx + 1;
  return {
    from: marks[fromIdx],
    to: marks[toIdx],
    fromIdx,
    toIdx,
    finished,
  };
}

export function nextEscaleNm(marks, nm) {
  const x = Number(nm) || 0;
  const nxt = (marks || []).find((m) => m.nm > x + 1);
  return nxt ? nxt.nm : (marks?.at(-1)?.nm ?? x);
}

export function prevEscaleNm(marks, nm) {
  const x = Number(nm) || 0;
  let prev = marks?.[0]?.nm ?? 0;
  for (const m of marks || []) {
    if (m.nm < x - 1) prev = m.nm;
    else break;
  }
  return prev;
}

/** La Rochelle → Fort-de-France, ou à défaut ~12 % de la route. */
export function atlanticSpanNm(marks, totalNm) {
  const start = (marks || []).find((m) => /La Rochelle/i.test(m.name));
  const end = (marks || []).find((m) => /Fort-de-France/i.test(m.name));
  if (start && end && end.nm > start.nm) return end.nm - start.nm;
  return Math.max(2000, (Number(totalNm) || 8000) * 0.12);
}

/** HUD du film : noms d’escales complets, restants jusqu’à la prochaine. */
export function filmLegContext({ marks, nm, sample, totalNm, boatKnots }) {
  const chapter = chapterAtNm(marks, nm);
  const remaining = chapter.finished
    ? 0
    : Math.max(0, (chapter.to?.nm ?? totalNm) - (Number(nm) || 0));
  const knots = Number(boatKnots) > 0 ? Number(boatKnots) : 7;
  const covered = Math.max(0, Number(nm) || 0);
  return {
    fromStop: chapter.from?.name ?? "Départ",
    toStop: chapter.finished
      ? (chapter.from?.name ?? "Arrivée")
      : (chapter.to?.name ?? "Arrivée"),
    fromStopIndex: chapter.fromIdx,
    toStopIndex: chapter.toIdx,
    nmCovered: Math.round(covered),
    nmRemainingToStop: Math.round(remaining),
    etaHours: knots > 0 ? remaining / knots : 0,
    bearing: Math.round(sample?.bearing ?? 0),
    snappedPosition: sample ? [sample.lon, sample.lat] : null,
    speedKnots: Math.round(knots * 10) / 10,
    finished: chapter.finished,
    remainingNm: remaining,
    chapter,
  };
}
