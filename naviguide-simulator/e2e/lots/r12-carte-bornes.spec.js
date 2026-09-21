// Lot R12 — carte bornée aux pôles, longitude libre, zoom molette.
// Sans API : les assertions carte tiennent seules (maxBounds Leaflet).
// GET /voyage/official : sondé ; s'il manque, annotation seulement.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-r12/${name}.jpg`,
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

async function dismissNotForNav(page) {
  const ok = page.getByRole("button", { name: /compris|j.ai compris|ok|continuer|accepter|understand|accept/i }).first();
  if (await ok.isVisible({ timeout: 3000 }).catch(() => false)) {
    const ack = page.getByTestId("not-for-nav-ack");
    if (await ack.isVisible().catch(() => false)) await ack.check();
    await ok.click();
  }
}

test("lot R12 — pôles bornés, longitude libre, zoom molette", async ({ page }) => {
  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions carte inchangées",
    });
  }

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await page.waitForFunction(() => Boolean(window.__naviguideScene?.map), { timeout: 30_000 });

  const options = await page.evaluate(() => {
    const map = window.__naviguideScene.map;
    const b = map.options.maxBounds;
    const south = b.getSouth ? b.getSouth() : b[0][0];
    const north = b.getNorth ? b.getNorth() : b[1][0];
    const west = b.getWest ? b.getWest() : b[0][1];
    const east = b.getEast ? b.getEast() : b[1][1];
    return {
      viscosity: map.options.maxBoundsViscosity,
      south,
      north,
      westFinite: Number.isFinite(west),
      eastFinite: Number.isFinite(east),
    };
  });
  expect(options.viscosity).toBe(1);
  expect(options.south).toBe(-85);
  expect(options.north).toBe(85);
  expect(options.westFinite, "longitude ouest non bornée").toBe(false);
  expect(options.eastFinite, "longitude est non bornée").toBe(false);

  const northEdge = await page.evaluate(() => {
    const map = window.__naviguideScene.map;
    map.setView([89, 5], 3, { animate: false });
    const bounds = map.getBounds();
    const c = map.getCenter();
    return { lat: c.lat, north: bounds.getNorth(), south: bounds.getSouth() };
  });
  expect(northEdge.north, `bord nord ${northEdge.north}`).toBeLessThanOrEqual(85.05);
  expect(northEdge.lat, `centre ${northEdge.lat}`).toBeLessThanOrEqual(85);

  const box = await page.locator(".leaflet-container").boundingBox();
  expect(box).toBeTruthy();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2 + 280, { steps: 12 });
  await page.mouse.up();
  const afterDrag = await page.evaluate(() => {
    const bounds = window.__naviguideScene.map.getBounds();
    return { north: bounds.getNorth(), lat: window.__naviguideScene.map.getCenter().lat };
  });
  expect(afterDrag.north, `drag nord ${afterDrag.north}`).toBeLessThanOrEqual(85.05);

  await page.waitForFunction(() => document.querySelectorAll(".leaflet-tile-loaded").length > 2, { timeout: 15_000 });
  const tilesInView = await page.evaluate(() => {
    const container = document.querySelector(".leaflet-container");
    const cr = container.getBoundingClientRect();
    return [...document.querySelectorAll(".leaflet-tile-loaded")].filter((t) => {
      const r = t.getBoundingClientRect();
      return r.bottom > cr.top && r.top < cr.bottom && r.right > cr.left && r.left < cr.right;
    }).length;
  });
  expect(tilesInView, "tuiles visibles au bord nord — pas un écran vide").toBeGreaterThan(2);

  await page.keyboard.press("Escape");
  const closeCard = page.getByRole("button", { name: /fermer|close/i }).first();
  if (await closeCard.isVisible({ timeout: 800 }).catch(() => false)) await closeCard.click();

  await shot(page, "01-bord-nord");

  const farEast = await page.evaluate(() => {
    const map = window.__naviguideScene.map;
    map.setView([0, 250], 3, { animate: false });
    return map.getCenter().lng;
  });
  expect(farEast, "longitude libre au-delà de 180°").toBeGreaterThan(180);

  await page.evaluate(() => {
    window.__naviguideScene.map.setView([20, -40], 3, { animate: false });
  });
  await page.waitForTimeout(300);
  const z0 = await page.evaluate(() => window.__naviguideScene.map.getZoom());
  await page.locator(".leaflet-container").hover();
  await page.mouse.wheel(0, -180);
  await expect.poll(async () => page.evaluate(() => window.__naviguideScene.map.getZoom()), { timeout: 2000 })
    .toBeGreaterThan(z0);
});
