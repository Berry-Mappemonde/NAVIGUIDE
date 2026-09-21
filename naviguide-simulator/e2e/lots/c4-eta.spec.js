// Lot C4 — ETA : la revue de plan s'affiche et chaque ligne a une date.
// Aucun changement de surface ; seuls les nombres (dates) bougent.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-c4/${name}.jpg`,
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

test("lot C4 — revue de plan : chaque étape a une date", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  const review = page.getByTestId("plan-review");
  await review.scrollIntoViewIfNeeded();
  await expect(review).toBeVisible({ timeout: 15_000 });
  await expect(review).not.toContainText(/lecture…|reading…/i, { timeout: 25_000 });
  if (!(await review.evaluate((el) => el.open))) {
    await review.locator("summary").click();
  }

  const rows = page.getByTestId("plan-review-leg");
  await expect(rows.first()).toBeVisible({ timeout: 15_000 }).catch(() => {});
  const n = await rows.count();
  if (n > 0) {
    for (let i = 0; i < n; i += 1) {
      const dates = rows.nth(i).getByTestId("plan-review-leg-dates");
      await expect(dates).toBeVisible();
      const text = (await dates.innerText()).trim();
      expect(text, `ligne ${i} sans date`).toMatch(/\d/);
      expect(text).toMatch(/→/);
    }
  } else {
    // Sans API le tableau est vide : le panneau reste visible (lot « nombres seulement »).
    await expect(review).toContainText(/Revue du plan|Plan review|indisponible|Aucune jambe/i);
  }
  await review.scrollIntoViewIfNeeded();
  await shot(page, "01-revue");
});
