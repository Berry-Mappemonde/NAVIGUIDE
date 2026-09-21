// Lot C2 — horloge à trois régimes. Sans API : fumée barre film.
// Avec API et hindcast prêt : clock-regime contient « hindcast » et « sources ».
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-c2/${name}.jpg`,
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

test("lot C2 — régime sur la barre film", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await shot(page, "01-regime");

  const regime = page.getByTestId("clock-regime");
  let api = null;
  try {
    const r = await page.request.get("/voyage/official/regimes");
    if (r.ok()) api = await r.json();
  } catch {
    api = null;
  }
  if (api) {
    await expect(regime).toBeVisible({ timeout: 15_000 });
    const text = await regime.innerText();
    expect(text).toMatch(/hindcast|forecast|prévision|climatolog/i);
    if (api.hindcastStatus === "ready") {
      expect(text).toMatch(/hindcast/i);
      expect(text).toMatch(/sources/i);
    }
  } else {
    await expect(page.getByTestId("film-bar")).toBeVisible();
  }
});
