// Lot F5 — film anglais + plein écran (sidebars masquées, pas démontées).
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-f5/${name}.jpg`,
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

async function switchToEnglish(page) {
  const en = page.getByTestId("lang-en");
  await expect(en).toBeVisible({ timeout: 15_000 });
  await en.click();
}

test("lot F5 — sous-titre anglais, plein écran film, Échap rend les sidebars", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  await switchToEnglish(page);
  await expect(page.getByTestId("view-suivre")).toContainText(/Follow/i);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("film-fullscreen")).toBeVisible();

  // Suivre range les panneaux (cinéma). On les rouvre pour que le masquage CSS soit visible.
  const leftToggle = page.locator(".naviguide-sidebar-toggle--left");
  const rightToggle = page.locator(".naviguide-sidebar-toggle--right");
  await expect(leftToggle).toBeVisible({ timeout: 10_000 });
  await leftToggle.click();
  await rightToggle.click();
  const panels = page.locator(".naviguide-sidebar-panel");
  await expect(panels).toHaveCount(2);
  await expect(panels.nth(0)).toBeVisible();
  await expect(panels.nth(1)).toBeVisible();
  await expect(panels.nth(0)).toBeInViewport();
  await expect(panels.nth(1)).toBeInViewport();

  await page.getByTestId("replay-start").click();
  const subtitle = page.getByTestId("film-subtitle");
  await expect(subtitle).toBeVisible({ timeout: 8_000 });
  await expect(subtitle).toContainText("Saint-Maur");
  await expect(subtitle).toContainText("La Rochelle");
  await expect(subtitle).toContainText(/left|departed/i);

  await page.getByTestId("film-fullscreen").click();
  await expect(page.getByTestId("sim-root")).toHaveClass(/film-fullscreen/);
  await expect(panels.nth(0)).toBeHidden();
  await expect(panels.nth(1)).toBeHidden();
  await shot(page, "01-plein-ecran");

  await page.keyboard.press("Escape");
  await expect(page.getByTestId("sim-root")).not.toHaveClass(/film-fullscreen/);
  await expect(panels.nth(0)).toBeVisible();
  await expect(panels.nth(1)).toBeVisible();
  await expect(panels.nth(0)).toBeInViewport();
  await expect(panels.nth(1)).toBeInViewport();
});
