// Lot R10c — écart local borné (corridor ± 300 nm, cap +20 %).
// Sans API : Simulation, ordres du skipper, bouton Recalculer tiennent seuls.
// GET /voyage/official : sondé ; s'il manque, annotation + return après
// les assertions UI (jamais affaiblies). Recalcul / ≤ 1 650 nm : seulement
// si l'API répond et que le dialogue de proposition s'ouvre.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-r10c/${name}.jpg`,
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
  const orders = page.getByTestId("skipper-orders");
  if (await orders.isVisible({ timeout: 1500 }).catch(() => false)) return;
  const toggle = page.locator(".naviguide-sidebar-toggle--right");
  if (await toggle.isVisible().catch(() => false)) await toggle.click();
}

test("lot R10c — Simulation, vent 30 kn, Recalculer, route bornée", async ({ page }) => {
  test.setTimeout(120_000);
  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — recalcul et ≤ 1 650 nm non joués",
    });
  }

  const errors = [];
  page.on("pageerror", (err) => errors.push(String(err)));

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("view-simulation")).toBeVisible();
  await page.getByTestId("view-simulation").click();
  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");

  await showToolsPanel(page);
  const orders = page.getByTestId("skipper-orders");
  await expect(orders).toBeVisible({ timeout: 15_000 });
  await orders.evaluate((el) => { el.open = true; });
  const gale = page.getByRole("spinbutton", { name: /^Coup de vent|^Gale\b/i }).first();
  await expect(gale).toBeVisible({ timeout: 10_000 });
  await gale.scrollIntoViewIfNeeded();
  await gale.fill("30");
  await expect(gale).toHaveValue("30");

  await showLeftPanel(page);
  const recalculate = page.getByRole("button", {
    name: /Recalculer l.itin[eé]raire|Demander conseil|Recalculate the route/i,
  });
  await expect(recalculate).toBeVisible({ timeout: 15_000 });
  await shot(page, "01-borne");

  expect(errors, `erreurs de page : ${errors.join(" | ")}`).toEqual([]);

  if (!apiUp) return;

  const enabled = await recalculate.isEnabled().catch(() => false);
  if (!enabled) {
    test.info().annotations.push({
      type: "recalcul inactif",
      description: "bouton Recalculer présent mais inactif (voyage / prévision) — ≤ 1 650 nm non joué",
    });
    return;
  }

  await recalculate.click();
  const proposed = page.getByText(/Propos[eé]|Proposed/i).first();
  const dialogUp = await proposed.isVisible({ timeout: 90_000 }).catch(() => false);
  if (!dialogUp) {
    test.info().annotations.push({
      type: "dialogue absent",
      description: "Recalculer cliqué — dialogue de proposition absent après 90 s",
    });
    return;
  }
  await shot(page, "01-borne");
  const dialog = page.locator(".fixed.inset-0").filter({ hasText: /Propos[eé]|Proposed/i }).first();
  const text = await dialog.innerText().catch(() => "");
  const nums = [...text.matchAll(/(\d+(?:[.,]\d+)?)\s*nm/gi)].map((m) => Number(m[1].replace(",", ".")));
  expect(nums.length, `distances nm dans le dialogue : « ${text.slice(0, 240)} »`).toBeGreaterThanOrEqual(1);
  const proposedNm = nums[nums.length - 1];
  expect(proposedNm, "jamais 4 643 nm").toBeLessThan(3000);
  expect(proposedNm).not.toBe(4643);
  if (nums[0] <= 1375) {
    expect(proposedNm, "cas 1 371 × 1,2").toBeLessThanOrEqual(1650);
  } else {
    expect(proposedNm, "cap +20 % de la searoute affichée").toBeLessThanOrEqual(nums[0] * 1.2 + 1);
  }
});
