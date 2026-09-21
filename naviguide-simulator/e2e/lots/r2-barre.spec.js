// Lot R2 — barre film : une rangée, Masquer partout, Escale précédente.
// Sans API : hauteur, légende en info-bulle, Masquer, prev-stop grisé tiennent seuls.
// Aller-retour d'escale : joue si « Prochaine escale » est actif (repli route interne).
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-r2/${name}.jpg`,
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

async function dismissNotForNav(page) {
  const ok = page.getByRole("button", { name: /compris|j.ai compris|ok|continuer|accepter/i }).first();
  if (await ok.isVisible({ timeout: 3000 }).catch(() => false)) {
    const ack = page.getByTestId("not-for-nav-ack");
    if (await ack.isVisible().catch(() => false)) await ack.check();
    await ok.click();
  }
}

async function leaveCinema(page) {
  const cinema = page.getByRole("button", { name: /^(cinéma|cinema)$/i });
  const isOn = async () => /bg-cyan-700/.test((await cinema.getAttribute("class")) || "");
  if (!(await isOn())) return;
  await page.keyboard.press("Escape");
  if (!(await isOn())) return;
  await cinema.click();
  if (!(await isOn())) return;
  await cinema.click();
}

test("lot R2 — une rangée, Masquer partout, Escale précédente", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  const bar = page.getByTestId("film-bar");
  await expect(bar).toBeVisible();
  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");

  await expect(bar.locator("[data-testid='regime-legend'] .w-2.h-2")).toHaveCount(0);
  const height = await bar.evaluate((el) => el.getBoundingClientRect().height);
  expect(height, `hauteur barre = ${height}px`).toBeLessThanOrEqual(96);

  const hide = page.getByTestId("hide-film-bar");
  await expect(hide).toBeVisible();
  await expect(hide).toHaveText(/Masquer la barre|Hide the bar/);

  const pill = page.getByTestId("speed-regime-pill");
  const legend = page.getByTestId("regime-legend");
  await expect(pill).toBeVisible();
  await expect(legend).toBeVisible();
  const tip = await legend.getAttribute("title");
  expect(tip, `title pilule : ${tip}`).toMatch(/hindcast/i);
  expect(tip).toMatch(/prévision|forecast/i);
  expect(tip).toMatch(/climatolog/i);
  expect(tip).toMatch(/10/);

  const prev = page.getByTestId("prev-stop");
  const next = bar.getByRole("button", { name: /prochaine escale|go to next stop/i });
  await expect(prev).toBeVisible();
  await expect(next).toBeVisible();
  await expect(prev).toHaveText(/Escale précédente|Previous stop/);
  await expect(prev).toBeDisabled();
  await expect(prev).toHaveClass(/disabled:opacity-30/);

  const prevBox = await prev.boundingBox();
  const nextBox = await next.boundingBox();
  expect(prevBox && nextBox, "les deux boutons d'escale ont une boîte").toBeTruthy();
  expect(prevBox.x).toBeLessThan(nextBox.x);

  await shot(page, "01-simulation");

  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);
  if (await next.isEnabled()) {
    await next.click();
    await expect(prev).toBeEnabled({ timeout: 10_000 });
    await prev.click();
    await expect(prev).toBeDisabled({ timeout: 10_000 });
  } else if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "Prochaine escale inactive — aller-retour d'escale non vérifié",
    });
  }

  await hide.click();
  await expect(page.getByTestId("film-bar")).toHaveCount(0);
  const show = page.getByTestId("show-film-bar");
  await expect(show).toBeVisible();
  await show.click();
  await expect(page.getByTestId("film-bar")).toBeVisible();
  await expect(page.getByTestId("hide-film-bar")).toBeVisible();

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await leaveCinema(page);
  await expect(page.getByTestId("hide-film-bar")).toBeVisible();
  await expect(page.getByTestId("film-bar").locator("[data-testid='regime-legend'] .w-2.h-2")).toHaveCount(0);
  await shot(page, "02-suivre");
});
