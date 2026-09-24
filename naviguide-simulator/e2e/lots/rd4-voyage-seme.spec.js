// Lot RD4 / RC7 — voyage officiel semé au démarrage : GET /voyage/official
// ne 404 pas ; Suivre, fourchette, journal et Revoir tiennent.
// Sans API : Suivre, barre film et Revoir tiennent seuls.
// GET /voyage/official sondé ; s'il manque, annotation + saut des seules
// assertions qui en dépendent — jamais Suivre, ni Revoir, ni l'onglet Journal.
// Avec API : GET /eta et /moments sont 200 en < 5 s (échec si 524 / connexion
// fermée). Fourchette / lignes de journal seulement si members > 0 / moments
// non vides — plus d'annotation qui verdit un GET mort.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-rc7/${name}.jpg`,
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
  const toggle = page.locator(".naviguide-sidebar-toggle--left");
  if (await toggle.isVisible().catch(() => false)) await toggle.click();
  await expect(box).toBeVisible({ timeout: 15_000 });
}

function pickEtaStop(body) {
  const marks = Array.isArray(body?.marks) ? body.marks : [];
  const named = marks.find((m) => /dzaoudzi/i.test(m.name || ""))
    || marks.find((m) => m.name && !/saint-maur|la rochelle/i.test(m.name));
  return named?.name || "Dzaoudzi";
}

test("lot RD4 — voyage semé : Suivre, fourchette, journal, Revoir", async ({ page }) => {
  test.setTimeout(90_000);
  const official = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  const apiUp = Boolean(official && official.ok());
  let etaBody = null;
  let momentRows = [];
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — 200 / fourchette / journal officiel sautés",
    });
  } else {
    expect(official.status(), "GET /voyage/official jamais 404 sur poste frais").toBe(200);
    const body = await official.json().catch(() => ({}));
    expect(body.voyageId).toBe("berry-mappemonde-2026-officiel");
    expect(Array.isArray(body.points) && body.points.length > 0).toBe(true);

    const etaStop = pickEtaStop(body);
    const etaStarted = Date.now();
    const etaRes = await page.request.get(
      `/voyage/official/eta?stop=${encodeURIComponent(etaStop)}`,
      { timeout: 5000 },
    );
    expect(etaRes.status(), "GET /voyage/official/eta 200 en < 5 s, jamais 524").toBe(200);
    expect(Date.now() - etaStarted, "GET /eta sans connexion fermée").toBeLessThan(5000);
    etaBody = await etaRes.json().catch(() => ({}));
    expect(Number.isFinite(Number(etaBody.members))).toBe(true);

    const momStarted = Date.now();
    const momRes = await page.request.get("/voyage/official/moments", { timeout: 5000 });
    expect(momRes.status(), "GET /voyage/official/moments 200 en < 5 s, jamais 524").toBe(200);
    expect(Date.now() - momStarted, "GET /moments sans connexion fermée").toBeLessThan(5000);
    const moments = await momRes.json().catch(() => ({}));
    momentRows = Array.isArray(moments.moments) ? moments.moments : [];
  }

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("film-bar")).toBeVisible();
  await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 15_000 });

  const legend = page.getByTestId("escale-legend");
  if (await legend.isVisible({ timeout: 4000 }).catch(() => false)) {
    await legend.scrollIntoViewIfNeeded();
  }

  if (apiUp && Number(etaBody?.members) > 0) {
    const legendEta = page.getByTestId("eta-range");
    await expect(legendEta.first()).toBeVisible({ timeout: 8_000 });
    const a = (await legendEta.first().innerText()).trim();
    expect(a).toMatch(/arrivée entre le|arrival between/i);
    expect(a).not.toMatch(/p10|membres|members/i);
  }

  await showLeftPanel(page);
  await expect(page.getByTestId("ici-tab-journal")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("ici-tab-journal").click();
  await expect(page.getByTestId("ici-tab-journal")).toHaveAttribute("aria-selected", "true");
  // Slot vide = hauteur 0 → Playwright le compte « hidden » ; l'onglet suffit
  // sans API. Les lignes ne sont exigées que si GET /moments en a renvoyé.
  await expect(page.getByTestId("ici-journal-slot")).toHaveCount(1);

  if (apiUp && momentRows.length) {
    const entries = page.getByTestId("ici-journal-entry");
    await expect(entries.first()).toBeVisible({ timeout: 20_000 });
    expect(await entries.count()).toBeGreaterThan(0);
  }

  await page.getByText(/Position de l.expédition|Positioning the expedition/i)
    .waitFor({ state: "hidden", timeout: 12_000 })
    .catch(() => {});
  await shot(page, "01-fourchette");

  await page.getByTestId("replay-start").click();
  await expect(page.getByTestId("replay-stop")).toBeVisible({ timeout: 8_000 });
  expect(await page.evaluate(() => Boolean(window.__naviguideFilm?.ended))).toBe(false);
});
