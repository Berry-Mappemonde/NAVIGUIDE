// Lot R9b — vue Journal (date · position · changement), clic → curseur.
// Sans API : l'onglet Journal et la liste tiennent seuls (repli local).
// GET /voyage/official : sondé ; s'il manque, on annote et on saute seulement
// les assertions d'entrées officielles (15 mai → aujourd'hui).
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-r9b/${name}.jpg`,
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

function localJournalSeed() {
  const t0 = new Date();
  t0.setUTCHours(8, 0, 0, 0);
  const later = new Date(t0.getTime() + 14 * 86400000);
  return [
    {
      voyageId: "local",
      seq: 0,
      t: t0.toISOString(),
      pos: { lat: 46.81, lon: 1.64 },
      signature: "r9b-seed-0",
      changes: [],
    },
    {
      voyageId: "local",
      seq: 1,
      t: later.toISOString(),
      pos: { lat: 41.92, lon: 8.74 },
      signature: "r9b-seed-1",
      changes: [{ kind: "escale", score: 3, title: "Ajaccio", fact: "" }],
    },
  ];
}

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

test("lot R9b — Journal : liste, clic place le curseur", async ({ page }) => {
  test.setTimeout(90_000);
  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — entrées officielles 15 mai → aujourd'hui non exigées",
    });
  }

  const errors = [];
  page.on("pageerror", (err) => errors.push(String(err)));

  await page.addInitScript(({ key, seed }) => {
    try {
      localStorage.setItem(key, JSON.stringify(seed));
    } catch {
      /* ignore */
    }
  }, { key: "naviguide.moment-journal.v1.simulation:official", seed: localJournalSeed() });

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await showLeftPanel(page);

  const box = page.getByTestId("ici-maintenant");
  await expect(box).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("ici-tab-journal")).toBeVisible();
  await page.getByTestId("ici-tab-journal").click();
  await expect(page.getByTestId("ici-journal-slot")).toBeVisible();
  await expect(page.getByTestId("ici-journal-list")).toBeVisible();
  await expect(box.getByText(/Le journal commence|Écrit par le serveur|cliquez pour/i)).toHaveCount(0);

  const simEntries = page.getByTestId("ici-journal-entry");
  await expect(simEntries.first()).toBeVisible({ timeout: 15_000 });
  const simCount = await simEntries.count();
  expect(simCount).toBeGreaterThanOrEqual(1);
  const firstSim = (await simEntries.first().innerText()).trim();
  const lastSim = (await simEntries.nth(simCount - 1).innerText()).trim();
  expect(firstSim.length).toBeGreaterThan(0);
  expect(lastSim.length).toBeGreaterThan(0);

  const clockBefore = (await page.getByTestId("film-clock-line").innerText().catch(() => "")) || "";
  const nmBefore = await page.evaluate(() => window.__naviguideScene?.playback?.state?.nm ?? null);
  const seekTarget = page.getByTestId("ici-journal-entry").filter({ hasText: /Ajaccio/i }).first();
  if (await seekTarget.isVisible().catch(() => false)) {
    await seekTarget.click();
  } else {
    await simEntries.nth(Math.min(simCount - 1, 1)).click();
  }
  if (clockBefore.trim()) {
    await expect(page.getByTestId("film-clock-line")).not.toHaveText(clockBefore, { timeout: 8_000 });
  } else if (nmBefore != null) {
    await expect.poll(async () => page.evaluate(() => window.__naviguideScene?.playback?.state?.nm ?? null), { timeout: 8_000 })
      .not.toBe(nmBefore);
  }

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await showLeftPanel(page);
  await page.getByTestId("ici-tab-journal").click();
  await expect(page.getByTestId("ici-journal-slot")).toBeVisible();
  await expect(page.getByTestId("ici-tab-now")).toBeVisible();
  await expect(page.getByTestId("ici-tab-story")).toBeVisible();

  if (apiUp) {
    const official = await page.request.get("/voyage/official/moments", { timeout: 8_000 })
      .then((r) => (r.ok() ? r.json() : null))
      .catch(() => null);
    if (official && Array.isArray(official.moments) && official.moments.length) {
      const officialEntries = page.getByTestId("ici-journal-entry");
      await expect(officialEntries.first()).toBeVisible({ timeout: 20_000 });
      await expect(officialEntries.first()).not.toContainText("Marina Bas-du-Fort", { timeout: 15_000 });
      const n = await officialEntries.count();
      expect(n).toBeGreaterThanOrEqual(1);
      const firstText = await officialEntries.first().innerText();
      expect(firstText).toMatch(/\d+ (janv|févr|mars|avr|mai|juin|juil|août|sept|oct|nov|déc|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/i);
      const mid = officialEntries.nth(Math.min(Math.max(n - 1, 0), 3));
      const clock0 = (await page.getByTestId("film-clock-line").innerText().catch(() => "")) || "";
      await mid.click();
      if (clock0.trim()) {
        await expect(page.getByTestId("film-clock-line")).not.toHaveText(clock0, { timeout: 10_000 });
      }
    } else {
      test.info().annotations.push({
        type: "journal vide",
        description: "GET /voyage/official/moments sans lignes — liste officielle non exigée",
      });
    }
  }

  if (!apiUp) {
    await page.getByTestId("view-simulation").click();
    await showLeftPanel(page);
    await page.getByTestId("ici-tab-journal").click();
    await expect(page.getByTestId("ici-journal-entry").first()).toBeVisible({ timeout: 10_000 });
  }
  await shot(page, "01-journal");
  expect(errors, `erreurs de page : ${errors.join(" | ")}`).toEqual([]);
});
