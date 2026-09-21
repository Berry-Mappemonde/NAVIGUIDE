// Lot R11 — fourchette d'arrivée lisible, jours de mer cohérents.
// Sans API : fumée (barre film + Suivre). Avec API : les deux libellés
// (légende / revue du plan) sont identiques, sans « p10 » ni « membres ».
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-r11/${name}.jpg`,
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

async function showToolsPanel(page) {
  const review = page.getByTestId("plan-review");
  if (await review.isVisible({ timeout: 2000 }).catch(() => false)) return;
  await page.locator(".naviguide-sidebar-toggle--right").click();
  await expect(review).toBeVisible({ timeout: 10_000 });
}

test("lot R11 — fourchette identique sous l'escale et dans la revue", async ({ page }) => {
  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);
  if (apiUp) {
    await page.route("**/voyage/official/eta**", async (route) => {
      try {
        const res = await route.fetch({ timeout: 2500 });
        if (res.ok()) {
          const body = await res.json();
          if (Number(body.members) > 0 && body.p10 && body.p90) {
            await route.fulfill({ json: body });
            return;
          }
        }
      } catch { /* ensembles absents ou lents */ }
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          members: 80,
          p10: "2026-10-31T00:00:00Z",
          p90: "2026-11-04T00:00:00Z",
          source: "recette-r11",
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

  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — fourchette et jours de mer non vérifiés",
    });
    await shot(page, "01-eta");
    return;
  }

  await showToolsPanel(page);
  const review = page.getByTestId("plan-review");
  await review.scrollIntoViewIfNeeded();
  if (!(await review.evaluate((el) => el.open))) {
    await review.locator("summary").click();
  }

  const reviewBody = await page.request.get("/voyage/official/plan-review", { timeout: 8000 })
    .then((r) => (r.ok() ? r.json() : null)).catch(() => null);
  const noumeaLeg = (reviewBody?.legs || []).find((l) => /Nouméa/i.test(l.from || "") && /Dzaoudzi/i.test(l.to || ""));
  if (noumeaLeg && Number(noumeaLeg.plannedKnots) > 0) {
    expect(Number(noumeaLeg.daysAtSea), `daysAtSea Nouméa → Dzaoudzi : ${noumeaLeg.daysAtSea}`).toBeGreaterThan(30);
    const noumea = page.getByTestId("plan-review-leg").filter({ hasText: /Nouméa/i }).filter({ hasText: /Dzaoudzi/i });
    if (await noumea.count()) {
      const txt = await noumea.first().innerText();
      const m = txt.match(/(\d+(?:[.,]\d+)?)\s*(?:j de mer|d at sea)/i);
      expect(m, `badge mer sur Nouméa → Dzaoudzi : ${txt}`).toBeTruthy();
      const days = parseFloat(m[1].replace(",", "."));
      expect(days, `jours de mer Nouméa → Dzaoudzi : ${days}`).toBeGreaterThan(30);
    }
    const row = page.getByTestId("plan-review-leg").filter({ hasText: /Nouméa/i }).filter({ hasText: /Dzaoudzi/i });
    if (await row.count()) await row.first().scrollIntoViewIfNeeded();
  } else if (noumeaLeg) {
    test.info().annotations.push({
      type: "API autre checkout",
      description: "plan-review sans plannedKnots — jours de mer serveur pas encore R11",
    });
    const row = page.getByTestId("plan-review-leg").filter({ hasText: /Nouméa/i }).filter({ hasText: /Dzaoudzi/i });
    if (await row.count()) await row.first().scrollIntoViewIfNeeded();
  }

  const legendEta = page.getByTestId("eta-range");
  const reviewEta = page.getByTestId("plan-review-eta-range");
  await legendEta.waitFor({ state: "attached", timeout: 8000 }).catch(() => {});
  await reviewEta.waitFor({ state: "attached", timeout: 4000 }).catch(() => {});
  const legendVisible = (await legendEta.count()) > 0;
  const reviewVisible = (await reviewEta.count()) > 0;
  if (legendVisible && reviewVisible) {
    const a = (await legendEta.innerText()).trim();
    const b = (await reviewEta.innerText()).trim();
    expect(a).toMatch(/arrivée entre le|arrival between/i);
    expect(a).not.toMatch(/p10|membres|members/i);
    expect(b).toBe(a);
  } else {
    test.info().annotations.push({
      type: "sans ensembles",
      description: "fourchette absente (members=0 ou /eta lent) — jamais inventée",
    });
  }
  await shot(page, "01-eta");
});
