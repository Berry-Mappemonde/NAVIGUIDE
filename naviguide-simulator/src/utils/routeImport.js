import { haversineNm, lerpLon } from "./geo.js";

export const ROUTE_IMPORT_MAX_POINTS = 60;
export const ROUTE_IMPORT_DEDUP_NM = 0.1;

function parseCoordTuples(text) {
  return String(text || "")
    .trim()
    .split(/[\s\n\r]+/)
    .map((tuple) => {
      const parts = tuple.split(",");
      if (parts.length < 2) return null;
      const a = Number(parts[0]);
      const b = Number(parts[1]);
      if (!Number.isFinite(a) || !Number.isFinite(b)) return null;
      let lat = b;
      let lon = a;
      // GeoJSON/KML = lon,lat ; copier-coller carte = lat,lon (|lat| souvent > |lon| en Atlantique/Europe).
      if (Math.abs(a) <= 90 && Math.abs(b) <= 90 && Math.abs(a) > Math.abs(b)) {
        lat = a;
        lon = b;
      }
      if (lat < -90 || lat > 90) return null;
      return { lat, lon };
    })
    .filter(Boolean);
}

function pointName(value, index) {
  const name = value == null ? "" : String(value).trim();
  return name || `Point ${index + 1}`;
}

export function dedupRoutePoints(points, minNm = ROUTE_IMPORT_DEDUP_NM) {
  const out = [];
  for (const p of points || []) {
    const lat = Number(p.lat);
    const lon = Number(p.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
    const prev = out.at(-1);
    if (prev && haversineNm(prev.lat, prev.lon, lat, lon) < minNm) continue;
    out.push({ ...p, lat, lon });
  }
  return out;
}

function finalize(points, source) {
  const cleaned = dedupRoutePoints(points);
  if (!cleaned.length) return { error: "noPoints" };
  const truncated = cleaned.length > ROUTE_IMPORT_MAX_POINTS;
  const cut = truncated ? cleaned.slice(0, ROUTE_IMPORT_MAX_POINTS) : cleaned;
  return {
    points: cut.map((p, i) => ({ lat: p.lat, lon: p.lon, name: pointName(p.name, i) })),
    source,
    ...(truncated ? { truncated: true } : {}),
  };
}

function lineVertices(coords, name) {
  if (!Array.isArray(coords)) return [];
  return coords.map((c, i) => {
    if (!Array.isArray(c) || c.length < 2) return null;
    const lon = Number(c[0]);
    const lat = Number(c[1]);
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || lat < -90 || lat > 90) return null;
    return { lat, lon, name: i === 0 ? name : null };
  }).filter(Boolean);
}

function pushLonLat(out, lon, lat, name) {
  const x = Number(lon);
  const y = Number(lat);
  if (!Number.isFinite(x) || !Number.isFinite(y) || y < -90 || y > 90) return;
  out.push({ lat: y, lon: x, name: name || null });
}

function walkGeometry(geom, points, lines, name) {
  if (!geom || typeof geom !== "object") return;
  const type = geom.type;
  if (type === "Point") {
    const c = geom.coordinates;
    if (Array.isArray(c)) pushLonLat(points, c[0], c[1], name);
    return;
  }
  if (type === "MultiPoint") {
    (geom.coordinates || []).forEach((c, i) => {
      if (Array.isArray(c)) pushLonLat(points, c[0], c[1], i === 0 ? name : null);
    });
    return;
  }
  if (type === "LineString") {
    lines.push(...lineVertices(geom.coordinates, name));
    return;
  }
  if (type === "MultiLineString") {
    for (const c of geom.coordinates || []) lines.push(...lineVertices(c, name));
    return;
  }
  if (type === "GeometryCollection") {
    for (const g of geom.geometries || []) walkGeometry(g, points, lines, name);
  }
}

function walkGeojson(obj, points, lines) {
  if (!obj || typeof obj !== "object") return;
  if (obj.type === "FeatureCollection") {
    for (const f of obj.features || []) walkGeojson(f, points, lines);
    return;
  }
  if (obj.type === "Feature") {
    walkGeometry(obj.geometry, points, lines, obj.properties?.name);
    return;
  }
  walkGeometry(obj, points, lines, obj.properties?.name);
}

function parseGeojson(text) {
  let obj;
  try {
    obj = JSON.parse(text);
  } catch {
    return { error: "invalid" };
  }
  if (!obj || typeof obj !== "object") return { error: "invalid" };
  const points = [];
  const lines = [];
  walkGeojson(obj, points, lines);
  return finalize(points.length ? points : lines, "geojson");
}

function decodeXml(text) {
  return String(text || "")
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .trim();
}

function tagInner(block, tag) {
  const m = String(block).match(new RegExp(`<${tag}\\b[^>]*>([\\s\\S]*?)</${tag}>`, "i"));
  return m ? decodeXml(m[1]) : "";
}

