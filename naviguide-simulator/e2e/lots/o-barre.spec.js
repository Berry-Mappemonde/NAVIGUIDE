// Lot O — barre film compacte, un seul bouton son.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-o/${name}.jpg`,
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

async function assertOneListen(bar) {
  await expect(bar.getByTestId("listen")).toHaveCount(1);
  await expect(bar.locator("[data-testid='replay-voice']")).toHaveCount(0);
  const height = await bar.evaluate((el) => el.getBoundingClientRect().height);
  expect(height, `hauteur barre = ${height}px`).toBeLessThanOrEqual(96);
}

test("lot O — un seul Écouter, pas de replay-voice, barre ≤ 96 px", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  const bar = page.getByTestId("film-bar");
  await expect(bar).toBeVisible();

  // Simulation par défaut : panneaux ouverts, barre étroite, commandes de lecture.
  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
  await assertOneListen(bar);
  await shot(page, "02-simulation");

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(bar.getByTestId("replay-start")).toBeVisible();
  await assertOneListen(bar);
  await shot(page, "01-suivre");
});
