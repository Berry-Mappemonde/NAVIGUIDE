import { haversineNm } from "../utils/geo.js";
import { gebcoLookup } from "./gebco.js";

export const ICI_RADIUS_NM = 30;
export const SCIENCE_LOCAL_NM = 2;

export function emptyDossier(lat, lon) {
  return {
    version: 1,
    at: { lat, lon },
    radiusNm: ICI_RADIUS_NM,
    zee: null,
    poe: [],
    amp: [],
    projects: [],
    nearby: { marinas: [], capitaineries: [], wpi: [] },
    marks: [],
    science: null,
    weather: null,
    polar: null,
    event: null,
    depthOffshore: null,
  };
}

/** 0 ou 1 objet science local — jamais les catalogues. */
export function pickLocalScience(lat, lon, features, radiusNm = SCIENCE_LOCAL_NM) {
  if (!features?.length || lat == null || lon == null) return null;
  let best = null;
  let bestD = Infinity;
  for (const f of features) {
    const p = f.properties || {};
    let glat = p.lat;
    let glon = p.lon;
    if (glat == null || glon == null) {
      const geom = f.geometry || {};
      const c = geom.coordinates;
      if (geom.type === "Point" && Array.isArray(c)) {
        glon = c[0];
        glat = c[1];
      } else if (geom.type === "LineString" && c?.length) {
        const mid = c[Math.floor(c.length / 2)];
        glon = mid[0];
        glat = mid[1];
      }
    }
    if (glat == null || glon == null) continue;
    const d = haversineNm(lat, lon, glat, glon);
    if (d <= radiusNm && d < bestD) {
      bestD = d;
      best = {
        id: p.id,
        name: p.name,
        source: p.source,
        kind: p.kind,
        error_m: p.error_m ?? null,
        method: p.method ?? null,
      };
    }
  }
  return best;
}

export function ici(lat, lon, extras = {}) {
  const d = emptyDossier(lat, lon);
  if (extras.polarMeta) {
    d.polar = {
      boat: extras.polarMeta.boat_name,
      vmgHint: extras.polarMeta.vmg_summary?.["12"] ?? null,
    };
  }
  if (extras.weather) d.weather = extras.weather;
  if (extras.science !== undefined) d.science = extras.science;
  else d.science = pickLocalScience(lat, lon, extras.scienceFeatures);
  d.depthOffshore = extras.depthOffshore !== undefined
    ? extras.depthOffshore
    : gebcoLookup(lat, lon, {
        grid: extras.gebcoGrid,
        distToShoreNm: extras.distToShoreNm,
      });
  return d;
}
