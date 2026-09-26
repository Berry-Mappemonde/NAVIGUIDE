// Lot RB7 — fourchette d'arrivée dès que l'ensemble est prêt, sans recharger.
// Sans API : fumée Suivre + liste des escales (la fourchette n'est jamais inventée).
// Avec API : première réponse members:0 puis ensemble → la phrase apparaît.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-rb7/${name}.jpg`,
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

function spanDays(p10, p90) {
  const a = Date.parse(p10);
  const b = Date.parse(p90);
  if (!Number.isFinite(a) || !Number.isFinite(b)) return Infinity;
  return (b - a) / 86400000;
}

async function dismissNotForNav(page) {
  const ok = page.getByRole("button", { name: /compris|j.ai compris|ok|continuer|accepter|understand|accept/i }).first();
  if (await ok.isVisible({ timeout: 3000 }).catch(() => false)) {
    const ack = page.getByTestId("not-for-nav-ack");
    if (await ack.isVisible().catch(() => false)) await ack.check();
    await ok.click();
  }
}

async function showToolsPanel(page) {
  const review = page.getByTestId("plan-review");
  if (await review.isVisible({ timeout: 2000 }).catch(() => false)) return;
  await page.locator(".naviguide-sidebar-toggle--right").click();
  await expect(review).toBeVisible({ timeout: 10_000 });
}

test("lot RB7 — fourchette dès que l'ensemble est prêt, sans recharger", async ({ page }) => {
  test.setTimeout(90_000);
  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);

  if (apiUp) {
    let etaHits = 0;
    await page.route("**/voyage/official/eta**", async (route) => {
      etaHits += 1;
      let live = null;
      try {
        const res = await route.fetch({ timeout: 2500 });
        if (res.ok()) {
          const body = await res.json();
          if (Number(body.members) > 0 && body.p10 && body.p90 && spanDays(body.p10, body.p90) <= 7) {
            live = body;
          }
        }
      } catch { /* ensembles absents ou encore froids */ }
      if (etaHits === 1) {
        await route.fulfill({
          contentType: "application/json",
          body: JSON.stringify({ members: 0, p10: null, p50: null, p90: null, source: null }),
        });
        return;
      }
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(live || {
          members: 40,
          p10: "2026-11-13T00:00:00Z",
          p50: "2026-11-15T00:00:00Z",
          p90: "2026-11-18T00:00:00Z",
          memberKnots: [8.1, 7.9, 8.0],
          source: "recette-rb7",
        }),
      });
    });
  }

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("film-bar")).toBeVisible();
  const legend = page.getByTestId("escale-legend");
  if (await legend.isVisible({ timeout: 4000 }).catch(() => false)) {
    await legend.scrollIntoViewIfNeeded();
  }

  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — fourchette non vérifiée (jamais inventée)",
    });
    await shot(page, "01-fourchette");
    return;
  }

  await expect(legend).toBeVisible({ timeout: 15_000 });

  await showToolsPanel(page);
  const review = page.getByTestId("plan-review");
  await review.scrollIntoViewIfNeeded();
  if (!(await review.evaluate((el) => el.open))) {
    await review.locator("summary").click();
  }

  const legendEta = page.getByTestId("eta-range");
  await expect(legendEta.first()).toBeVisible({ timeout: 20_000 });
  const a = (await legendEta.first().innerText()).trim();
  expect(a).toMatch(/arrivée entre le|arrival between/i);
  expect(a).not.toMatch(/p10|membres|members|juin|June/i);
  expect(await legendEta.count(), "une seule fourchette sous la prochaine escale").toBe(1);

  const reviewEta = page.getByTestId("plan-review-eta-range");
  if (await reviewEta.count()) {
    const b = (await reviewEta.first().innerText()).trim();
    expect(b).toBe(a);
  }
  const row = page.getByTestId("plan-review-leg").filter({ hasText: /Nouméa/i }).filter({ hasText: /Dzaoudzi/i });
  if (await row.count()) await row.first().scrollIntoViewIfNeeded();
  await shot(page, "01-fourchette");
});
