// Fumée (lot H) : ce que `main` garantit à l'ouverture, sans serveur API.
import { expect, test } from "@playwright/test";

test.describe("simulateur — fumée", () => {
  test("ouvre en Simulation cinéma, barre film, sans erreur de page", async ({ page }) => {
    const errors = [];
    page.on("pageerror", (err) => errors.push(String(err)));
    await page.goto("/");
    // Modal « ne convient pas à la navigation » (si présente) : on la ferme.
    const ok = page.getByRole("button", { name: /compris|j.ai compris|ok|continuer/i }).first();
    if (await ok.isVisible({ timeout: 3000 }).catch(() => false)) await ok.click();
    await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
    const cinema = page.getByRole("button", { name: /^(cinéma|cinema)$/i });
    await expect(cinema).toBeVisible();
    expect((await cinema.getAttribute("class")) || "").toMatch(/bg-cyan-700/);
    expect(errors, `erreurs de page : ${errors.join(" | ")}`).toEqual([]);
  });

  test("Suivre / Simulation se commutent, un calque s'allume", async ({ page }) => {
    const errors = [];
    page.on("pageerror", (err) => errors.push(String(err)));
    await page.goto("/");
    await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("view-suivre").click();
    await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
    await page.getByTestId("view-simulation").click();
    await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
    // Suivre ouvre le cinéma : les deux panneaux se ferment. Les calques
    // sont dans le panneau droit — on le rouvre avant ZEE (sans API).
    const drawer = page.getByTestId("layers-drawer");
    if (!(await drawer.locator("summary").isVisible().catch(() => false))) {
      await page.locator(".naviguide-sidebar-toggle--right").click();
      await expect(drawer.locator("summary")).toBeVisible({ timeout: 10_000 });
    }
    await drawer.locator("summary").scrollIntoViewIfNeeded();
    if (!(await drawer.evaluate((el) => el.open))) await drawer.locator("summary").click();
    const zee = drawer.getByRole("button", { name: "ZEE", exact: true });
    await zee.scrollIntoViewIfNeeded();
    await zee.click();
    await expect(zee).toHaveAttribute("aria-pressed", "true");
    expect(errors, `erreurs de page : ${errors.join(" | ")}`).toEqual([]);
  });
});
