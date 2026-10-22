/**
 * Chart tint for the Esri grey base maps. Each grey level of a tile maps to a
 * colour of the chart palette (sea, coast, land, labels), so the map and the
 * panels read as one surface. index.css applies the filters by tile URL.
 */

/** Grey level of the source tile (0–255) → chart colour. Sorted by level. */
export const CHART_TILE_STOPS = Object.freeze({
  // World_Dark_Gray_Base: sea ≈ 35, land ≈ 63, labels ≈ 150.
  "ng-chart-night": [
    [0, "#0e2232"],
    [35, "#0e2232"],
    [63, "#283643"],
    [149, "#8ea3ae"],
    [255, "#dce6ea"],
  ],
  // World_Light_Gray_Base: labels ≈ 110, borders ≈ 190, sea ≈ 208, land ≈ 239.
  // Sea darker than land, and borders stay grey rather than sea blue.
  "ng-chart-day": [
    [0, "#2a333d"],
    [110, "#3a4552"],
    [190, "#9aa6ad"],
    [208, "#c8dce6"],
    [239, "#f4edd8"],
    [255, "#f8f3e6"],
  ],
});

// One entry per grey level, so every stop renders exactly.
const TABLE_SIZE = 256;

function channels(hex) {
  const n = Number.parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** Piecewise-linear colour at a grey level, clamped to the first and last stops. */
export function chartColorAt(stops, level) {
  if (level <= stops[0][0]) return channels(stops[0][1]);
  for (let i = 1; i < stops.length; i++) {
    const [hi, hiHex] = stops[i];
    if (level <= hi) {
      const [lo, loHex] = stops[i - 1];
      const t = hi === lo ? 1 : (level - lo) / (hi - lo);
      const a = channels(loHex);
      const b = channels(hiHex);
      return a.map((v, c) => v + (b[c] - v) * t);
    }
  }
  return channels(stops[stops.length - 1][1]);
}

/** `tableValues` for feFuncR/G/B: TABLE_SIZE evenly spaced grey levels. */
export function chartTableValues(stops, size = TABLE_SIZE) {
  const rows = [[], [], []];
  for (let i = 0; i < size; i++) {
    const rgb = chartColorAt(stops, (255 * i) / (size - 1));
    rgb.forEach((v, c) => rows[c].push((v / 255).toFixed(3)));
  }
  return rows.map((row) => row.join(" "));
}

export function chartFilterMarkup() {
  const filters = Object.entries(CHART_TILE_STOPS).map(([id, stops]) => {
    const [r, g, b] = chartTableValues(stops);
    return `<filter id="${id}" color-interpolation-filters="sRGB"><feComponentTransfer>`
      + `<feFuncR type="table" tableValues="${r}"/>`
      + `<feFuncG type="table" tableValues="${g}"/>`
      + `<feFuncB type="table" tableValues="${b}"/>`
      + "</feComponentTransfer></filter>";
  });
  return `<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" aria-hidden="true" focusable="false" style="position:absolute;width:0;height:0;overflow:hidden">${filters.join("")}</svg>`;
}

/** True between integer zoom levels, when Leaflet scales the tiles and seams can appear. */
export function isFractionalZoom(zoom) {
  return Number.isFinite(zoom) && Math.abs(zoom - Math.round(zoom)) > 1e-6;
}

/** Marks the map container with `ng-frac-zoom` while the zoom is fractional (see index.css). */
export function trackFractionalZoom(map) {
  const sync = () => map.getContainer().classList.toggle("ng-frac-zoom", isFractionalZoom(map.getZoom()));
  map.on("zoomend", sync);
  sync();
}

/** Adds the filters once, at the start of <body>. */
export function installChartTileFilters(doc = globalThis.document) {
  if (!doc?.body || doc.getElementById("ng-chart-night")) return;
  doc.body.insertAdjacentHTML("afterbegin", chartFilterMarkup());
}
