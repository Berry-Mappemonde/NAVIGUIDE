// Lot S — route dessinée Brisbane → San Francisco dans le Pacifique.
// Sans API : le spec vérifie le mode Tracer + l'absence de sommet > 50° N
// (repli/dépli client, corde de repli). Avec API (proxy /route → :8010) :
// distance du résumé entre 6 000 et 7 500 nm.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-s/${name}.jpg`,
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

const BRISBANE = { lat: -27.0, lon: 153.4 };
// SF (−122,4) sur la copie-monde +360 : c'est la lon dépliée envoyée avant le lot S.
const SAN_FRANCISCO_UNFOLDED = { lat: 37.7, lon: 237.6 };

async function dismissNotForNav(page) {
  const ok = page.getByRole("button", { name: /compris|j.ai compris|ok|continuer|accepter|understand|accept/i }).first();
  if (await ok.isVisible({ timeout: 3000 }).catch(() => false)) {
    const ack = page.getByTestId("not-for-nav-ack");
    if (await ack.isVisible().catch(() => false)) await ack.check();
    await ok.click();
  }
}

async function clickLatLng(page, lat, lon) {
  // Même chemin que le clic carte (handleDrawingClick → addPoint).
  // map.fire('click') ne transmet pas toujours latlng jusqu'au handler Leaflet.
  await page.waitForFunction(() => typeof window.__naviguideAddDrawnPoint === "function", { timeout: 10_000 });
  await page.evaluate(({ lat, lon }) => {
    window.__naviguideAddDrawnPoint(lat, lon);
  }, { lat, lon });
}

function parseNm(text) {
  const matches = [...String(text || "").matchAll(/(\d[\d\s\u00a0\u202f.,]*)\s*nm/gi)];
  if (!matches.length) return null;
  const raw = matches[matches.length - 1][1].replace(/[\s\u00a0\u202f,]/g, "");
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

test("lot S — Tracer Brisbane → SF : aucun sommet au nord de 50° N", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });
  await page.waitForFunction(() => Boolean(window.__naviguideScene?.map), { timeout: 30_000 });

  const drawBtn = page.getByRole("button", { name: /Berry-Mappemonde.*Tracer votre propre route/i });
  if (!(await drawBtn.isVisible().catch(() => false))) {
    await page.locator(".naviguide-sidebar-toggle--left").click();
  }
  await expect(drawBtn).toBeVisible({ timeout: 15_000 });
  await drawBtn.click();
  await expect(page.getByTestId("drawing-box")).toBeVisible({ timeout: 15_000 });

  const tools = page.getByTestId("drawing-summary");
  if (!(await tools.isVisible().catch(() => false))) {
    await page.locator(".naviguide-sidebar-toggle--right").click();
  }
  await expect(page.getByTestId("drawing-summary")).toBeVisible({ timeout: 10_000 });

  await clickLatLng(page, BRISBANE.lat, BRISBANE.lon);
  await page.waitForFunction(() => (window.__naviguideDrawn?.points?.length || 0) >= 1, { timeout: 10_000 });
  await clickLatLng(page, SAN_FRANCISCO_UNFOLDED.lat, SAN_FRANCISCO_UNFOLDED.lon);
  await page.waitForFunction(() => (window.__naviguideDrawn?.segments?.length || 0) >= 1, { timeout: 90_000 });

  const info = await page.evaluate(() => {
    const drawn = window.__naviguideDrawn || {};
    const sceneSegs = window.__naviguideScene?.routeInputs?.drawnSegments || [];
    const segs = drawn.segments?.length ? drawn.segments : sceneSegs;
    const coords = drawn.coords?.length
      ? drawn.coords
      : segs.flatMap((s) => s.coords || []);
    const lats = coords.map((c) => c[1]).filter((lat) => Number.isFinite(lat));
    const lons = coords.map((c) => c[0]);
    let jump = 0;
    for (let i = 1; i < lons.length; i++) jump = Math.max(jump, Math.abs(lons[i] - lons[i - 1]));
    return {
      n: coords.length,
      maxLat: lats.length ? Math.max(...lats) : null,
      failed: segs.some((s) => s.failed),
      jump,
      points: drawn.points || [],
    };
  });

  expect(info.points.length).toBeGreaterThanOrEqual(2);
  expect(info.points[0].lat).toBeCloseTo(BRISBANE.lat, 1);
  expect(info.points[0].lon).toBeCloseTo(BRISBANE.lon, 1);
  expect(info.points[1].lat).toBeCloseTo(SAN_FRANCISCO_UNFOLDED.lat, 1);
  expect(info.points[1].lon).toBeCloseTo(SAN_FRANCISCO_UNFOLDED.lon, 1);
  expect(info.n).toBeGreaterThanOrEqual(2);
  expect(info.maxLat).not.toBeNull();
  expect(info.maxLat).toBeLessThanOrEqual(50);
  expect(info.jump).toBeLessThanOrEqual(180);

  if (!info.failed) {
    const summary = await page.getByTestId("drawing-summary").innerText();
    const nm = parseNm(summary);
    expect(nm, `résumé: ${summary}`).not.toBeNull();
    expect(nm).toBeGreaterThanOrEqual(6000);
    expect(nm).toBeLessThanOrEqual(7500);
  }

  await page.evaluate(({ a, b }) => {
    const map = window.__naviguideScene?.map;
    if (!map) return;
    map.fitBounds([[a.lat, a.lon], [b.lat, b.lon]], {
      animate: false,
      padding: [56, 56],
      maxZoom: 3,
    });
  }, { a: BRISBANE, b: SAN_FRANCISCO_UNFOLDED });
  await page.waitForTimeout(600);
  await shot(page, "01-pacifique");
});
