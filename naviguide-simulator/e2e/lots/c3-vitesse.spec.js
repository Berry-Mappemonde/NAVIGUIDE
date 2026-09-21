// Lot C3 — une seule vitesse (barre = horloge = debug) ; légende des régimes.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-c3/${name}.jpg`,
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

function knotsIn(text) {
  const m = String(text || "").match(/(\d+[.,]\d+)\s*kt/);
  return m ? Number(m[1].replace(",", ".")) : null;
}

test("lot C3 — vitesse unique et légende des régimes", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");

  const clock = page.getByTestId("clock-line");
  await expect(clock).toBeVisible({ timeout: 15_000 });
  const legend = page.getByTestId("regime-legend");
  await expect(legend).toBeVisible({ timeout: 15_000 });
  await expect(legend).toContainText(/hindcast/i);
  await expect(legend).toContainText(/prévision|forecast/i);
  await expect(legend).toContainText(/climatolog/i);

  const line = await clock.innerText();
  const debug = await page.evaluate(() => window.__naviguideDebug || null);
  expect(debug, "window.__naviguideDebug exposé").toBeTruthy();
  if (/à quai|in port/i.test(line)) {
    expect(debug.atQuay).toBeTruthy();
    expect(debug.speed === 0 || debug.speed == null).toBeTruthy();
    await expect(clock).not.toContainText(/\d+[.,]\d+\s*kt/);
  } else {
    const kn = knotsIn(line);
    expect(kn, `kn dans clock-line : ${line}`).not.toBeNull();
    expect(Number(debug.speed)).toBeCloseTo(kn, 1);
  }
  await shot(page, "01-legende");
});
