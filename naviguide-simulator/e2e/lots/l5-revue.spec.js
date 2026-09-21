// Lot L5 — revue commentée : paragraphe sous le tableau (texte ou « règles »).
// Sans API : source = règles. Recette réelle (Nemotron Super) : NEBIUS_API_KEY.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-l5/${name}.jpg`,
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

test("lot L5 — plan-review-comment : texte ou règles", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  const review = page.getByTestId("plan-review");
  await review.scrollIntoViewIfNeeded();
  await expect(review).toBeVisible({ timeout: 15_000 });
  if (!(await review.evaluate((el) => el.open))) {
    await review.locator("summary").click();
  }
  const comment = page.getByTestId("plan-review-comment");
  await comment.scrollIntoViewIfNeeded();
  await expect(comment).toBeVisible();
  const text = (await comment.innerText()).trim();
  expect(text, "plan-review-comment ne doit pas être vide").not.toBe("");
  expect(text).toMatch(/Ce que je changerais|What I would change|règles|rules/i);
  await shot(page, "01-commentaire");
});
