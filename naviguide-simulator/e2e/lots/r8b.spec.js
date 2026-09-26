// Lot R8b — endpoint + encadré (pas encore branché). Aucun changement visible
// dans l'app. La page /lot-r8b.html rend le composant seul (fixture).
// Sans API : barre film, Suivre / Simulation / Tracer tiennent seuls.
// GET /voyage/official : sondé ; s'il manque, annotation seulement.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-r8b/${name}.jpg`,
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

test("lot R8b — encadré seul, puis aucun changement visible dans l'app", async ({ page }) => {
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

  await page.goto("/lot-r8b.html");
  await expect(page.getByTestId("ici-maintenant")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("ici-tab-now")).toBeVisible();
  await expect(page.getByTestId("ici-tab-story")).toBeVisible();
  await expect(page.getByTestId("ici-tab-journal")).toBeVisible();
  await expect(page.getByTestId("ici-section-leg")).toBeVisible();
  await expect(page.getByTestId("ici-section-alerts")).toBeVisible();
  await expect(page.getByTestId("ici-section-here")).toBeVisible();
  await expect(page.getByTestId("ici-section-around")).toBeVisible();
  await expect(page.getByTestId("ici-section-sources")).toBeVisible();
  await expect(page.getByText(/Ici et maintenant|Here and now/i)).toHaveCount(0);
  await expect(page.locator("h1, h2")).toHaveCount(0);
  const pills = page.getByTestId("ici-alert");
  const n = await pills.count();
  expect(n).toBeGreaterThanOrEqual(2);
  await expect(page.getByTestId("ici-source-link").first()).toBeVisible();
  await shot(page, "01-encadre");
  await pills.nth(0).getByTestId("ici-alert-close").click();
  await expect(page.getByTestId("ici-alert")).toHaveCount(n - 1);
  await page.getByTestId("ici-tab-story").click();
  await expect(page.getByTestId("ici-story-slot")).toBeVisible();
  await expect(page.getByTestId("ici-section-leg")).toHaveCount(0);
  await page.getByTestId("ici-tab-now").click();
  await expect(page.getByTestId("ici-section-leg")).toBeVisible();

  await page.goto("/lot-r8b.html?light=1");
  await expect(page.getByTestId("ici-maintenant")).toBeVisible({ timeout: 15_000 });
  await expect(page.locator("html")).toHaveClass(/light-mode/);
  await shot(page, "02-encadre-clair");

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("view-suivre")).toBeVisible();
  await expect(page.getByTestId("view-simulation")).toBeVisible();
  await expect(page.getByTestId("ici-maintenant")).toHaveCount(0);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("film-bar")).toBeVisible();
  if (apiUp) {
    await expect(page.getByTestId("film-clock-line")).not.toHaveText(/^\s*$/);
  }
  await shot(page, "03-suivre");

  await page.getByTestId("view-simulation").click();
  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("film-bar")).toBeVisible();
  await expect(page.getByTestId("ici-maintenant")).toHaveCount(0);

  await showLeftPanel(page);
  const draw = page.getByRole("button", { name: /Berry-Mappemonde.*Tracer votre propre route|Draw your own route/i });
  await expect(draw).toBeVisible({ timeout: 15_000 });
  await draw.scrollIntoViewIfNeeded();
  await draw.click({ force: true });
  await expect(page.getByTestId("drawing-box")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("ici-maintenant")).toHaveCount(0);

  expect(errors, `erreurs de page : ${errors.join(" | ")}`).toEqual([]);
});
