// Lot RF1 — plus de 400 /advice au parcours nominal. Sans API : Suivre,
// Simulation, Tracer et l'onglet Revue tiennent seuls. GET /voyage/official
// sondé ; s'il manque, annotation + saut des seules assertions /advice —
// jamais les trois modes ni la revue.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rf1");
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

async function leaveCinema(page) {
  const cinema = page.getByRole("button", { name: /^(cinéma|cinema)$/i });
  if (!(await cinema.isVisible().catch(() => false))) return;
  const on = /bg-cyan-700/.test((await cinema.getAttribute("class")) || "");
  if (on) await cinema.click();
}

async function showLeftPanel(page) {
  await leaveCinema(page);
  const box = page.getByTestId("ici-maintenant");
  if (await box.isVisible().catch(() => false)) return;
  const toggle = page.locator(".naviguide-sidebar-toggle--left");
  if (await toggle.isVisible().catch(() => false)) await toggle.click();
  await expect(box).toBeVisible({ timeout: 15_000 });
}

test("lot RF1 — aucun 4xx/5xx advice, revue comme avant", async ({ page }) => {
  test.setTimeout(90_000);
  const official = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  const apiUp = Boolean(official && official.ok());
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions /advice sautées",
    });
  }

  const adviceStatuses = [];
  page.on("response", (res) => {
    if (res.url().includes("/voyage/official/advice")) adviceStatuses.push(res.status());
  });
  const pageErrors = [];
  page.on("pageerror", (err) => pageErrors.push(String(err)));

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("film-bar")).toBeVisible();
  await showLeftPanel(page);
  const reviewTab = page.getByTestId("ici-tab-review");
  await expect(reviewTab).toBeVisible({ timeout: 10_000 });
  await reviewTab.click();
  await expect(page.getByTestId("ici-review-slot")).toBeVisible();
  await expect(page.getByTestId("plan-review")).toBeVisible();
  await expect(page.getByTestId("plan-review-leg").first()).toBeVisible({ timeout: 10_000 });
  await page.waitForTimeout(4000);

  await page.getByTestId("view-tracer").click();
  await expect(page.getByTestId("view-tracer")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("film-bar")).toBeVisible();
  await showLeftPanel(page);
  await expect(page.getByTestId("ici-tab-review")).toBeVisible();
  await page.getByTestId("ici-tab-review").click();
  await expect(page.getByTestId("plan-review")).toBeVisible();
  await page.waitForTimeout(2000);

  const draw = page.getByRole("button", {
    name: /Berry-Mappemonde.*Tracer votre propre route|Tracer votre propre route|Draw your own route/i,
  });
  await expect(draw).toBeVisible({ timeout: 15_000 });
  await draw.scrollIntoViewIfNeeded();
  // Panneau gauche encore en transition (tranches CI) : le clic DOM ne dépend pas de la géométrie (même repli que enterTracer).
  await draw.click({ force: true, timeout: 5_000 }).catch(() => draw.evaluate((el) => el.click()));
  await expect(page.getByTestId("drawing-box")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("ici-tab-review")).toHaveCount(0);
  await page.waitForTimeout(1500);

  const cancel = page.getByRole("button", { name: /annuler|cancel/i }).first();
  if (await cancel.isVisible().catch(() => false)) await cancel.click();
  await page.getByTestId("view-suivre").click();
  await showLeftPanel(page);
  await page.getByTestId("ici-tab-review").click();
  await expect(page.getByTestId("plan-review")).toBeVisible();

  expect(pageErrors, `erreurs de page : ${pageErrors.join(" | ")}`).toEqual([]);
  await shot(page, "01-console");

  if (!apiUp) return;

  expect(
    adviceStatuses.filter((s) => s >= 400),
    `advice 4xx/5xx : ${adviceStatuses.join(",")}`,
  ).toEqual([]);

  const reviewRes = await page.request.get("/voyage/official/plan-review", { timeout: 12_000 }).catch(() => null);
  if (!reviewRes || !reviewRes.ok()) {
    test.info().annotations.push({
      type: "sans revue",
      description: "GET /plan-review absent — sondes /advice par indice sautées",
    });
    return;
  }
  const review = await reviewRes.json().catch(() => null);
  const n = Array.isArray(review?.legs) ? review.legs.length : 0;
  const adviceRes = await page.request.get("/voyage/official/advice?leg=0&lang=fr", { timeout: 8000 }).catch(() => null);
  expect(adviceRes, "GET /advice a répondu").toBeTruthy();
  expect(adviceRes.status(), "GET /advice jamais 4xx").toBeLessThan(400);
  const body = await adviceRes.json();
  expect(body.status).toMatch(/^(pending|done|unavailable)$/);
  if (n === 0) {
    expect(body.status).toBe("unavailable");
  }
});
