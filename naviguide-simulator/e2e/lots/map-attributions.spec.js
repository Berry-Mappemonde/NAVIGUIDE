// Crédits des tuiles : OpenStreetMap reste affiché, OpenSeaMap seulement
// tant que le calque est actif. Les serveurs de tuiles sont simulés.
import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema } from "../helpers.js";

const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "base64",
);

const TILE_URL = /arcgisonline\.com|openseamap\.org|emodnet|geoserver|\/proxy\/seamark\/|\/proxy\/zee\/wms/i;

async function panelClosed(page, side) {
  const loc = side === "left"
    ? page.locator(".naviguide-sidebar-panel.left-0").first()
    : page.locator(".naviguide-sidebar-panel.right-0").first();
  return loc.evaluate((el) => el.className.includes("translate-x-full"));
}

async function setTools(page, open) {
  if (await panelClosed(page, "right") !== !open) {
    await page.locator(".naviguide-sidebar-toggle--right").click();
  }
  await expect.poll(() => panelClosed(page, "right"), { timeout: 10_000 }).toBe(!open);
}

function creditLayout(page, needle) {
  return page.evaluate((needle) => {
    const attr = document.querySelector(".leaflet-control-attribution");
    const zoom = document.querySelector(".leaflet-bottom.leaflet-right .leaflet-control-zoom");
    if (!attr) return { ok: false, reason: "contrôle absent" };
    const walker = document.createTreeWalker(attr, NodeFilter.SHOW_TEXT);
    let node = null;
    let found = null;
    while ((node = walker.nextNode())) {
      const text = node.textContent || "";
      const at = text.indexOf(needle);
      if (at < 0) continue;
      const range = document.createRange();
      range.setStart(node, at);
      range.setEnd(node, at + needle.length);
      found = range;
      break;
    }
    if (!found) return { ok: false, reason: "texte absent", text: attr.textContent || "" };
    const rects = [...found.getClientRects()];
    const box = attr.getBoundingClientRect();
    const z = zoom?.getBoundingClientRect();
    const overlaps = (r) => Boolean(
      z && r.right > z.left + 1 && r.left < z.right - 1 && r.bottom > z.top + 1 && r.top < z.bottom - 1,
    );
    const onScreen = rects.length > 0 && rects.every((r) => (
      r.width > 0.5 && r.height > 0.5
      && r.left >= -1 && r.top >= -1
      && r.right <= window.innerWidth + 1
      && r.bottom <= window.innerHeight + 1
      && r.left >= box.left - 1 && r.right <= box.right + 1
      && r.top >= box.top - 1 && r.bottom <= box.bottom + 1
      && !overlaps(r)
    ));
    return {
      ok: onScreen,
      reason: onScreen ? "ok" : "hors cadre ou sous le zoom",
      n: rects.length,
      text: (attr.textContent || "").replace(/\s+/g, " ").trim(),
    };
  }, needle);
}

test("OpenSeaMap s'affiche avec le calque, OpenStreetMap reste", async ({ page }) => {
  test.setTimeout(60_000);
  await page.route(TILE_URL, (route) => route.fulfill({
    status: 200,
    contentType: "image/png",
    body: PNG,
  }));

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await page.waitForFunction(() => Boolean(window.__naviguideScene?.map), null, { timeout: 30_000 });
  await leaveCinema(page);

  const attr = page.locator(".leaflet-control-attribution");
  const osm = attr.locator('a[href="https://www.openstreetmap.org/copyright"]');
  await expect(osm).toBeVisible();
  await expect(osm).toHaveText("OpenStreetMap contributors");
  await expect.poll(() => creditLayout(page, "OpenStreetMap contributors")).toMatchObject({ ok: true });

  await setTools(page, true);
  const drawer = page.getByTestId("layers-drawer");
  const balisage = page.getByTestId("layer-balisage");
  if (!(await balisage.isVisible().catch(() => false))) {
    await drawer.locator("summary").click();
  }
  await expect(balisage).toBeVisible();
  await balisage.click();
  const modal = page.getByTestId("not-for-nav-modal");
  if (await modal.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await page.getByTestId("not-for-nav-ack").check();
    await page.getByTestId("not-for-nav-accept").click();
  }
  await expect(balisage).toHaveAttribute("aria-pressed", "true");
  await setTools(page, false);

  await expect(attr).toContainText("© OpenSeaMap contributors");
  await expect.poll(() => creditLayout(page, "© OpenSeaMap contributors")).toMatchObject({ ok: true });
  await expect.poll(() => creditLayout(page, "OpenStreetMap contributors")).toMatchObject({ ok: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await expect.poll(() => creditLayout(page, "© OpenSeaMap contributors")).toMatchObject({ ok: true });
  await expect.poll(() => creditLayout(page, "OpenStreetMap contributors")).toMatchObject({ ok: true });

  await page.setViewportSize({ width: 1280, height: 800 });
  await setTools(page, true);
  await balisage.click();
  await expect(balisage).toHaveAttribute("aria-pressed", "false");
  await setTools(page, false);

  await expect(attr).not.toContainText("OpenSeaMap");
  await expect(osm).toBeVisible();
  await expect.poll(() => creditLayout(page, "OpenStreetMap contributors")).toMatchObject({ ok: true });
});
