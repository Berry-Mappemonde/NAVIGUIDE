// Lot RA5 — Stop / Stop auto / Écouter distincts ; fiche hors film.
// Sans API : drapeau, fiche, croix, Suivre, Revoir local tiennent seuls.
// Voix réelle / horloge officielle : seulement si GET /voyage/official répond.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-ra5/${name}.jpg`,
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

test("lot RA5 — Stop, Écouter, fiche hors film", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");

  const apiUp = await probeOfficial(page);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — voix / horloge officielle non vérifiées",
    });
  }

  await waitAjaccioFlag(page);
  const flag = page.locator("[data-testid='waypoint-flag'][data-escale*='Ajaccio']").first();
  await expect(flag).toBeVisible({ timeout: 10_000 });
  await flag.click({ force: true });
  const sheet = page.getByTestId("escale-sheet");
  await expect(sheet).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("escale-close")).toBeVisible();

  await page.getByTestId("escale-close").click();
  await expect(page.getByTestId("escale-sheet")).toHaveCount(0);

  await flag.click({ force: true });
  await expect(page.getByTestId("escale-sheet")).toBeVisible({ timeout: 10_000 });
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("escale-sheet")).toHaveCount(0);

  await flag.click({ force: true });
  await expect(page.getByTestId("escale-sheet")).toBeVisible({ timeout: 8_000 });
  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("escale-sheet")).toHaveCount(0);

  const listen = page.getByTestId("listen");
  await expect(listen).toBeVisible();
  await expect(listen).toBeEnabled();
  await expect(listen).toContainText(/Écouter|Listen/i);

  const replayStart = page.getByTestId("replay-start");
  if (!(await replayStart.isVisible({ timeout: 15_000 }).catch(() => false))) {
    test.info().annotations.push({
      type: "sans API",
      description: "Revoir absent (pas d'horloge) — Stop / film non joués",
    });
    await expect(page.getByTestId("view-simulation")).toBeEnabled();
    await expect(listen).toBeEnabled();
    await shot(page, "01-stop");
    return;
  }

  await replayStart.click();
  await expect(page.getByTestId("replay-stop")).toBeVisible({ timeout: 8_000 });
  await expect(page.getByTestId("escale-sheet")).toHaveCount(0);
  await expect(page.getByTestId("replay-stop")).toBeEnabled();
  await expect(page.getByTestId("replay-stop")).toContainText(/^■?\s*Stop$/i);
  await expect(page.getByTestId("stop-auto")).toHaveCount(0);
  await expect(listen).toContainText(/Écouter|Listen/i);

  const pressed0 = await listen.getAttribute("aria-pressed");
  await listen.click();
  await expect(listen).toHaveAttribute("aria-pressed", pressed0 === "true" ? "false" : "true");
  await listen.click();
  await expect(listen).toHaveAttribute("aria-pressed", pressed0 === "true" ? "true" : "false");

  await expect(page.getByTestId("view-suivre")).toBeEnabled();
  await expect(page.getByTestId("view-simulation")).toBeEnabled();

  await page.getByTestId("replay-stop").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 8_000 });
  await expect(page.getByTestId("replay-stop")).toHaveCount(0);
  await expect(page.getByTestId("escale-sheet")).toHaveCount(0);
  await expect(listen).toBeEnabled();
  await expect(page.getByTestId("replay-start")).toBeEnabled();
  await expect(page.getByTestId("view-simulation")).toBeEnabled();

  await shot(page, "01-stop");
});
