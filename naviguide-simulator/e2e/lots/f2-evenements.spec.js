// Lot F2 — événements climo / sci dans le fil de cartes (Suivre).
// Sans API : repli sur cardFromJournalEntry (titre climo non vide).
import { expect, test } from "@playwright/test";
import { cardFromJournalEntry } from "../../src/engine/momentCard.js";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-f2/${name}.jpg`,
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

test("lot F2 — fil de cartes : climo ou sci, sinon titre fixture", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");

  await page.evaluate(() => {
    const el = document.querySelector("[data-testid='journal-panel']");
    if (el) el.open = true;
  });

  const found = page.locator('[data-kind="climo"], [data-kind="sci"]');
  const n = await found.count();
  if (n > 0) {
    await expect(found.first()).toBeVisible();
  } else {
    const card = cardFromJournalEntry({
      id: "climo:rose:fixture",
      kind: "climo",
      event: "rose",
      t: "2026-06-02T12:00:00Z",
      lat: 22.0,
      lon: -40.0,
      title: { fr: "Changement de régime", en: "Regime change" },
      facts: { fromDeg: 45, toDeg: 165, deltaDeg: 120 },
    }, "fr");
    expect(card, "cardFromJournalEntry(climo)").toBeTruthy();
    expect(card.title, "titre climo non vide").toBeTruthy();
    expect(String(card.title).length).toBeGreaterThan(0);
    expect(card.kind).toBe("climo");
    expect(card.text).toMatch(/120/);
  }
  await shot(page, "01-regime");
});
