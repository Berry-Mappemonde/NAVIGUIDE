// Lot RE1 — accueil Simulation + Cinéma + monde dézoomé ;
// Suivre → Simulation décoche le Cinéma et ouvre les deux panneaux.
// Sans API : montage (Simulation, Cinéma, zoom monde, panneaux fermés)
// et la bascule tiennent seuls.
// GET /voyage/official sondé ; s'il manque, annotation + saut des seules
// assertions qui en dépendent (recadrage caméra sur le bateau en Suivre)
// — jamais le mode initial, ni le Cinéma, ni l'ouverture des panneaux.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-re1");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`),
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

function cinemaButton(page) {
  return page.getByRole("button", { name: /^(cinéma|cinema)$/i });
}

async function cinemaPressed(page) {
  return /bg-cyan-700/.test((await cinemaButton(page).getAttribute("class")) || "");
}

function panelOnScreen(page, side) {
  const sel = side === "left"
    ? ".naviguide-sidebar-panel.left-0"
    : ".naviguide-sidebar-panel.right-0";
  return page.locator(sel).first().evaluate((el) => {
    const s = getComputedStyle(el);
    if (s.visibility === "hidden" || s.display === "none" || Number(s.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 50 && r.right > 12 && r.left < window.innerWidth - 12;
  });
}

async function mapZoom(page) {
  return page.evaluate(() => window.__naviguideScene?.map?.getZoom?.() ?? null);
}

async function probeOfficial(request) {
  const official = await request.get("/voyage/official", { timeout: 4000 }).catch(() => null);
  if (!official || !official.ok()) return null;
  const ct = official.headers()["content-type"] || "";
  if (!ct.includes("json")) return null;
  const body = await official.json().catch(() => null);
  return body && typeof body === "object" ? body : null;
}

test("lot RE1 — accueil Simulation cinéma monde ; Suivre → Simulation ouvre les panneaux", async ({ page, request }) => {
  test.setTimeout(90_000);
  const officialBody = await probeOfficial(request);
  const apiUp = Boolean(officialBody);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — recadrage caméra Suivre sauté",
    });
  }

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("scene-load-mask").waitFor({ state: "hidden", timeout: 25_000 }).catch(() => {});

  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "false");
  await expect(cinemaButton(page)).toBeVisible();
  expect(await cinemaPressed(page), "Cinéma enfoncé au chargement").toBe(true);
  await expect.poll(() => panelOnScreen(page, "left"), { timeout: 8_000 }).toBe(false);
  await expect.poll(() => panelOnScreen(page, "right"), { timeout: 8_000 }).toBe(false);

  const mapReady = await page.waitForFunction(() => window.__naviguideScene?.map, null, { timeout: 20_000 })
    .then(() => true)
    .catch(() => false);
  if (mapReady) {
    const zoom0 = await mapZoom(page);
    expect(zoom0, "carte initiale monde dézoomée").toBeGreaterThanOrEqual(2);
    expect(zoom0, "carte initiale monde dézoomée").toBeLessThanOrEqual(2.25);
  }

  await shot(page, "01-accueil");

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  expect(await cinemaPressed(page), "entrée en Suivre : Cinéma reste enfoncé").toBe(true);
  await expect.poll(() => panelOnScreen(page, "left"), { timeout: 8_000 }).toBe(false);
  await expect.poll(() => panelOnScreen(page, "right"), { timeout: 8_000 }).toBe(false);

  if (apiUp && mapReady) {
    await expect.poll(async () => {
      const z = await mapZoom(page);
      return Number.isFinite(z) ? z : 0;
    }, { timeout: 15_000 }).toBeGreaterThan(3);
  }

  await page.getByTestId("view-simulation").click();
  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
  await expect.poll(async () => cinemaPressed(page), { timeout: 8_000 }).toBe(false);
  await expect.poll(() => panelOnScreen(page, "left"), { timeout: 10_000 }).toBe(true);
  await expect.poll(() => panelOnScreen(page, "right"), { timeout: 10_000 }).toBe(true);
  await expect(page.getByTestId("ici-maintenant")).toBeVisible({ timeout: 8_000 });

  await shot(page, "02-bascule");
});
