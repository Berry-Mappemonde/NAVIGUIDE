// Popup de climatologie : phrase lisible, jamais « kind: ».
// Tuiles et point d'atlas factices — aucun appel Nebius ni Tavily.
import { expect, test } from "@playwright/test";
import { dismissNotForNav } from "../helpers.js";

const POINT = {
  kind: "climatology",
  month: 5,
  wind_atlas: { most_likely: { speed_knots: 14, dir_deg: 60 } },
  coordinates: { cell_selection: "fixture" },
};

const TILE = {
  type: "FeatureCollection",
  features: [{
    type: "Feature",
    geometry: { type: "Point", coordinates: [-40, 20] },
    properties: {
      speed_knots: 14,
      dir_from_deg: 60,
      wind_speed_knots: 14,
      wind_direction_from_deg: 60,
      month: 5,
    },
  }],
};

test("popup climatologie sans « kind: »", async ({ page }) => {
  await page.route("**/climatology/wind/tiles/**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(TILE) });
  });
  await page.route("**/climatology/point**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(POINT) });
  });
  await page.route("**/climatology/wind.geojson**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(TILE) });
  });

  await page.goto("/?climo=wind&map=20,-40,3&month=5");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("scene-load-mask").waitFor({ state: "hidden", timeout: 25_000 }).catch(() => {});

  await expect.poll(async () => page.evaluate(() => {
    const map = window.__naviguideScene?.map;
    if (!map) return "no-map";
    const latlng = map.getCenter();
    map.fire("click", { latlng });
    return document.querySelector("[data-testid='climatology-map-popup']") ? "open" : "waiting";
  }), { timeout: 15_000 }).toBe("open");

  const popup = page.getByTestId("climatology-map-popup");
  await expect(popup).toBeVisible();
  const text = await popup.innerText();
  expect(text).not.toMatch(/kind:/);
  expect(text).toMatch(/Climatologie — moyenne mensuelle \(mai\), pas une prévision|Climatology — monthly average \(May\), not a forecast/);
  const size = await page.getByTestId("climatology-caption").first().evaluate((el) => (
    Number.parseFloat(getComputedStyle(el).fontSize)
  ));
  expect(size).toBeGreaterThanOrEqual(12);
});
