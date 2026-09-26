// Lot R8c — branchement de l'encadré, plus de pop-up hors film.
// Sans API : l'encadré se remplit via la fixture useMoment ; Suivre /
// Simulation / Tracer tiennent seuls. GET /voyage/official : sondé ; s'il
// manque, on annote et on saute seulement les assertions d'horloge / fiche
// enrichie, jamais celles sur l'absence de cartes flottantes.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-r8c/${name}.jpg`,
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
  const box = page.getByTestId("ici-maintenant");
  if (await box.isVisible().catch(() => false)) return;
  await page.locator(".naviguide-sidebar-toggle--left").click();
  await expect(box).toBeVisible({ timeout: 15_000 });
}

async function hideLeftPanel(page) {
  const cinema = page.getByRole("button", { name: /^(cinéma|cinema)$/i });
  if (!(await cinema.isVisible().catch(() => false))) return;
  const on = /bg-cyan-700/.test((await cinema.getAttribute("class")) || "");
  if (!on) await cinema.click();
}

function noFloatingCards(page) {
  return Promise.all([
    expect(page.locator(".naviguide-floating-card[data-testid='moment-now']")).toHaveCount(0),
    expect(page.locator(".naviguide-floating-card[data-testid='moment-free']")).toHaveCount(0),
    expect(page.locator(".leaflet-popup.escale-popup")).toHaveCount(0),
    expect(page.getByTestId("moment-free-listen")).toHaveCount(0),
  ]);
}

test("lot R8c — un encadré, plus aucune carte flottante hors film", async ({ page }) => {
  test.setTimeout(90_000);
  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — horloge officielle / fiche enrichie non exigées",
    });
  }

  const errors = [];
  page.on("pageerror", (err) => errors.push(String(err)));

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");

  await hideLeftPanel(page);
  await noFloatingCards(page);

  await showLeftPanel(page);
  const box = page.getByTestId("ici-maintenant");
  await expect(box).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("ici-tab-now")).toBeVisible();
  await expect(page.getByTestId("ici-tab-story")).toBeVisible();
  await expect(page.getByTestId("ici-tab-journal")).toBeVisible();
  await expect(page.getByTestId("ici-section-leg")).toBeVisible();
  await expect(page.getByTestId("ici-section-here")).toBeVisible();
  await expect(page.getByText(/Ici et maintenant|Here and now/i)).toHaveCount(0);
  await expect(box.locator("h1, h2")).toHaveCount(0);
  await expect(page.getByTestId("listen")).toBeVisible();
  await noFloatingCards(page);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await hideLeftPanel(page);
  await noFloatingCards(page);
  await showLeftPanel(page);
  await expect(box).toBeVisible();
  await expect(page.getByTestId("ici-section-leg")).toBeVisible();
  await expect(page.getByText(/À bord, maintenant|Pendant ce temps, autour du bateau/i)).toHaveCount(0);
  if (apiUp) {
    await expect(page.getByTestId("film-clock-line")).not.toHaveText(/^\s*$/);
  }
  await shot(page, "01-suivre");

  await page.getByTestId("view-simulation").click();
  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
  await showLeftPanel(page);
  await expect(box).toBeVisible();
  await expect(page.getByTestId("ici-leg-line")).toBeVisible();
  await noFloatingCards(page);

  const hasAjaccio = await page.waitForFunction(() => {
    const scene = window.__naviguideScene;
    if (!scene?.waypointMarkers) return false;
    for (const marker of scene.waypointMarkers.values()) {
      if (/Ajaccio/i.test(marker._naviguideWaypoint?.name || "")) return true;
    }
    return false;
  }, null, { timeout: 20_000 }).then(() => true).catch(() => false);

  if (hasAjaccio) {
    await page.evaluate(() => {
      const scene = window.__naviguideScene;
      if (!scene?.map || !scene.waypointMarkers) return;
      for (const marker of scene.waypointMarkers.values()) {
        if (/Ajaccio/i.test(marker._naviguideWaypoint?.name || "")) {
          scene.map.setView(marker.getLatLng(), 7, { animate: false });
          marker.fire("click");
          return;
        }
      }
    });
    const sheet = page.getByTestId("ici-maintenant").getByTestId("escale-sheet");
    const opened = await sheet.isVisible({ timeout: 8_000 }).catch(() => false);
    if (!opened) {
      const row = page.locator("li").filter({ hasText: /Ajaccio/i }).first();
      const openBtn = row.getByTestId("escale-sheet-open");
      if (await openBtn.isVisible().catch(() => false)) await openBtn.click();
    }
    await expect(sheet).toBeVisible({ timeout: 10_000 });
    await expect(sheet).toContainText(/Ajaccio/i);
    await expect(page.getByTestId("here-product").getByTestId("escale-sheet")).toHaveCount(0);
    await expect(page.locator(".leaflet-popup.escale-popup")).toHaveCount(0);
    await expect(sheet.getByRole("button", { name: /écouter|listen/i })).toHaveCount(0);
    await expect(page.getByTestId("ici-tab-now")).toHaveAttribute("aria-selected", "true");
    await sheet.scrollIntoViewIfNeeded();
  } else {
    test.info().annotations.push({
      type: apiUp ? "drapeau" : "sans API",
      description: "aucun drapeau Ajaccio — ouverture d'escale dans l'encadré non jouée",
    });
  }
  await shot(page, "02-simulation");

  const draw = page.getByRole("button", { name: /Berry-Mappemonde.*Tracer votre propre route|Tracer votre propre route|Draw your own route/i });
  await expect(draw).toBeVisible({ timeout: 15_000 });
  await draw.scrollIntoViewIfNeeded();
  await draw.click({ force: true });
  await expect(page.getByTestId("drawing-points")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("ici-maintenant")).toBeVisible();
  await noFloatingCards(page);

  await page.getByRole("button", { name: /annuler|cancel/i }).first().click().catch(() => {});
  await showLeftPanel(page);
  const tools = page.locator(".naviguide-sidebar-toggle--right");
  if (await tools.isVisible().catch(() => false)) {
    const theme = page.getByRole("button", { name: /^(clair|light)$/i });
    if (!(await theme.isVisible().catch(() => false))) await tools.click();
    if (await theme.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await theme.click();
      await expect(page.locator(".light-mode")).toBeVisible({ timeout: 5_000 });
      await showLeftPanel(page);
      await expect(page.getByTestId("ici-maintenant")).toBeVisible();
      await expect(page.getByTestId("ici-tabs")).toBeVisible();
    }
  }

  expect(errors, `erreurs de page : ${errors.join(" | ")}`).toEqual([]);
});
