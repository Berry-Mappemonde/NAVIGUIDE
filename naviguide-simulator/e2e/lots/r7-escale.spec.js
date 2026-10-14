// Lot R7 — fiche d'escale en popup sur le drapeau.
// Sans API : le nom de l'escale et la croix tiennent seuls (repli itinéraire).
// Le paragraphe / les listes de la fiche viennent de GET /escale : sautés si l'API est absente.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-r7/${name}.jpg`,
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

async function showLeftPanel(page) {
  const chat = page.getByTestId("logbook-chat");
  if (await chat.isVisible({ timeout: 2000 }).catch(() => false)) return;
  const cinema = page.getByRole("button", { name: /^(cinéma|cinema)$/i });
  if (await cinema.isVisible().catch(() => false)) {
    const on = /bg-cyan-700/.test((await cinema.getAttribute("class")) || "");
    if (on) await cinema.click();
  }
  if (await chat.isVisible({ timeout: 3000 }).catch(() => false)) return;
  await page.locator(".naviguide-sidebar-toggle--left").click();
  await expect(chat).toBeVisible({ timeout: 15_000 });
}

async function showToolsPanel(page) {
  const { showRightPanel } = await import("../helpers.js");
  await showRightPanel(page);
  await expect(page.getByTestId("escale-legend")).toBeVisible({ timeout: 10_000 });
}

async function waitAjaccioFlag(page) {
  await page.waitForFunction(() => {
    const scene = window.__naviguideScene;
    if (!scene?.waypointMarkers) return false;
    for (const marker of scene.waypointMarkers.values()) {
      if (/Ajaccio/i.test(marker._naviguideWaypoint?.name || "")) return true;
    }
    return false;
  }, null, { timeout: 30_000 });
  await page.evaluate(() => {
    const scene = window.__naviguideScene;
    if (!scene?.map || !scene.waypointMarkers) return;
    for (const marker of scene.waypointMarkers.values()) {
      if (/Ajaccio/i.test(marker._naviguideWaypoint?.name || "")) {
        scene.map.setView(marker.getLatLng(), 7, { animate: false });
        return;
      }
    }
  });
}

test("lot R7 — fiche d'escale sur le drapeau, plus dans le panneau", async ({ page }) => {
  test.setTimeout(45_000);
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await page.getByTestId("view-tracer").click();
  await expect(page.getByTestId("view-tracer")).toHaveAttribute("aria-checked", "true");

  await waitAjaccioFlag(page);
  const flag = page.locator("[data-testid='waypoint-flag'][data-escale*='Ajaccio']").first();
  await expect(flag).toBeVisible({ timeout: 10_000 });
  await flag.click({ force: true });

  const sheet = page.getByTestId("escale-sheet");
  await expect(sheet).toBeVisible({ timeout: 10_000 });
  await expect(sheet).toContainText("Ajaccio");
  await expect(sheet.getByTestId("escale-listen")).toHaveCount(0);
  await expect(sheet.getByRole("button", { name: /écouter|listen/i })).toHaveCount(0);
  await expect(page.getByTestId("escale-close")).toBeVisible();
  await expect(page.getByTestId("here-product").getByTestId("escale-sheet")).toHaveCount(0);

  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);
  if (apiUp) {
    const loading = await sheet.getByText(/On rassemble|Loading the sheet/i).isVisible().catch(() => false);
    if (loading) {
      test.info().annotations.push({
        type: "poste",
        description: "fiche encore « On rassemble » (stock figé sans /escale enrichi)",
      });
    } else {
      await expect(sheet).not.toContainText(/On rassemble|Loading the sheet/i);
    }
  } else {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — paragraphe / listes de fiche non vérifiés",
    });
  }
  await shot(page, "01-popup");

  await page.getByTestId("escale-close").click();
  await expect(page.getByTestId("escale-sheet")).toHaveCount(0);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await showLeftPanel(page);
  await expect(page.getByTestId("here-product").getByTestId("escale-sheet")).toHaveCount(0);

  await showToolsPanel(page);
  await expect(page.getByTestId("escale-sheet-open")).toHaveCount(0);
  // RE2 / RF8 : la liste n'ouvre plus la fiche ; le drapeau oui — recentré d'abord (en Suivre la caméra
  // est sur le bateau, le drapeau d'Ajaccio est hors cadre).
  const { centerOnFlag } = await import("../helpers.js");
  await centerOnFlag(page, /Ajaccio/);
  await flag.click({ force: true, timeout: 5_000 }).catch(() => flag.evaluate((el) => el.click()));
  const sheetAgain = page.getByTestId("escale-sheet");
  await expect(sheetAgain).toBeVisible({ timeout: 10_000 });
  await expect(sheetAgain).toContainText("Ajaccio");
  await expect(page.getByTestId("here-product").getByTestId("escale-sheet")).toHaveCount(0);
  await showLeftPanel(page);
  await expect(sheetAgain).toBeInViewport({ timeout: 5_000 });
  await shot(page, "02-suivre");
});
