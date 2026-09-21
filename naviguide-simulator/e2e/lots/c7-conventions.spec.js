// Lot C7 — conventions : info-bulle sur la distance (saut avion exclu).
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-c7/${name}.jpg`,
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

test("lot C7 — survol de la distance : title non vide", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });
  const summary = page.getByTestId("route-summary");
  await expect(summary).toBeVisible({ timeout: 30_000 });
  const title = await summary.getAttribute("title");
  expect(title, "title sur route-summary").toBeTruthy();
  expect(String(title).trim().length).toBeGreaterThan(0);
  await summary.hover();
  await shot(page, "01-infobulle");
});
