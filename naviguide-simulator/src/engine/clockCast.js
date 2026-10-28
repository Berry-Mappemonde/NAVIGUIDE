import { haversineNm, lerpLon, wrapLon } from "../utils/geo.js";

/**
 * Distribution du film lue sur l'horloge (Suivre / film), pas sur le trait.
 *
 * L'horloge sait déjà qui bouge : chaque sommet porte son véhicule
 * (main, quay, side, plane, land). Un épisode aérien = deux sommets « plane »
 * dont le second atterrit là où le premier a décollé (Cayenne → Halifax …
 * Halifax → Cayenne). Pendant l'épisode :
 *  - le bateau A (main) reste à quai au point de décollage ;
 *  - l'avion n'existe que sur les deux vols ;
 *  - le bateau B (side) n'existe qu'entre l'atterrissage à Halifax et le
 *    décollage du retour (Halifax → Saint-Pierre → Halifax).
 * Aucun acteur ne saute d'un bout à l'autre de l'Atlantique.
 */

/** Le retour atterrit à moins de ce rayon du décollage aller. */
export const CLOCK_EPISODE_RETURN_NM = 80;

function finite(v) {
  return Number.isFinite(v?.lat) && Number.isFinite(v?.lon) && Number.isFinite(v?.tHours);
}

