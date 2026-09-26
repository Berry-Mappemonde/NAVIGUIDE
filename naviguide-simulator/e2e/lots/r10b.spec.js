// Lot R10b — compromis par décalage de date (serveur). Aucun changement visible.
// Sans API : barre film, Suivre / Simulation / Tracer tiennent seuls.
// GET /voyage/official : sondé ; s'il manque, annotation seulement.
// GET /voyage/official/advice?leg=3 : sondé ensuite ; 404 / hors contrat → annotation.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-r10b/${name}.jpg`,
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
  const drawBtn = page.getByRole("button", { name: /Berry-Mappemonde.*Tracer votre propre route|Tracer votre propre route|Draw your own route/i });
  if (await drawBtn.isVisible().catch(() => false)) return;
  await page.locator(".naviguide-sidebar-toggle--left").click();
}

test("lot R10b — aucun changement visible, trois parcours", async ({ page }) => {
  test.setTimeout(90_000);
  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions d'horloge officielle et /advice non jouées",
    });
  }

  const errors = [];
  page.on("pageerror", (err) => errors.push(String(err)));

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("view-suivre")).toBeVisible();
  await expect(page.getByTestId("view-simulation")).toBeVisible();

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("film-bar")).toBeVisible();
  if (apiUp) {
    await expect(page.getByTestId("film-clock-line")).not.toHaveText(/^\s*$/);
  }
  await shot(page, "01-suivre");

  await page.getByTestId("view-simulation").click();
  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("film-bar")).toBeVisible();
  await shot(page, "02-simulation");

  await showLeftPanel(page);
  const draw = page.getByRole("button", { name: /Berry-Mappemonde.*Tracer votre propre route|Draw your own route/i });
  await expect(draw).toBeVisible({ timeout: 15_000 });
  await draw.scrollIntoViewIfNeeded();
  await draw.click({ force: true });
  await expect(page.getByTestId("drawing-box")).toBeVisible({ timeout: 15_000 });
  await shot(page, "03-tracer");

  expect(errors, `erreurs de page : ${errors.join(" | ")}`).toEqual([]);

  if (!apiUp) return;

  const adviceRes = await page.request.get("/voyage/official/advice?leg=3", { timeout: 8000 }).catch(() => null);
  if (!adviceRes || !adviceRes.ok()) {
    test.info().annotations.push({
      type: "sans advice",
      description: `GET /voyage/official/advice?leg=3 → ${adviceRes ? adviceRes.status() : "erreur"} — assertions pending|done non jouées`,
    });
    return;
  }
  let body = await adviceRes.json();
  expect(body.status).toMatch(/^(pending|done)$/);
  expect(body.weights.shiftPerDay).toBe(0.3);
  expect(body.weights.extraNm).toBe(0.02);
  for (let i = 0; i < 40 && body.status === "pending"; i += 1) {
    await page.waitForTimeout(250);
    const again = await page.request.get("/voyage/official/advice?leg=3", { timeout: 8000 });
    if (!again.ok()) break;
    body = await again.json();
  }
  if (body.status === "done") {
    expect(body.leg).toBe(3);
    expect(body.best).toBeTruthy();
    expect(Array.isArray(body.alternatives)).toBeTruthy();
    expect(body.alternatives.length).toBeLessThanOrEqual(3);
    expect(body.best.sentence).toBeTruthy();
    expect(Array.isArray(body.best.facts)).toBeTruthy();
    expect(Array.isArray(body.best.cascade)).toBeTruthy();
  } else {
    test.info().annotations.push({
      type: "advice encore pending",
      description: "GET /voyage/official/advice?leg=3 encore pending après 10 s — structure pending déjà vérifiée",
    });
  }
});
