// Lot R8a — modèle build_moment (serveur). Aucun changement visible.
// Sans API : barre film, Suivre / Simulation / Tracer tiennent seuls.
// GET /voyage/official : sondé ; s'il manque, annotation seulement.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-r8a/${name}.jpg`,
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

test("lot R8a — aucun changement visible, trois parcours", async ({ page }) => {
  test.setTimeout(90_000);
  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions d'horloge officielle non jouées",
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
});
