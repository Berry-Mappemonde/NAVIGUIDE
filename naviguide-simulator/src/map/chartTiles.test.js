import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  CHART_TILE_STOPS,
  chartColorAt,
  chartFilterMarkup,
  chartTableValues,
  installChartTileFilters,
  isFractionalZoom,
  trackFractionalZoom,
} from "./chartTiles.js";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "..", "index.css"), "utf8");

test("chart tint: sea, land and labels land on the palette", () => {
  const night = CHART_TILE_STOPS["ng-chart-night"];
  assert.deepEqual(chartColorAt(night, 35), [0x0e, 0x22, 0x32]);
  assert.deepEqual(chartColorAt(night, 149), [0x8e, 0xa3, 0xae]);
  assert.deepEqual(chartColorAt(night, -5), [0x0e, 0x22, 0x32]);
  assert.deepEqual(chartColorAt(night, 300), [0xdc, 0xe6, 0xea]);
  const day = CHART_TILE_STOPS["ng-chart-day"];
  assert.deepEqual(chartColorAt(day, 208), [0xc8, 0xdc, 0xe6]);
  assert.deepEqual(chartColorAt(day, 239), [0xf4, 0xed, 0xd8]);
  assert.deepEqual(chartColorAt(day, 190), [0x9a, 0xa6, 0xad]);
});

test("chart tint: stops are sorted and span 0–255", () => {
  for (const stops of Object.values(CHART_TILE_STOPS)) {
    assert.equal(stops[0][0], 0);
    assert.equal(stops.at(-1)[0], 255);
    for (let i = 1; i < stops.length; i++) assert.ok(stops[i][0] > stops[i - 1][0]);
  }
});

test("chart tint: one table value per grey level and channel, all within 0–1", () => {
  const rows = chartTableValues(CHART_TILE_STOPS["ng-chart-night"]);
  assert.equal(rows.length, 3);
  for (const row of rows) {
    const values = row.split(" ").map(Number);
    assert.equal(values.length, 256);
    assert.ok(values.every((v) => v >= 0 && v <= 1));
  }
  // Sea (grey 35) lands exactly on its stop.
  assert.equal(rows[0].split(" ")[35], (0x0e / 255).toFixed(3));
});

test("chart tint: on the day chart, land is lighter than sea", () => {
  const day = CHART_TILE_STOPS["ng-chart-day"];
  const lum = ([r, g, b]) => 0.2126 * r + 0.7152 * g + 0.0722 * b;
  assert.ok(lum(chartColorAt(day, 239)) > lum(chartColorAt(day, 208)) + 10);
});

test("chart tint: the CSS targets each base map by URL with a filter that exists", () => {
  const markup = chartFilterMarkup();
  assert.match(css, /img\.leaflet-tile\[src\*="World_Dark_Gray_Base"\] \{ filter: url\(#ng-chart-night\); \}/);
  assert.match(css, /img\.leaflet-tile\[src\*="World_Light_Gray_Base"\] \{ filter: url\(#ng-chart-day\); \}/);
  assert.match(markup, /<filter id="ng-chart-night"/);
  assert.match(markup, /<filter id="ng-chart-day"/);
  assert.match(markup, /aria-hidden="true"/);
});

test("chart tint: base tiles overlap only at fractional zoom", () => {
  assert.equal(isFractionalZoom(4), false);
  assert.equal(isFractionalZoom(4.25), true);
  assert.equal(isFractionalZoom(Number.NaN), false);
  assert.match(css, /\.leaflet-container\.ng-frac-zoom img\.leaflet-tile\[src\*="_Gray_Base"\] \{ width: 257px !important; height: 257px !important; \}/);
  let zoom = 3.5;
  const classes = new Set();
  const handlers = {};
  const map = {
    getZoom: () => zoom,
    on: (name, fn) => { handlers[name] = fn; },
    getContainer: () => ({ classList: { toggle: (c, on) => (on ? classes.add(c) : classes.delete(c)) } }),
  };
  trackFractionalZoom(map);
  assert.ok(classes.has("ng-frac-zoom"));
  zoom = 4;
  handlers.zoomend();
  assert.ok(!classes.has("ng-frac-zoom"));
});

test("chart tint: installs once", () => {
  const inserted = [];
  const doc = {
    body: { insertAdjacentHTML: (where, html) => inserted.push([where, html]) },
    getElementById: () => (inserted.length ? {} : null),
  };
  installChartTileFilters(doc);
  installChartTileFilters(doc);
  assert.equal(inserted.length, 1);
  assert.equal(inserted[0][0], "afterbegin");
  installChartTileFilters(null);
});