function bearing(a, b) {
  const toRad = (d) => (d * Math.PI) / 180;
  const φ1 = toRad(a.lat);
  const φ2 = toRad(b.lat);
  const Δλ = toRad(lerpLon(a.lon, b.lon, 1) - a.lon);
  const y = Math.sin(Δλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

function hidden() {
  return { visible: false, lat: null, lon: null, bearing: 0 };
}

function actor(pos, heading = 0) {
  return { visible: true, lat: pos.lat, lon: wrapLon(pos.lon), bearing: heading };
}

const PREPARED = new WeakMap();

/** Sommets utilisables de l'horloge, dans l'ordre du temps. */
export function clockVertices(clock) {
  return (clock?.vertices || []).filter(finite);
}

/** Sommets + épisodes, calculés une fois par horloge (appelé à chaque image). */
function prepared(clock) {
  if (!clock || typeof clock !== "object") return null;
  let hit = PREPARED.get(clock);
  if (!hit || hit.source !== clock.vertices) {
    const verts = clockVertices(clock);
    hit = { source: clock.vertices, verts, episodes: clockAirEpisodes(verts) };
    PREPARED.set(clock, hit);
  }
  return hit;
}

/**
 * Épisodes aériens de l'horloge : { out, ret } = index des deux sommets
 * « plane » ; park = sommet de décollage (bateau A à quai), hub = atterrissage.
 */
export function clockAirEpisodes(verts) {
  const planes = [];
  for (let i = 1; i < verts.length; i++) {
    if (verts[i].vehicle === "plane") planes.push(i);
  }
  const episodes = [];
  for (let k = 0; k + 1 < planes.length; k++) {
    const out = planes[k];
    const ret = planes[k + 1];
    const park = verts[out - 1];
    const back = verts[ret];
    if (haversineNm(park.lat, park.lon, back.lat, back.lon) > CLOCK_EPISODE_RETURN_NM) continue;
    episodes.push({ out, ret, park, hub: verts[out] });
    k += 1;
  }
  return episodes;
}

/** Segment [a, b] de l'horloge qui contient tHours (le premier, aux égalités). */
function segmentAt(verts, tHours) {
  if (tHours <= verts[0].tHours) return { k: 0, u: 0 };
  const lastIdx = verts.length - 1;
  if (tHours >= verts[lastIdx].tHours) return { k: Math.max(0, lastIdx - 1), u: 1 };
  let lo = 0;
  let hi = lastIdx;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (verts[mid].tHours < tHours) lo = mid;
    else hi = mid;
  }
  const a = verts[lo];
  const b = verts[hi];
  const span = b.tHours - a.tHours;
  return { k: lo, u: span > 0 ? (tHours - a.tHours) / span : 1 };
}

function moves(a, b) {
  return Math.abs(a.lat - b.lat) > 1e-7 || Math.abs(a.lon - b.lon) > 1e-7;
}

/** Cap du dernier segment qui bouge dans [lo, k] ; à défaut, du prochain avant hi. */
function headingAt(verts, k, lo = 0, hi = verts.length - 1) {
  for (let j = k; j >= lo && j + 1 <= hi; j--) {
    if (moves(verts[j], verts[j + 1])) return bearing(verts[j], verts[j + 1]);
  }
  for (let j = k + 1; j + 1 <= hi; j++) {
    if (moves(verts[j], verts[j + 1])) return bearing(verts[j], verts[j + 1]);
  }
  return 0;
}

function lerpNum(a, b, u) {
  if (!Number.isFinite(a)) return Number.isFinite(b) ? b : 0;
  if (!Number.isFinite(b)) return a;
  return a + u * (b - a);
}

/**
 * Qui est où à l'instant tMs. Même forme que interpolateCast (filmCast.js) :
 * { phase, vehicle, main, side, plane, follow, hopFrom, hopTo }.
 */
export function castAtClock(clock, tMs) {
  const prep = prepared(clock);
  const verts = prep?.verts || [];
  if (!verts.length) return null;
  const t0 = Date.parse(clock?.t0);
  if (!Number.isFinite(t0) || !Number.isFinite(tMs)) return null;
  const tHours = (tMs - t0) / 3600000;
  const { episodes } = prep;
  if (verts.length === 1) {
    const main = actor(verts[0]);
    return {
      phase: "sail", vehicle: "main", sailNm: verts[0].sailNm ?? 0,
      main, side: hidden(), plane: hidden(), follow: main, hopFrom: null, hopTo: null,
    };
  }
  const { k, u } = segmentAt(verts, tHours);
  const a = verts[k];
  const b = verts[k + 1];
  const pos = { lat: a.lat + u * (b.lat - a.lat), lon: lerpLon(a.lon, b.lon, u) };
  const sailNm = lerpNum(a.sailNm, b.sailNm, u);
  const ep = episodes.find((e) => k + 1 >= e.out && k + 1 <= e.ret);
  if (ep) {
    const main = actor(ep.park, headingAt(verts, Math.max(0, ep.out - 2)));
    if (k + 1 === ep.out || k + 1 === ep.ret) {
      const outbound = k + 1 === ep.out;
      const plane = actor(pos, bearing(a, b));
      return {
        phase: outbound ? "air-out" : "air-return",
        vehicle: "plane",
        sailNm: a.sailNm ?? 0,
        main,
        side: hidden(),
        plane,
        follow: plane,
        hopFrom: outbound ? { lat: ep.park.lat, lon: ep.park.lon } : { lat: a.lat, lon: a.lon },
        hopTo: outbound ? { lat: b.lat, lon: b.lon } : { lat: ep.park.lat, lon: ep.park.lon },
      };
    }
    // Bateau B : cap pris sur sa propre route (jamais celui de l'avion).
    const side = actor(pos, headingAt(verts, k, ep.out, ep.ret - 1));
    return {
      phase: "side-sail", vehicle: "side", sailNm,
      main, side, plane: hidden(), follow: side, hopFrom: null, hopTo: null,
    };
  }
  const main = actor(pos, headingAt(verts, k));
  return {
    phase: "sail", vehicle: "main", sailNm,
    main, side: hidden(), plane: hidden(), follow: main, hopFrom: null, hopTo: null,
  };
}

/**
 * Distribution que la carte dessine. En film, celle publiée par le lecteur
 * (window.__naviguideFilm.cast, lue sur l'horloge à l'instant de la phrase) ;
 * sinon celle du trait (Tracer, aperçu).
 */
export function pickSceneCast({ filmActive, film, fallback }) {
  if (filmActive && film?.cast && film.cast.main) return film.cast;
  return typeof fallback === "function" ? fallback() : (fallback ?? null);
}
