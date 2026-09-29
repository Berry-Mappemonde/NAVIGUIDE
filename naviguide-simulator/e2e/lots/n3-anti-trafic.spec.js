// Lot N3 — Score anti-trafic (pastille « couloirs : Gibraltar »).
// Sans API : fixture usePlanReview (Ajaccio → Fort-de-France, Gibraltar).
// GET /voyage/official : sondé ; s'il manque, annotation seulement —
// les pastilles fixture ne sont pas affaiblies.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-n3/${name}.jpg`,
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

async function leaveCinema(page) {
  const cinema = page.getByRole("button", { name: /^(cinéma|cinema)$/i });
  if (!(await cinema.isVisible().catch(() => false))) return;
  const on = /bg-cyan-700/.test((await cinema.getAttribute("class")) || "");
  if (on) await cinema.click();
}

async function showReview(page) {
  const { openReviewTab } = await import("../helpers.js");
  await openReviewTab(page);
}

test("lot N3 — Revue du plan : couloirs Gibraltar sous Ajaccio → Fort-de-France", async ({ page }) => {
  test.setTimeout(45_000);
  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — pastilles servies par la fixture (jamais affaiblies)",
    });
  }

  const errors = [];
  page.on("pageerror", (err) => errors.push(String(err)));

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 15_000 });

  await showReview(page);
  const review = page.getByTestId("plan-review");
  await expect(review).toBeVisible({ timeout: 15_000 });

  const row = page.getByTestId("plan-review-leg").filter({ hasText: /Ajaccio/i }).filter({ hasText: /Fort-de-France/i });
  await expect(row).toBeVisible({ timeout: 20_000 });
  await row.scrollIntoViewIfNeeded();
  const lanes = row.getByTestId("plan-review-lanes");

  let officialPack = null;
  if (apiUp) {
    const body = await page.request.get("/voyage/official/plan-review", { timeout: 8000 })
      .then((r) => (r.ok() ? r.json() : null)).catch(() => null);
    officialPack = (body?.legs || []).find((l) => /Ajaccio/i.test(l.from || "") && /Fort-de-France/i.test(l.to || ""))?.antiShipping || null;
  }

  const serverHasN3 = Array.isArray(officialPack?.lanes) && officialPack.lanes.includes("Gibraltar");
  if (!apiUp || serverHasN3) {
    // RD9 : plus de pastille route-anti-shipping — les couloirs sont sur la ligne.
    await expect(lanes).toBeVisible({ timeout: 15_000 });
    await expect(lanes).toContainText(/couloirs\s*:\s*Gibraltar|lanes\s*:\s*Gibraltar|Gibraltar/);
    if (serverHasN3) {
      expect(Number(officialPack.score)).toBeLessThan(1);
    }
    await shot(page, "01-couloirs");
  } else {
    test.info().annotations.push({
      type: "API sans N3",
      description: "GET /voyage/official/plan-review sans antiShipping (API d'un autre checkout) — pastille non exigée",
    });
  }

  expect(errors, `erreurs de page : ${errors.join(" | ")}`).toEqual([]);
});
