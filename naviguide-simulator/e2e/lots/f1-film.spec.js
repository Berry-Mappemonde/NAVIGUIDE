// Lot F1 — chapitrage et cinématique menée par la voix.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-f1/${name}.jpg`,
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

test("lot F1 — film 150 s, zoom fixe, sous-titre Saint-Maur", async ({ page }) => {
  test.setTimeout(220_000);
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("film-duration")).toBeVisible();

  await page.getByTestId("replay-start").click();
  const subtitle = page.getByTestId("film-subtitle");
  await expect(subtitle).toBeVisible({ timeout: 8_000 });
  await expect(subtitle).toContainText("Saint-Maur");
  await shot(page, "01-depart");

  await page.waitForFunction(() => Boolean(window.__naviguideScene?.map), { timeout: 10_000 });
  // Zoom fixe pendant une jambe. Le chapitre 1 (Saint-Maur → La Rochelle) est
  // court : on relance la fenêtre de 4 s si on a changé de chapitre.
  await page.waitForTimeout(1_500);
  let z0 = 0;
  let end = { z: 0, ch: -1 };
  let chapter = -1;
  for (let i = 0; i < 4; i++) {
    chapter = await page.evaluate(() => window.__naviguideFilm?.chapterIdx ?? 0);
    z0 = await page.evaluate(() => window.__naviguideScene.map.getZoom());
    await page.waitForTimeout(4_000);
    end = await page.evaluate(() => ({
      z: window.__naviguideScene.map.getZoom(),
      ch: window.__naviguideFilm?.chapterIdx ?? 0,
    }));
    if (end.ch === chapter) break;
  }
  expect(end.ch, "mesure à cheval sur deux chapitres").toBe(chapter);
  expect(Math.abs(end.z - z0), `zoom ${z0} → ${end.z}`).toBeLessThanOrEqual(0.01);

  await page.waitForFunction(() => {
    const el = document.querySelector("[data-testid='film-subtitle']");
    const text = el?.textContent || "";
    return text.length > 0 && (/Rochelle|Ajaccio|mer|Atlantique|Fort-de-France/i.test(text) || (window.__naviguideFilm?.chapterIdx ?? 0) >= 1);
  }, { timeout: 80_000 }).catch(() => {});
  await shot(page, "02-atlantique");

  await page.waitForFunction(() => Boolean(window.__naviguideFilm?.ended), { timeout: 180_000 });
  const elapsed = await page.evaluate(() => window.__naviguideFilm?.elapsed);
  expect(elapsed, `durée film = ${elapsed}s`).toBeGreaterThanOrEqual(142);
  expect(elapsed, `durée film = ${elapsed}s`).toBeLessThanOrEqual(158);
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await shot(page, "03-arrivee");
});
