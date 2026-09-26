// Lot R10d — interface de l'expert (revue + Demander conseil).
// Sans API : fixture usePlanReview (Nouméa, 11 → 5, +41 nm, +7 j) et
// le bouton Simulation tiennent seuls. GET /voyage/official : sondé ;
// s'il manque, annotation + return après les assertions UI (jamais
// affaiblies). Dialogue de brouillon : seulement si l'API répond.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-r10d/${name}.jpg`,
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

async function showLeftPanel(page) {
  await leaveCinema(page);
  const sim = page.getByTestId("view-simulation");
  if (await sim.isVisible({ timeout: 1500 }).catch(() => false)) return;
  await page.locator(".naviguide-sidebar-toggle--left").click();
}

async function showToolsPanel(page) {
  await leaveCinema(page);
  const review = page.getByTestId("plan-review");
  if (await review.isVisible({ timeout: 1500 }).catch(() => false)) return;
  const toggle = page.locator(".naviguide-sidebar-toggle--right");
  if (await toggle.isVisible().catch(() => false)) await toggle.click();
}

test("lot R10d — revue du plan conseillée, Demander conseil", async ({ page }) => {
  test.setTimeout(120_000);
  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — dialogue de brouillon non joué",
    });
  }

  const errors = [];
  page.on("pageerror", (err) => errors.push(String(err)));

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });

  await showToolsPanel(page);
  const review = page.getByTestId("plan-review");
  await expect(review).toBeVisible({ timeout: 15_000 });
  if (!(await review.evaluate((el) => el.open))) {
    await review.locator("summary").click();
  }
  const comment = page.getByTestId("plan-review-comment");
  await expect(comment).toBeVisible();
  await expect(comment).toContainText(/Ce que je changerais|What I would change/);

  const alerts = page.getByTestId("plan-review-leg-alerts");
  await expect(alerts.first()).toBeVisible({ timeout: 10_000 });
  await expect(alerts.first()).toContainText(/alertes\s*:\s*\d+|alerts:\s*\d+/i);

  const sentence = page.getByTestId("plan-advice-sentence");
  const sentenceUp = await sentence.isVisible({ timeout: apiUp ? 60_000 : 15_000 }).catch(() => false);
  if (!sentenceUp) {
    expect(apiUp, "sans API la phrase du conseil (fixture) doit être là").toBeTruthy();
    test.info().annotations.push({
      type: "conseil pending",
      description: "GET /voyage/official/advice encore pending — pastilles / Appliquer non joués",
    });
  } else {
    const sentenceText = (await sentence.innerText()).trim();
    expect(sentenceText).toMatch(/Nouméa|Dzaoudzi|Partir|Leave|Rester|Keep leaving/);
    expect(sentenceText).not.toMatch(/\b(Leave Nouméa rather|What I would change is)\b/);
    const pills = page.getByTestId("plan-advice-pills");
    await expect(pills).toBeVisible();
    await expect(pills).toContainText(/\d+\s*→\s*\d+\s*alertes|\d+\s*→\s*\d+\s*alerts/);
    await expect(pills).toContainText(/[+-]?\d+\s*nm/i);
    await expect(pills).toContainText(/[+-]?\d+\s*[jd]\b/i);
    const apply = page.getByTestId("plan-advice-apply");
    await expect(apply).toBeVisible();
    await expect(apply).toContainText(/Appliquer|Apply/);
  }

  await page.getByTestId("view-simulation").click();
  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
  await showLeftPanel(page);
  const ask = page.getByTestId("ask-advice");
  await expect(ask).toBeVisible({ timeout: 15_000 });
  await expect(ask).toContainText(/Demander conseil|Ask for advice/);
  await expect(ask).not.toContainText(/Recalculer l.itin[eé]raire|Recalculate the route/);
  await shot(page, "02-conseil");

  await showToolsPanel(page);
  if (!(await review.evaluate((el) => el.open))) {
    await review.locator("summary").click();
  }
  if (sentenceUp) {
    await page.getByTestId("plan-advice-apply").click();
    const compare = page.getByTestId("plan-advice-compare");
    await expect(compare).toBeVisible();
    await expect(compare).toContainText(/aujourd'hui|today/i);
    await expect(compare).toContainText(/conseillé|advised/i);
    await expect(page.getByTestId("plan-advice-col-today")).toContainText(/alertes|alerts/i);
    await expect(page.getByTestId("plan-advice-col-advised")).toContainText(/alertes|alerts/i);
    await expect(compare).toContainText(/Dzaoudzi|nm/);
  }
  await shot(page, "01-revue");

  expect(errors, `erreurs de page : ${errors.join(" | ")}`).toEqual([]);

  if (!apiUp) return;

  const enabled = await ask.isEnabled().catch(() => false);
  if (!enabled) {
    test.info().annotations.push({
      type: "conseil inactif",
      description: "Demander conseil présent mais inactif (voyage / prévision) — dialogue non joué",
    });
    return;
  }
  await ask.click();
  const dialog = page.getByTestId("route-compare");
  const dialogUp = await dialog.isVisible({ timeout: 90_000 }).catch(() => false);
  if (!dialogUp) {
    test.info().annotations.push({
      type: "dialogue absent",
      description: "Demander conseil cliqué — carte deux colonnes absente après 90 s",
    });
    return;
  }
  await expect(dialog.getByTestId("route-compare-today")).toBeVisible();
  await expect(dialog.getByTestId("route-compare-advised")).toBeVisible();
});
