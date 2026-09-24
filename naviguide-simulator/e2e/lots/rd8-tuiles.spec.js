// Lot RD8 — couches climato en tuiles XYZ : plus de wind.geojson globe.
// Sans API : la pastille Vent et les requêtes /tiles/ (même en échec)
// tiennent seuls. GET /voyage/official sondé ; s'il manque, annotation
// + saut des seules assertions qui en dépendent — jamais l'absence de
// wind.geojson ni la forme des URLs tuiles.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-rd8/${name}.jpg`,
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

const TILE_RE = /\/climatology\/wind\/tiles\/\d+\/\d+\/\d+\.json/;

async function dismissNotForNav(page) {
  const ok = page.getByRole("button", { name: /compris|j.ai compris|ok|continuer|accepter|understand|accept/i }).first();
  if (await ok.isVisible({ timeout: 3000 }).catch(() => false)) {
    const ack = page.getByTestId("not-for-nav-ack");
    if (await ack.isVisible().catch(() => false)) await ack.check();
    await ok.click();
  }
}

async function leaveCinema(page) {
  const cinema = page.getByRole("button", { name: /^(cinéma|cinema)$/i });
  if (!(await cinema.isVisible().catch(() => false))) return;
  const on = /bg-cyan-700/.test((await cinema.getAttribute("class")) || "");
  if (on) await cinema.click();
}

function rightPanelOpen(page) {
  return page.locator(".naviguide-sidebar-panel.right-0").first().evaluate((el) => (
    !el.className.includes("translate-x-full")
  ));
}

async function showToolsPanel(page) {
  await leaveCinema(page);
  if (await rightPanelOpen(page).catch(() => false)) return;
  const toggle = page.locator(".naviguide-sidebar-toggle--right");
  if (await toggle.isVisible().catch(() => false)) await toggle.click();
  await expect.poll(() => rightPanelOpen(page), { timeout: 10_000 }).toBe(true);
}

async function turnOnWind(page) {
  await showToolsPanel(page);
  const drawer = page.getByTestId("layers-drawer");
  await drawer.locator("summary").scrollIntoViewIfNeeded();
  if (!(await drawer.evaluate((el) => el.open))) await drawer.locator("summary").click();
  const wind = page.getByTestId("layer-climo-wind");
  await wind.scrollIntoViewIfNeeded();
  if ((await wind.getAttribute("aria-pressed")) !== "true") await wind.click();
  await expect(wind).toHaveAttribute("aria-pressed", "true");
}

test("lot RD8 — tuiles vent, plus de wind.geojson", async ({ page }) => {
  test.setTimeout(90_000);
  const official = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  const apiUp = Boolean(official && official.ok());
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — flèches / nouvelles tuiles après glisser sautées si l'atlas ne répond pas",
    });
  }

  const tileUrls = [];
  const geojsonUrls = [];
  page.on("request", (req) => {
    const u = req.url();
    if (TILE_RE.test(u)) tileUrls.push(u);
    if (u.includes("wind.geojson")) geojsonUrls.push(u);
  });

  await page.goto("/?climo=wind&map=45.5,-3.2,6");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("scene-load-mask").waitFor({ state: "hidden", timeout: 25_000 }).catch(() => {});
  await leaveCinema(page);
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await turnOnWind(page);

  await expect.poll(() => tileUrls.length, { timeout: 15_000 }).toBeGreaterThan(0);
  expect(geojsonUrls, "aucune wind.geojson").toEqual([]);
  expect(tileUrls.every((u) => TILE_RE.test(u) && !u.includes("wind.geojson"))).toBe(true);

  const atlas = await page.request.get("/bi/climatology/wind/tiles/4/8/5.json?month=5", { timeout: 8000 })
    .then((r) => r.ok())
    .catch(() => false);
  if (await rightPanelOpen(page).catch(() => false)) {
    await page.locator(".naviguide-sidebar-toggle--right").click();
    await expect.poll(() => rightPanelOpen(page), { timeout: 8_000 }).toBe(false);
  }
  await page.locator(".leaflet-container").first().waitFor({ timeout: 10_000 }).catch(() => {});
  await page.addStyleTag({ content: '[data-testid="scene-load-mask"]{display:none!important}' });

  if (atlas) {
    await expect.poll(async () => page.locator(".bi-climo-rose").count(), { timeout: 15_000 }).toBeGreaterThan(0);
  } else {
    test.info().annotations.push({
      type: "sans API",
      description: "atlas tuiles absent — flèches dessinées non exigées",
    });
  }
  await shot(page, "01-dense");

  const keysBefore = new Set(tileUrls.map((u) => (u.match(/tiles\/\d+\/\d+\/\d+/) || [])[0]).filter(Boolean));
  await page.evaluate(() => {
    const scene = window.__naviguideScene;
    if (scene) scene.userNavigated = true;
    const map = scene?.map;
    if (map) map.setView([45.5, -28], map.getZoom(), { animate: false });
  });
  await expect.poll(() => {
    const keys = new Set(tileUrls.map((u) => (u.match(/tiles\/\d+\/\d+\/\d+/) || [])[0]).filter(Boolean));
    return [...keys].some((k) => !keysBefore.has(k));
  }, { timeout: 12_000 }).toBe(true);
  expect(geojsonUrls).toEqual([]);

  if (atlas) {
    await expect.poll(async () => page.locator(".bi-climo-rose").count(), { timeout: 10_000 }).toBeGreaterThan(0);
  }
  await shot(page, "02-reseau");
});
