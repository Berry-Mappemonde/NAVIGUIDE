// Lot RE5 — fourchette d'arrivée sous la prochaine escale, ou rien
// (jamais une date inventée). Sans API : Suivre + liste tiennent seuls.
// GET /voyage/official sondé ; s'il manque, annotation + saut des seules
// assertions fourchette / members — jamais la liste ni l'absence de date inventée.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-re5");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`),
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

function rightPanelOpen(page) {
  return page.locator(".naviguide-sidebar-panel.right-0").first().evaluate((el) => (
    !el.className.includes("translate-x-full")
  ));
}

async function showToolsPanel(page) {
  await leaveCinema(page);
  if (await rightPanelOpen(page).catch(() => false)) return;
  const toggle = page.locator(".naviguide-sidebar-toggle--right");
  if (await toggle.isVisible().catch(() => false)) await toggle.click();
  await expect.poll(() => rightPanelOpen(page), { timeout: 10_000 }).toBe(true);
}

function spanDays(p10, p90) {
  const a = Date.parse(p10);
  const b = Date.parse(p90);
  if (!Number.isFinite(a) || !Number.isFinite(b)) return Infinity;
  return (b - a) / 86400000;
}

async function probeOfficial(request) {
  const official = await request.get("/voyage/official", { timeout: 4000 }).catch(() => null);
  if (!official || !official.ok()) return null;
  const ct = official.headers()["content-type"] || "";
  if (!ct.includes("json")) return null;
  const body = await official.json().catch(() => null);
  return body && typeof body === "object" ? body : null;
}

test("lot RE5 — fourchette sous la prochaine escale, sinon rien", async ({ page, request }) => {
  test.setTimeout(90_000);
  const officialBody = await probeOfficial(request);
  const apiUp = Boolean(officialBody);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — fourchette / members sautés (jamais inventés)",
    });
  }

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
      } catch { /* ensemble encore froid ou quota */ }
      if (etaHits === 1) {
        await route.fulfill({
          contentType: "application/json",
          body: JSON.stringify({
            members: 0,
            p10: null,
            p50: null,
            p90: null,
            source: null,
            reason: "ensemble_unavailable",
            lastAttempt: "2026-09-26T12:00:00Z",
            nextRetry: "2026-09-27T00:15:00Z",
            detail: "Daily API request limit exceeded. Please try again tomorrow.",
          }),
        });
        return;
      }
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(live || {
          members: 24,
          p10: "2026-10-11T00:00:00Z",
          p50: "2026-10-12T12:00:00Z",
          p90: "2026-10-14T00:00:00Z",
          memberKnots: [8.0, 8.1, 7.9],
          source: "recette-re5",
        }),
      });
    });
  }

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("scene-load-mask").waitFor({ state: "hidden", timeout: 25_000 }).catch(() => {});

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await leaveCinema(page);
  await showToolsPanel(page);

  const legend = page.getByTestId("escale-legend");
  await expect(legend).toBeVisible({ timeout: 20_000 });
  await legend.scrollIntoViewIfNeeded();

  const legendEta = page.getByTestId("eta-range");
  // Sans membres : pas de date inventée sous l'escale (vrai avec ou sans API).
  if (!apiUp) {
    await expect(legendEta).toHaveCount(0);
    await shot(page, "01-fourchette");
    return;
  }

  const etaProbe = await request.get("/voyage/official/eta?stop=Papeete", { timeout: 5000 }).catch(() => null);
  if (etaProbe && etaProbe.ok()) {
    const etaBody = await etaProbe.json().catch(() => null);
    if (etaBody && Number(etaBody.members) === 0) {
      expect(etaBody.p10, "sans membres, pas de p10 inventé").toBeFalsy();
      expect(etaBody.p90, "sans membres, pas de p90 inventé").toBeFalsy();
      if (etaBody.reason) {
        expect(etaBody.lastAttempt, "raison sans dernière tentative").toBeTruthy();
        expect(etaBody.nextRetry, "raison sans prochaine relance").toBeTruthy();
      }
    }
  }

  await expect(legendEta.first()).toBeVisible({ timeout: 25_000 });
  const a = (await legendEta.first().innerText()).trim();
  expect(a).toMatch(/arrivée entre le|arrival between/i);
  expect(a).not.toMatch(/p10|membres|members/i);
  expect(await legendEta.count(), "une seule fourchette sous la prochaine escale").toBe(1);
  const nextRow = page.locator("[data-testid='escale-legend-row']").filter({ has: legendEta }).first();
  await nextRow.scrollIntoViewIfNeeded();
  await legendEta.first().scrollIntoViewIfNeeded();
  await shot(page, "01-fourchette");
});
