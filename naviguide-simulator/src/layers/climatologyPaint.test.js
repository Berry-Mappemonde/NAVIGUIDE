import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { layerPopupHtml, pointPopupHtml, roseSvg, waveColor } from "./climatologyPaint.js";

const t = (key) => ({
  climoAverage: "AVERAGE",
  climoMostLikely: "MOST_LIKELY",
  climoDisclaimer: "Not for navigation.",
  modeClimatologyFull: "Climatologie",
  climoWaveP50Hint: "P50",
  climoWaveP90Hint: "P90",
}[key] || key);

describe("climatologyPaint", () => {
  it("paints a rose and keeps kind climatology in the popup", () => {
    const svg = roseSvg({
      wind_direction_from_deg: 55,
      wind_speed_knots: 16,
      directions_from: [{ dir_deg: 45, pct: 40 }],
    });
    assert.match(svg, /<svg/);
    const html = layerPopupHtml("wind", {
      month: 6,
      wind_speed_knots: 16,
      wind_direction_from_deg: 55,
      vector_mean_knots: 14,
      vector_mean_from_deg: 60,
      directions_from: [{ dir_deg: 45, pct: 40 }],
      calm_pct: 4,
      gale_pct: 1,
      sample_count: 200,
    }, t);
    assert.match(html, /kind: climatology/);
    assert.match(html, /data-testid="climatology-popup"/);
    assert.doesNotMatch(html, /forecast|GRIB/i);
  });

  it("uses distinct P50 / P90 colours", () => {
    assert.notEqual(waveColor(2.8, "p90"), waveColor(2.8, "p50"));
    const point = pointPopupHtml({
      kind: "climatology",
      month: 6,
      wind_atlas: { most_likely: { speed_knots: 16, dir_deg: 55 } },
      wave: { hs_p50_m: 1.4, hs_p90_m: 2.8 },
      current: { speed_knots: 0.4 },
    }, t);
    assert.match(point, /Hs P50 1.4/);
    assert.match(point, /Hs P90 2.8/);
    assert.match(point, /kind: climatology/);
  });
});
