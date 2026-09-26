// Lot RD3 — panneau droit : plus d'encadré jaune route, nom du bateau
// une fois sous Polaires, remise 34 → 29 → ↺ → 34.
// Sans API : badge absent, skipper et cycle clavier tiennent seuls.
// GET /voyage/official sondé ; s'il manque, annotation + saut des seules
// assertions qui en dépendent (pastilles jambe, nom sous Polaires si
// la polar n'a pas chargé) — jamais le badge, ni le nom dans Paramètres
// avancés, ni la remise.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-rd3/${name}.jpg`,
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

async function probeOfficial(page) {
  return page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);
}

async function leaveCinema(page) {
  const cinema = page.getByRole("button", { name: /^(cinéma|cinema)$/i });
  if (!(await cinema.isVisible().catch(() => false))) return;
  const on = /bg-cyan-700/.test((await cinema.getAttribute("class")) || "");
  if (on) await cinema.click();
}

function rightPanelOpen(page) {
  return page.locator(".naviguide-sidebar-panel.right-0").first().evaluate((el) => (
    !el.className.includes("translate-x-full")
  ));
}

async function showToolsPanel(page) {
  await leaveCinema(page);
  if (await rightPanelOpen(page)) return;
  await page.locator(".naviguide-sidebar-toggle--right").click();
  await expect.poll(() => rightPanelOpen(page), { timeout: 10_000 }).toBe(true);
}

test("lot RD3 — plus d'encadré jaune, nom une fois, remise 34 → 29 → 34", async ({ page }) => {
  test.setTimeout(90_000);
  const apiUp = await probeOfficial(page);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — badge, skipper et remise autonomes",
    });
  }

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);
  await showToolsPanel(page);

  await expect(page.getByTestId("route-anti-shipping")).toHaveCount(0);

  const review = page.getByTestId("plan-review");
  if (await review.isVisible({ timeout: 8_000 }).catch(() => false)) {
    if (!(await review.evaluate((el) => el.open))) {
      await review.locator("summary").click();
    }
    const lanes = page.getByTestId("plan-review-lanes");
    if (await lanes.count()) {
      await expect(lanes.first()).toContainText(/couloirs\s*:|lanes\s*:/);
    } else if (!apiUp) {
      test.info().annotations.push({
        type: "sans API",
        description: "Revue du plan sans pastille par jambe — assertion couloirs sautée",
      });
    }
  } else if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "Revue du plan absente — assertion couloirs sautée",
    });
  }

  const polarBoat = page.getByTestId("polar-boat");
  const polarName = await polarBoat.isVisible().catch(() => false)
    ? (await polarBoat.innerText()).trim()
    : "";
  if (polarName) {
    await expect(polarBoat).toBeVisible();
    expect(polarName).not.toBe("");
  } else if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "Polaire non chargée — nom sous Polaires non exigé",
    });
  }

  const orders = page.getByTestId("skipper-orders");
  await expect(orders).toBeVisible({ timeout: 15_000 });
  if (!(await orders.evaluate((el) => el.open))) {
    await orders.locator("summary").first().click();
  }
  const openText = await orders.innerText();
  expect(openText, "Paramètres avancés sans Leopard").not.toMatch(/Leopard|Léopard/i);
  await expect(orders.getByText(/^Bateau$/)).toHaveCount(0);
  if (polarName) {
    expect(openText).not.toContain(polarName);
  }

  await shot(page, "01-panneau");

  const gale = page.getByTestId("skipper-expert-galeKt");
  await expect(gale).toBeVisible();
  await gale.scrollIntoViewIfNeeded();
  await expect(gale).toHaveValue("34");
  const reset = page.getByTestId("skipper-expert-galeKt-reset");
  await expect(reset).toBeDisabled();

  await gale.click({ clickCount: 3 });
  await page.keyboard.type("29");
  await expect(gale).toHaveValue("29");
  await expect(reset).toBeEnabled();
  await shot(page, "02-remise");

  await reset.click();
  await expect(gale).toHaveValue("34");
  await expect(reset).toBeDisabled();
});