function geomCoords(block, geom) {
  const m = String(block).match(new RegExp(`<${geom}\\b[\\s\\S]*?<coordinates\\b[^>]*>([\\s\\S]*?)</coordinates>`, "i"));
  return m ? parseCoordTuples(m[1]) : [];
}

function collectKmlParts(placemarks) {
  const points = [];
  const lines = [];
  for (const mark of placemarks) {
    const name = mark.name || null;
    for (const p of mark.points) points.push({ ...p, name });
    mark.lines.forEach((line, li) => {
      line.forEach((p, i) => lines.push({ ...p, name: li === 0 && i === 0 ? name : null }));
    });
  }
  return finalize(points.length ? points : lines, "kml");
}

function parseKmlWithDom(text) {
  const doc = new DOMParser().parseFromString(text, "text/xml");
  if (doc.getElementsByTagName("parsererror").length) return { error: "invalid" };
  const marks = [...doc.getElementsByTagName("Placemark")];
  const placemarks = (marks.length ? marks : [doc.documentElement]).map((el) => {
    const name = decodeXml(el.getElementsByTagName("name")[0]?.textContent || "");
    const points = [...el.getElementsByTagName("Point")].flatMap((pt) => {
      const node = pt.getElementsByTagName("coordinates")[0];
      return parseCoordTuples(node?.textContent || "");
    });
    const lines = [...el.getElementsByTagName("LineString")].map((ls) => {
      const node = ls.getElementsByTagName("coordinates")[0];
      return parseCoordTuples(node?.textContent || "");
    });
    return { name, points, lines };
  });
  return collectKmlParts(placemarks);
}

function parseKmlWithTags(text) {
  if (!/<kml\b|<Placemark\b|<Point\b|<LineString\b/i.test(text)) return { error: "invalid" };
  const blocks = text.match(/<Placemark\b[\s\S]*?<\/Placemark>/gi) || [text];
  const placemarks = blocks.map((block) => ({
    name: tagInner(block, "name"),
    points: geomCoords(block, "Point"),
    lines: (block.match(/<LineString\b[\s\S]*?<\/LineString>/gi) || []).map((ls) => geomCoords(ls, "LineString")),
  }));
  return collectKmlParts(placemarks);
}

function parseKml(text) {
  if (typeof DOMParser === "function") return parseKmlWithDom(text);
  return parseKmlWithTags(text);
}

function looksJson(text) {
  const t = text.trim();
  return t.startsWith("{") || t.startsWith("[");
}

/**
 * A rhumb sampled between the endpoints. Two consecutive land hits
 * (a mask already loaded, or the caller's predicate) refuse the fallback.
 */
export function rhumbCrossesLand(from, to, isLand, steps = 16) {
  if (typeof isLand !== "function") return false;
  const lat1 = Number(from?.lat);
  const lon1 = Number(from?.lon);
  const lat2 = Number(to?.lat);
  const lon2 = Number(to?.lon);
  if (![lat1, lon1, lat2, lon2].every(Number.isFinite)) return false;
  let consecutive = 0;
  const n = Math.max(2, steps);
  for (let i = 1; i < n; i += 1) {
    const t = i / n;
    const lat = lat1 + (lat2 - lat1) * t;
    const lon = lerpLon(lon1, lon2, t);
    if (isLand(lat, lon)) {
      consecutive += 1;
      if (consecutive >= 2) return true;
    } else {
      consecutive = 0;
    }
  }
  return false;
}

/** Refuse a straight fallback that would cross land. `null` means the rhumb is allowed. */
export function refuseRhumbFallback(from, to, options = {}) {
  const detail = options.serverDetail || options.detail || "";
  if (detail === "crosses_land") return { error: "rhumbCrossesLand" };
  if (rhumbCrossesLand(from, to, options.isLand)) return { error: "rhumbCrossesLand" };
  return null;
}

/**
 * GeoJSON (Point / MultiPoint / LineString / Feature / FeatureCollection)
 * or KML Placemark Point / LineString → ordered waypoints.
 */
export function parseRouteFile(text, name = "") {
  const raw = String(text ?? "").replace(/^\uFEFF/, "");
  if (!raw.trim()) return { error: "empty" };
  const preferKml = String(name || "").toLowerCase().endsWith(".kml");
  if (preferKml) {
    const kml = parseKml(raw);
    if (kml.error && looksJson(raw)) return parseGeojson(raw);
    return kml;
  }
  if (looksJson(raw)) return parseGeojson(raw);
  const kml = parseKml(raw);
  if (!kml.error) return kml;
  const tuples = parseCoordTuples(raw);
  if (tuples.length) return finalize(tuples, "coords");
  return kml;
}
