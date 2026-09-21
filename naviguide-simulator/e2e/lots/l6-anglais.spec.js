// Lot L6 — langue EN : source du récit ici() visible (Lightning ou règles).
// Sans API : le libellé dit « rules ». La traduction Nemotron exige l'API.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-l6/${name}.jpg`,
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
  if (!(await en.isVisible().catch(() => false))) {
    const right = page.locator(".naviguide-sidebar-toggle--right");
    if (await right.isVisible().catch(() => false)) await right.click();
  }
  await expect(en).toBeVisible({ timeout: 15_000 });
  await en.click();
}

test("lot L6 — langue EN : story-source présent et non vide", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  await switchToEnglish(page);
  await expect(page.getByTestId("view-suivre")).toContainText(/Follow/i);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  // Suivre ouvre le cinéma : on le quitte pour le libellé sous le récit ici().
  await page.getByRole("button", { name: /^(cinéma|cinema)$/i }).click();

  const source = page.getByTestId("story-source");
  await expect(source).toBeVisible({ timeout: 10_000 });
  const text = (await source.innerText()).trim();
  expect(text, "story-source ne doit pas être vide").not.toBe("");
  expect(text).toMatch(/Token Factory|règles|rules|cache|budget/i);
  await shot(page, "01-en");
});
