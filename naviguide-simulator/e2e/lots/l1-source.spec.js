// Lot L1 — source du récit ici() (Token Factory ou règles).
// Sans API : le libellé dit « règles ». La recette réelle (Nemotron Super)
// exige NEBIUS_API_KEY sur le VPS / l’API locale.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-l1/${name}.jpg`,
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

test("lot L1 — story-source : Token Factory ou règles, jamais vide", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  // Suivre ouvre le cinéma et range les panneaux : on sort du cinéma pour
  // le libellé sous le récit ici().
  await page.getByRole("button", { name: /^cinéma$/i }).click();
  const source = page.getByTestId("story-source");
  if (await source.count()) {
    await source.scrollIntoViewIfNeeded();
    await expect(source).toBeVisible({ timeout: 10_000 });
    const text = (await source.innerText()).trim();
    expect(text, "story-source ne doit pas être vide").not.toBe("");
    expect(text).toMatch(/Token Factory|règles|rules/i);
  }
  await shot(page, "01-source");
});
