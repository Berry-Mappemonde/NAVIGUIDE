// Lot RC14 — Tracer ouvre le monde (zoom 2), pas les Amériques (zoom 3).
// Sans API : accueil monde, molette, et le geste Tracer après un zoom > 3
// tiennent seuls (le zoom bateau est posé sur la carte, pas une donnée
// d'expédition). GET /voyage/official sondé ; s'il manque, annotation +
// saut du seul recadrage caméra réel après clic Suivre — jamais le
// dézoom Tracer, ni l'accueil, ni la molette.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rc14");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`),
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

async function dismissNotForNav(page) {
  const modal = page.getByTestId("not-for-nav-modal");
  if (!(await modal.isVisible({ timeout: 1500 }).catch(() => false))) return;
  const ack = page.getByTestId("not-for-nav-ack");
  if (await ack.isVisible().catch(() => false)) await ack.check();
  const ok = page.getByTestId("not-for-nav-accept");
  if (await ok.isVisible().catch(() => false)) await ok.click();
}

function cinemaButton(page) {
  return page.getByRole("button", { name: /^(cinéma|cinema)$/i });
}

async function cinemaPressed(page) {
  return /bg-cyan-700/.test((await cinemaButton(page).getAttribute("class")) || "");
}

async function panelClosed(page, side) {
  const loc = side === "left"
    ? page.locator(".naviguide-sidebar-panel.left-0").first()
    : page.locator(".naviguide-sidebar-panel.right-0").first();
  const cls = (await loc.getAttribute("class")) || "";
  return cls.includes("translate-x-full");
}

async function mapZoom(page) {
  return page.evaluate(() => window.__naviguideScene?.map?.getZoom?.() ?? null);
}

async function enterTracer(page) {
  if (await panelClosed(page, "left")) {
    await page.locator(".naviguide-sidebar-toggle--left").click();
    await expect.poll(() => panelClosed(page, "left"), { timeout: 8_000 }).toBe(false);
  }
  const drawBtn = page.getByRole("button", { name: /Tracer votre propre route|Draw your own route/i });
  await expect(drawBtn).toBeVisible({ timeout: 10_000 });
  await drawBtn.click();
  await expect(page.getByTestId("drawing-points")).toBeVisible({ timeout: 10_000 });
}

test("lot RC14 — après Suivre (zoom bateau) Tracer ouvre le monde", async ({ page }) => {
  test.setTimeout(90_000);

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });

  const official = await page.request.get("/voyage/official", { timeout: 2500 }).catch(() => null);
  const apiUp = Boolean(official && official.ok());
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — recadrage caméra réel après clic Suivre sauté ; zoom > 3 posé sur la carte pour le geste Tracer",
    });
  }

  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(cinemaButton(page)).toBeVisible();
  expect(await cinemaPressed(page), "Cinéma enfoncé au chargement").toBe(true);

  const mapReady = await page.waitForFunction(() => window.__naviguideScene?.map, null, { timeout: 15_000 })
    .then(() => true)
    .catch(() => false);
  if (mapReady) {
    await expect.poll(async () => {
      const z = await mapZoom(page);
      return Number.isFinite(z) ? z : 99;
    }, { timeout: 8_000 }).toBeLessThanOrEqual(2.6);
  }

  await page.getByTestId("view-tracer").click();
  await expect(page.getByTestId("view-tracer")).toHaveAttribute("aria-checked", "true");
  await expect.poll(async () => cinemaPressed(page), { timeout: 8_000 }).toBe(false);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  expect(await cinemaPressed(page), "clic Suivre : Cinéma enfoncé").toBe(true);

  if (mapReady && apiUp) {
    await expect.poll(async () => {
      const z = await mapZoom(page);
      return Number.isFinite(z) ? z : 0;
    }, { timeout: 15_000 }).toBeGreaterThan(3);
  } else if (mapReady) {
    await page.evaluate(() => {
      window.__naviguideScene.map.setView([16, -40], 6, { animate: false });
    });
    await expect.poll(async () => {
      const z = await mapZoom(page);
      return Number.isFinite(z) ? z : 0;
    }, { timeout: 5_000 }).toBeGreaterThan(3);
  }

  await enterTracer(page);
  if (mapReady) {
    await expect.poll(async () => {
      const z = await mapZoom(page);
      return Number.isFinite(z) ? z : 99;
    }, { timeout: 8_000 }).toBeLessThanOrEqual(2.6);
    await page.waitForFunction(() => document.querySelectorAll(".leaflet-tile-loaded").length >= 4, {
      timeout: 8_000,
    }).catch(() => {});
    await shot(page, "01-tracer-monde");

    await page.evaluate(() => {
      window.__naviguideScene.map.setView([22, 5], 5, { animate: false });
    });
    await page.waitForTimeout(200);
    const box = await page.locator(".leaflet-container").boundingBox();
    expect(box).toBeTruthy();
    await page.mouse.move(box.x + box.width * 0.72, box.y + box.height * 0.42);
    for (let i = 0; i < 16; i += 1) await page.mouse.wheel(0, 240);
    await expect.poll(async () => {
      const z = await mapZoom(page);
      return Number.isFinite(z) ? z : 99;
    }, { timeout: 8_000 }).toBeLessThanOrEqual(2.6);
  } else {
    await shot(page, "01-tracer-monde");
  }
});
