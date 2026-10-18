// ↶ pendant le calcul d'une jambe (/route lent, 1,5 s) : la page reste affichée,
// la console reste propre, la réponse tardive est ignorée, aucun trou de jambe.
import { expect, test } from "@playwright/test";
import { dismissNotForNav, enterTracer } from "../helpers.js";

const ROUTE_DELAY_MS = 1500;
const A = { lat: 46.0, lon: -2.5, name: "A" };
const B = { lat: 44.5, lon: -4.0, name: "B" };
const C = { lat: 43.8, lon: -8.5, name: "C" };
const D = { lat: 42.0, lon: -10.0, name: "D" };

async function slowRoute(page) {
  await page.route("**/route?*", async (route) => {
    const url = new URL(route.request().url());
    const slat = Number(url.searchParams.get("start_lat"));
    const slon = Number(url.searchParams.get("start_lon"));
    const elat = Number(url.searchParams.get("end_lat"));
    const elon = Number(url.searchParams.get("end_lon"));
    await new Promise((resolve) => setTimeout(resolve, ROUTE_DELAY_MS));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        type: "Feature",
        geometry: { type: "LineString", coordinates: [[slon, slat], [(slon + elon) / 2, (slat + elat) / 2], [elon, elat]] },
        properties: { length: 185.2, units: "km" },
      }),
    }).catch(() => {});
  });
}

function drawn(page) {
  return page.evaluate(() => {
    const d = window.__naviguideDrawn || { points: [], segments: [] };
    return {
      names: d.points.map((p) => p.name),
      legs: d.segments.map((s) => (s ? `${s.from?.name}-${s.to?.name}` : null)),
    };
  });
}

async function add(page, p) {
  await page.evaluate((q) => { window.__naviguideAddDrawnPoint(q.lat, q.lon, { name: q.name }); }, p);
}

test("↶ pendant le calcul d'une jambe ne vide pas la page", async ({ page }) => {
  test.setTimeout(90_000);
  const pageErrors = [];
  const consoleErrors = [];
  page.on("pageerror", (err) => pageErrors.push(String(err)));
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    // Tuiles ou ressources hors ligne : bruit réseau, pas une erreur de l'application.
    if (/Failed to load resource/i.test(text)) return;
    consoleErrors.push(text);
  });
  await slowRoute(page);
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await enterTracer(page);
  await page.waitForFunction(() => typeof window.__naviguideAddDrawnPoint === "function");
  // Le ↶ du cadre de tracé (la pilule du haut porte le même titre).
  const undo = page.getByTitle(/Annuler le dernier point|Undo last point/).filter({ hasText: "↶" });

  // 1) ↶ pendant la toute première jambe.
  await add(page, A);
  await add(page, B);
  await page.waitForTimeout(300);
  await undo.click();
  expect(await drawn(page)).toEqual({ names: ["A"], legs: [] });

  // 2) Deux jambes posées, ↶ pendant la deuxième, puis un nouveau point.
  await add(page, B);
  await page.waitForFunction(() => window.__naviguideDrawn?.segments?.length === 1, null, { timeout: 15_000 });
  await add(page, C);
  await page.waitForTimeout(300);
  await undo.click();
  expect(await drawn(page)).toEqual({ names: ["A", "B"], legs: ["A-B"] });
  // La réponse tardive B→C arrive : elle est ignorée.
  await page.waitForTimeout(ROUTE_DELAY_MS + 500);
  expect(await drawn(page)).toEqual({ names: ["A", "B"], legs: ["A-B"] });

  await add(page, D);
  await page.waitForFunction(() => window.__naviguideDrawn?.segments?.length === 2, null, { timeout: 15_000 });
  expect(await drawn(page)).toEqual({ names: ["A", "B", "D"], legs: ["A-B", "B-D"] });

  // 3) Rétablir après un ↶ pendant le calcul recalcule la jambe.
  await add(page, C);
  await page.waitForTimeout(300);
  await undo.click();
  await page.getByTitle(/^(Rétablir|Redo)$/).click();
  await page.waitForFunction(() => window.__naviguideDrawn?.segments?.length === 3, null, { timeout: 15_000 });
  expect(await drawn(page)).toEqual({ names: ["A", "B", "D", "C"], legs: ["A-B", "B-D", "D-C"] });

  await expect(page.getByTestId("film-bar")).toBeVisible();
  await expect(page.getByTestId("drawing-box")).toBeVisible();
  expect(pageErrors, pageErrors.join("\n")).toEqual([]);
  expect(consoleErrors, consoleErrors.join("\n")).toEqual([]);
});

test("↶ puis D aussitôt : la jambe B-C n'apparaît jamais", async ({ page }) => {
  test.setTimeout(90_000);
  await slowRoute(page);
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await enterTracer(page);
  await page.waitForFunction(() => typeof window.__naviguideAddDrawnPoint === "function");
  const undo = page.getByTitle(/Annuler le dernier point|Undo last point/).filter({ hasText: "↶" });
  // Toutes les jambes vues pendant le test, image par image.
  await page.evaluate(() => {
    window.__seenLegs = new Set();
    const tick = () => {
      for (const s of window.__naviguideDrawn?.segments || []) {
        if (s) window.__seenLegs.add(`${s.from?.name}-${s.to?.name}`);
      }
      window.__seenLegsRaf = requestAnimationFrame(tick);
    };
    tick();
  });
  await add(page, A);
  await add(page, B);
  await page.waitForFunction(() => window.__naviguideDrawn?.segments?.length === 1, null, { timeout: 15_000 });
  await add(page, C);
  await page.waitForTimeout(300);
  await undo.click();
  await add(page, D);
  await page.waitForFunction(() => window.__naviguideDrawn?.segments?.length === 2, null, { timeout: 15_000 });
  // La réponse tardive B→C est passée : toujours pas de B-C.
  await page.waitForTimeout(ROUTE_DELAY_MS + 500);
  expect(await drawn(page)).toEqual({ names: ["A", "B", "D"], legs: ["A-B", "B-D"] });
  const seen = await page.evaluate(() => [...window.__seenLegs]);
  expect(seen).not.toContain("B-C");
  expect(seen).toContain("B-D");
});
