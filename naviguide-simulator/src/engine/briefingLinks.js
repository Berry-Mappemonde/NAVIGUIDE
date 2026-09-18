/**
 * Briefing links — every place the ICI briefing names becomes clickable.
 * Pure functions. No HTTP. No chat.
 *
 * Two links per entity, in this order:
 *   1. "voir sur la carte" — the app switches the matching layer on and fits
 *      the map on the boat AND the place (handled by App / MapScene);
 *   2. the sheet — official site when the bag has one (Sextant, douane,
 *      marina website…), else a Google Maps sheet built from lat / lon.
 *
 * `segmentBriefing` never rewrites the text: it splits `narrateIci()` around
 * the names the bag already wrote, in order. Plain text stays identical.
 */

/** listPlaces() caps, mirrored from iciBriefing.js so we only link what is written. */
const WRITTEN = Object.freeze({
  poe: 4,
  amp: 3,
  project: 3,
  marina: 3,
  capitainerie: 2,
  wpi: 2,
  science: 3,
  anchorage: 3,
  aton: 3,
});

/** BI toggle (App `setShowBi*` / catalog id) to switch on for each kind. */
export const LAYER_FOR_KIND = Object.freeze({
  poe: "poe",
  amp: "amp",
  project: "projects",
  marina: "marinas",
  capitainerie: "capitaineries",
  wpi: "wpi",
  anchorage: "anchorages",
  aton: "aton",
  science: null, // decided by `source` (sextant, csr, argo, odatis, edmed)
});

const SCIENCE_LAYERS = new Set(["sextant", "csr", "argo", "odatis", "edmed"]);

/** Kinds that deserve a Google Maps sheet (a real place a skipper can go to). */
const MAPS_KINDS = new Set(["poe", "marina", "capitainerie", "wpi", "anchorage", "aton", "project"]);

/** null / undefined / "" stay unknown — Number(null) would lie with 0. */
function finite(n) {
  if (n == null || n === "") return null;
  return Number.isFinite(Number(n)) ? Number(n) : null;
}

function cleanUrl(url) {
  if (!url || typeof url !== "string") return null;
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:" ? u.toString() : null;
  } catch {
    return null;
  }
}

export function googleMapsUrl(lat, lon) {
  const la = finite(lat);
  const lo = finite(lon);
  if (la == null || lo == null) return null;
  return `https://www.google.com/maps/search/?api=1&query=${la.toFixed(5)}%2C${lo.toFixed(5)}`;
}

function entity(kind, item, index) {
  if (!item || !item.name) return null;
  const url = cleanUrl(item.url) || (kind === "amp" ? cleanUrl(item.visit_url) || cleanUrl(item.manager_url) : null);
  return {
    id: `${kind}:${index}:${item.site_id ?? item.id ?? item.osm_id ?? item.name}`,
    kind,
    name: String(item.name),
    lat: finite(item.lat),
    lon: finite(item.lon),
    nm: finite(item.nm),
    url,
    source: item.source || null,
  };
}

/**
 * Entities in the order `narrateIci` writes them:
 * PoE → AMP → projects → marinas → capitaineries → WPI → science → anchorages → AtoN.
 */
export function briefingEntities(dossier) {
  if (!dossier) return [];
  const out = [];
  const push = (kind, items) => {
    (items || []).slice(0, WRITTEN[kind]).forEach((it, i) => {
      const e = entity(kind, it, i);
      if (e) out.push(e);
    });
  };
  push("poe", dossier.poe);
  push("amp", dossier.amp);
  push("project", dossier.projects);
  push("marina", dossier.nearby?.marinas);
  push("capitainerie", dossier.nearby?.capitaineries);
  push("wpi", dossier.nearby?.wpi);
  push("science", dossier.science?.nearby);
  push("anchorage", dossier.nearby?.anchorages);
  push("aton", dossier.aton?.nearby);
  return out;
}

/** Which BI layer to switch on so the place is drawn on the map. null = none. */
export function layerForEntity(e) {
  if (!e) return null;
  if (e.kind === "science") {
    const src = String(e.source || "").toLowerCase();
    return SCIENCE_LAYERS.has(src) ? src : null;
  }
  return LAYER_FOR_KIND[e.kind] ?? null;
}

/**
 * External sheets for an entity: official site first, Google Maps for real places.
 * `[{ kind: "site" | "maps", href, host }]`
 */
export function entityLinks(e) {
  if (!e) return [];
  const links = [];
  if (e.url) {
    let host = null;
    try { host = new URL(e.url).hostname.replace(/^www\./, ""); } catch { host = null; }
    links.push({ kind: "site", href: e.url, host });
  }
  if (MAPS_KINDS.has(e.kind)) {
    const maps = googleMapsUrl(e.lat, e.lon);
    if (maps) links.push({ kind: "maps", href: maps, host: "google.com/maps" });
  }
  return links;
}

/** A place can be focused on the map only with coordinates. */
export function canFocus(e) {
  return Boolean(e && e.lat != null && e.lon != null);
}

/**
 * Split the briefing text around entity names, sequentially (each entity is
 * searched after the previous match, so duplicates map to the right item).
 * Joining `segments.map(s => s.text)` gives back exactly `text`.
 */
export function segmentBriefing(text, entities) {
  const src = text || "";
  const segments = [];
  let cursor = 0;
  for (const e of entities || []) {
    if (!e?.name || e.name.length < 2) continue;
    const idx = src.indexOf(e.name, cursor);
    if (idx < 0) continue;
    if (idx > cursor) segments.push({ text: src.slice(cursor, idx) });
    segments.push({ text: e.name, entity: e });
    cursor = idx + e.name.length;
  }
  if (cursor < src.length) segments.push({ text: src.slice(cursor) });
  if (!segments.length && src) segments.push({ text: src });
  return segments;
}
