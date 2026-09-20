// Lot P2 — vitesse réelle, zéro à quai.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-p2/${name}.jpg`,
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

async function seekFilm(page, ratio) {
  const bar = page.locator("[data-testid='film-bar'] .relative.w-full.h-2").first();
  await expect(bar).toBeVisible({ timeout: 15_000 });
  const box = await bar.boundingBox();
  if (!box) throw new Error("barre film introuvable");
  await bar.click({ position: { x: Math.max(4, box.width * ratio), y: box.height / 2 } });
}

test("lot P2 — à quai 0 kn ; en mer la vitesse varie", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");

  const clock = page.getByTestId("clock-line");
  await expect(clock).toBeVisible({ timeout: 15_000 });
  let line = await clock.innerText();
  if (!/à quai/i.test(line)) {
    // Le 20 sept. au soir le live peut déjà avoir quitté Nouméa :
    // on se place à une escale en Simulation (holding → atQuay).
    await page.getByTestId("view-simulation").click();
    await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
    const next = page.getByRole("button", { name: /prochaine escale/i });
    await expect(next).toBeVisible({ timeout: 15_000 });
    for (let i = 0; i < 4 && !/à quai/i.test(line); i++) {
      await next.click();
      await page.waitForTimeout(800);
      line = await clock.innerText();
    }
  }
  await expect(clock).toContainText("à quai", { timeout: 10_000 });
  await expect(clock).not.toContainText(/\d+[.,]\d+\s*kt/);
  await shot(page, "01-quai");

  await page.getByTestId("view-simulation").click();
  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
  const seen = new Set();
  for (const ratio of [0.18, 0.42, 0.68]) {
    await seekFilm(page, ratio);
    await page.waitForTimeout(700);
    const kn = knotsIn(await clock.innerText());
    if (kn != null) seen.add(kn);
  }
  expect(seen.size, `vitesses relevées : ${[...seen].join(", ") || "aucune"}`).toBeGreaterThanOrEqual(2);
  await shot(page, "02-mer");
});
