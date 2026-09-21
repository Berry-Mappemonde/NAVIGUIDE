// Lot N — panneau gauche stable : le chat ne saute pas pendant une lecture.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-n/${name}.jpg`,
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

async function showLeftPanel(page) {
  const chat = page.getByTestId("logbook-chat");
  if (await chat.isVisible().catch(() => false)) return;
  const cinema = page.getByRole("button", { name: /^cinéma$/i });
  if (await cinema.isVisible().catch(() => false)) await cinema.click();
  if (await chat.isVisible({ timeout: 4000 }).catch(() => false)) return;
  await page.locator(".naviguide-sidebar-toggle--left").click();
  await expect(chat).toBeVisible({ timeout: 15_000 });
}

async function showToolsPanel(page) {
  const theme = page.getByRole("button", { name: /^(sombre|clair|dark|light)$/i });
  if (await theme.isVisible().catch(() => false)) return;
  await page.locator(".naviguide-sidebar-toggle--right").click();
  await expect(theme).toBeVisible({ timeout: 10_000 });
}

test("lot N — chat immobile pendant une lecture Suivre ; sombre puis clair", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await showLeftPanel(page);

  const chat = page.getByTestId("logbook-chat");
  await expect(chat).toBeVisible({ timeout: 15_000 });
  const topBefore = await chat.evaluate((el) => el.getBoundingClientRect().top);

  const start = page.getByTestId("replay-start");
  if (await start.isVisible({ timeout: 8_000 }).catch(() => false)) {
    await start.click();
  }
  await page.waitForTimeout(6_000);

  await expect(chat).toBeVisible();
  const topAfter = await chat.evaluate((el) => el.getBoundingClientRect().top);
  expect(topAfter, `chat.top avant=${topBefore} après=${topAfter}`).toBe(topBefore);
  await shot(page, "01-sombre");

  await showToolsPanel(page);
  const theme = page.getByRole("button", { name: /^(sombre|dark)$/i });
  await expect(theme).toBeVisible({ timeout: 8_000 });
  await theme.click();
  await expect(page.locator(".light-mode")).toBeVisible({ timeout: 5_000 });
  await page.locator(".naviguide-sidebar-toggle--right").click();
  await showLeftPanel(page);
  await expect(chat).toBeVisible();
  const topLight = await chat.evaluate((el) => el.getBoundingClientRect().top);
  expect(topLight, `chat.top clair=${topLight} sombre=${topBefore}`).toBe(topBefore);
  await shot(page, "02-clair");
});
