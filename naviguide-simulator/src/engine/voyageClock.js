/**
 * Table d’horloge civile le long du trait (contrat A = contrat B).
 * Intégrateur synchrone : dt = nm / nœuds. Vent via windFn ou zone du mois.
 */

import { alongTrackSpeed } from "./alongTrackSpeed.js";
import { boatSpeedFromWind, zoneWindAt } from "../utils/climatologyWind.js";
import { twaDeg } from "./routeWindProfile.js";

export const AIR_CALENDAR_HOURS = 8;
export const LAND_CALENDAR_HOURS = 4;
export const MIN_KNOTS = 0.5;
export const WAVE_NOGO_M = 2.5;
export const WAVE_NOGO_DT_FACTOR = 3;

export function portDaysFor(name) {
  const n = String(name || "").toLowerCase();
  if (/saint-?\s*maur/.test(n)) return 0;
  if (/la rochelle/.test(n)) return 3;
  if (/halifax/.test(n)) return 1;
  return 2;
}

export function twaFromHeading(bearing, dirFromDeg) {
  return twaDeg(bearing, dirFromDeg);
}

function toRad(d) {
  return (d * Math.PI) / 180;
}

export function bearingDeg(lat1, lon1, lat2, lon2) {
  let dLon = lon2 - lon1;
  while (dLon > 180) dLon -= 360;
  while (dLon < -180) dLon += 360;
  const φ1 = toRad(lat1);
  const φ2 = toRad(lat2);
  const Δλ = toRad(dLon);
  const y = Math.sin(Δλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

export function parseIso(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) throw new Error(`t0 invalide: ${iso}`);
  return d;
}

export function toIso(date) {
  return new Date(date).toISOString().replace(/\.000Z$/, "Z");
}

function addHours(date, hours) {
  return new Date(date.getTime() + hours * 3600 * 1000);
}

function wrapLon(lon) {
  let x = lon;
  while (x > 180) x -= 360;
  while (x < -180) x += 360;
  return x;
}

function markIndexOnPoints(marks, points) {
  return (marks || []).map((m) => {
    if (Number.isInteger(m.index) && m.index >= 0 && m.index < points.length) {
      return { ...m, index: m.index };
    }
    const targetNm = m.nm ?? m.filmNm;
    let best = 0;
    let bestD = Infinity;
    for (let i = 0; i < points.length; i++) {
      const d = Math.abs((points[i].cumNm ?? 0) - (targetNm ?? 0));
      if (d < bestD) {
        bestD = d;
        best = i;
      }
    }
    return { ...m, index: best };
  });
}

export function findStartIndex(points, marks, startAt = "la-rochelle") {
  if (startAt === "saint-maur") return 0;
  const tagged = markIndexOnPoints(marks, points);
  const lr = tagged.find((m) => /la rochelle/i.test(m.name || ""));
  if (lr) return lr.index;
  return 0;
}

function defaultWindFn(lat, lon, t) {
  const month = t.getUTCMonth() + 1;
  return zoneWindAt(lat, lon, month);
}

function emitVertex({
  p, tHours, t0, bearing, speedKnots, wind, vehicle, month,
}) {
  const when = addHours(t0, tHours);
  return {
    filmNm: round4(p.filmCum ?? p.cumNm ?? 0),
    sailNm: round4(p.cumNm ?? 0),
    lat: p.lat,
    lon: wrapLon(p.lon),
    bearing: round1(bearing),
    tHours: round4(tHours),
    iso: toIso(when),
    speedKnots: speedKnots == null ? null : round1(speedKnots),
    windKnots: wind?.speedKnots == null ? null : round1(wind.speedKnots),
    twa: wind?.twa == null ? null : round1(wind.twa),
    month,
    vehicle,
    kind: wind?.kind || "climatology",
    model: wind?.model || null,
    leadHours: wind?.leadHours ?? null,
    reason: wind?.reason || null,
  };
}

function round1(n) {
  return Math.round(Number(n) * 10) / 10;
}

function round4(n) {
  return Math.round(Number(n) * 10000) / 10000;
}

/**
 * @param {object} opts
 * @param {Array} opts.points flattenRoute.points
 * @param {Array} opts.marks escales à drapeau
 * @param {string} opts.t0 ISO UTC
 * @param {object|null} opts.polarRaw
 * @param {string} [opts.startAt]
 * @param {Function} [opts.windFn] (lat, lon, Date) => wind
 */
export function buildVoyageClock({
  points,
  marks = [],
  t0,
  polarRaw = null,
  startAt = "la-rochelle",
  windFn = null,
} = {}) {
  const pts = points || [];
  const t0d = parseIso(t0);
  const windAt = windFn || defaultWindFn;
  const startIdx = pts.length ? findStartIndex(pts, marks, startAt) : 0;
  const taggedMarks = markIndexOnPoints(marks, pts);
  const markByIndex = new Map();
  for (const m of taggedMarks) markByIndex.set(m.index, m);

  const vertices = [];
  const clockMarks = [];
  let tHours = 0;
  let seaHours = 0;
  let quayHours = 0;

  const push = (v) => {
    vertices.push(v);
  };

  for (let i = 0; i < startIdx; i++) {
    const nxt = pts[i + 1] || pts[i];
    push(emitVertex({
      p: pts[i],
      tHours: 0,
      t0: t0d,
      bearing: bearingDeg(pts[i].lat, pts[i].lon, nxt.lat, nxt.lon),
      speedKnots: null,
      wind: { kind: "climatology", speedKnots: null, twa: null },
      vehicle: "land",
      month: t0d.getUTCMonth() + 1,
    }));
  }

  if (!pts.length) {
    return emptyClock(t0d);
  }

  const start = pts[startIdx];
  const startNext = pts[startIdx + 1] || start;
  push(emitVertex({
    p: start,
    tHours: 0,
    t0: t0d,
    bearing: bearingDeg(start.lat, start.lon, startNext.lat, startNext.lon),
    speedKnots: null,
    wind: { kind: "climatology", speedKnots: null, twa: null },
    vehicle: start.nonMaritime ? "land" : "boat",
    month: t0d.getUTCMonth() + 1,
  }));

  const landEndIdx = (() => {
    if (startAt !== "saint-maur") return -1;
    const lr = taggedMarks.find((m) => /la rochelle/i.test(m.name || ""));
    return lr ? lr.index : -1;
  })();

  for (let i = startIdx; i < pts.length - 1; i++) {
    const a = pts[i];
    const b = pts[i + 1];
    const bearing = bearingDeg(a.lat, a.lon, b.lat, b.lon);
    const spanNm = Math.max(0, (b.cumNm ?? 0) - (a.cumNm ?? 0));
    const when = addHours(t0d, tHours);
    const month = when.getUTCMonth() + 1;
    let vehicle = "boat";
    let speedKnots = null;
    let windPack = { kind: "climatology", speedKnots: null, twa: null };

    if (b.jump) {
      tHours += AIR_CALENDAR_HOURS;
      vehicle = "plane";
    } else if (a.nonMaritime && b.nonMaritime) {
      vehicle = "land";
      if (startAt === "saint-maur" && landEndIdx >= 0 && i + 1 === landEndIdx) {
        tHours += LAND_CALENDAR_HOURS;
      }
    } else {
      const midLat = (a.lat + b.lat) / 2;
      const midLon = (a.lon + b.lon) / 2;
      const w = windAt(midLat, midLon, when);
      const along = alongTrackSpeed({
        lat: midLat,
        lon: midLon,
        bearing,
        month,
        polarRaw,
        wind: w,
      });
      speedKnots = Math.max(MIN_KNOTS, along.speedKnots || boatSpeedFromWind(w.speedKnots));
      let dt = spanNm / speedKnots;
      if (w.hs != null && Number(w.hs) >= WAVE_NOGO_M) {
        dt *= WAVE_NOGO_DT_FACTOR;
      }
      tHours += dt;
      seaHours += dt;
      vehicle = "boat";
      windPack = {
        speedKnots: w.speedKnots,
        twa: along.twa,
        kind: along.kind || w.kind || "climatology",
        model: w.model,
        leadHours: w.leadHours,
        reason: w.reason,
      };
    }

    push(emitVertex({
      p: b,
      tHours,
      t0: t0d,
      bearing,
      speedKnots,
      wind: windPack,
      vehicle,
      month: addHours(t0d, tHours).getUTCMonth() + 1,
    }));

    const arrived = markByIndex.get(i + 1);
    if (arrived && i + 1 !== startIdx) {
      const hold = portDaysFor(arrived.name) * 24;
      const arriveIso = toIso(addHours(t0d, tHours));
      clockMarks.push({
        name: arrived.name,
        filmNm: round4(b.filmCum ?? b.cumNm ?? 0),
        tHours: round4(tHours),
        iso: arriveIso,
        holdHours: hold,
      });
      if (hold > 0) {
        tHours += hold;
        quayHours += hold;
        push(emitVertex({
          p: b,
          tHours,
          t0: t0d,
          bearing,
          speedKnots: 0,
          wind: { kind: windPack.kind || "climatology", speedKnots: windPack.speedKnots, twa: null },
          vehicle: "quay",
          month: addHours(t0d, tHours).getUTCMonth() + 1,
        }));
      }
    }
  }

  const last = vertices[vertices.length - 1];
  const kinds = new Set(vertices.map((v) => v.kind).filter(Boolean));
  return {
    t0: toIso(t0d),
    kind: kinds.has("forecast") ? "mixed" : "climatology",
    vertices,
    marks: clockMarks,
    seaHours: round4(seaHours),
    quayHours: round4(quayHours),
    arrivalIso: last?.iso || toIso(t0d),
  };
}

function emptyClock(t0d) {
  return {
    t0: toIso(t0d),
    kind: "climatology",
    vertices: [],
    marks: [],
    seaHours: 0,
    quayHours: 0,
    arrivalIso: toIso(t0d),
  };
}

export function lerp(a, b, t) {
  return a + (b - a) * t;
}

export function sampleClockAtHours(clock, tHours) {
  const verts = clock?.vertices || [];
  if (!verts.length) return null;
  const x = Number(tHours);
  if (x <= verts[0].tHours) return { ...verts[0], atQuay: false, status: x < 0 ? "waiting" : "live" };
  const last = verts[verts.length - 1];
  if (x >= last.tHours) return { ...last, atQuay: last.vehicle === "quay", status: "arrived" };
  for (let i = 0; i < verts.length - 1; i++) {
    const a = verts[i];
    const b = verts[i + 1];
    if (x > b.tHours) continue;
    const span = b.tHours - a.tHours || 1;
    const t = (x - a.tHours) / span;
    const sameNm = Math.abs((b.filmNm ?? 0) - (a.filmNm ?? 0)) < 1e-6;
    if (sameNm) {
      return { ...a, tHours: x, atQuay: true, status: "live", vehicle: "quay" };
    }
    return {
      ...a,
      lat: lerp(a.lat, b.lat, t),
      lon: lerp(a.lon, b.lon, t),
      filmNm: lerp(a.filmNm, b.filmNm, t),
      sailNm: lerp(a.sailNm, b.sailNm, t),
      tHours: x,
      atQuay: false,
      status: "live",
      kind: t < 0.5 ? a.kind : b.kind,
      speedKnots: b.speedKnots ?? a.speedKnots,
      windKnots: b.windKnots ?? a.windKnots,
      model: b.model ?? a.model,
      leadHours: b.leadHours ?? a.leadHours,
    };
  }
  return { ...last, atQuay: false, status: "arrived" };
}

export function sampleClockAtTime(clock, when) {
  const t0 = parseIso(clock.t0);
  const w = when instanceof Date ? when : parseIso(when);
  const hours = (w.getTime() - t0.getTime()) / 3600000;
  if (hours < 0) {
    const v = clock.vertices[0];
    return {
      ...v,
      atQuay: true,
      status: "waiting",
      countdownHours: -hours,
    };
  }
  return sampleClockAtHours(clock, hours);
}

export function sampleClockAtFilmNm(clock, filmNm) {
  const verts = clock?.vertices || [];
  if (!verts.length) return null;
  const x = Number(filmNm) || 0;
  if (x <= verts[0].filmNm) return verts[0];
  const last = verts[verts.length - 1];
  if (x >= last.filmNm) return last;
  for (let i = 0; i < verts.length - 1; i++) {
    const a = verts[i];
    const b = verts[i + 1];
    if (b.filmNm < x) continue;
    const span = b.filmNm - a.filmNm;
    if (span <= 1e-9) return a.tHours <= b.tHours ? a : b;
    const t = (x - a.filmNm) / span;
    return {
      ...a,
      lat: lerp(a.lat, b.lat, t),
      lon: lerp(a.lon, b.lon, t),
      filmNm: x,
      sailNm: lerp(a.sailNm, b.sailNm, t),
      tHours: lerp(a.tHours, b.tHours, t),
      iso: toIso(addHours(parseIso(clock.t0), lerp(a.tHours, b.tHours, t))),
      kind: t < 0.5 ? a.kind : b.kind,
      speedKnots: b.speedKnots ?? a.speedKnots,
    };
  }
  return last;
}

export function formatCivilUtc(iso, lang = "fr") {
  if (!iso) return "—";
  const d = parseIso(iso);
  const months = lang === "en"
    ? ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    : ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
  const day = d.getUTCDate();
  const mon = months[d.getUTCMonth()];
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${day} ${mon} ${hh}:${mm} UTC`;
}

export function seaDayIndex(tHours) {
  return Math.max(0, Math.floor(Number(tHours) / 24) + (Number(tHours) > 0 ? 1 : 0));
}
