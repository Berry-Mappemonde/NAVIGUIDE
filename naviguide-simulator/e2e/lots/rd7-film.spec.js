// Lot RD7 — le film raconte les vraies données : durées décochables,
// journal sans budget, plus jamais les phrases ATMOS.
// Sans API : cases 2:30 / 3:00 et l'absence de remplissage dans le
// sous-titre local tiennent seuls.
// GET /voyage/official sondé ; s'il manque, annotation + saut des seules
// assertions du script serveur — jamais le défaut décoché, ni le toggle.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-rd7/${name}.jpg`,
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

const FILLER = /ciel reste haut|mer porte le bateau|route tient le cap|vent reste le vent|mer reste la mer|sky stays high|sea carries the boat|course holds|wind stays the wind/i;

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

async function muteVoice(page) {
  const listen = page.getByTestId("listen");
  if (await listen.isVisible().catch(() => false)) {
    if (await listen.getAttribute("aria-pressed") === "true") await listen.click();
  }
}

function durationBtn(page, sec) {
  return page.getByTestId("film-duration").locator(`[data-seconds="${sec}"]`);
}

test("lot RD7 — durées décochées, récit du journal, budget tenu", async ({ page }) => {
  test.setTimeout(90_000);
  const official = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  const apiUp = Boolean(official && official.ok());
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — script serveur /film sauté",
    });
  }

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("film-duration")).toBeVisible();

  const btn150 = durationBtn(page, 150);
  const btn180 = durationBtn(page, 180);
  await expect(btn150).toBeVisible();
  await expect(btn180).toBeVisible();
  await expect(btn150).toHaveAttribute("aria-pressed", "false");
  await expect(btn180).toHaveAttribute("aria-pressed", "false");

  await btn150.click();
  await expect(btn150).toHaveAttribute("aria-pressed", "true");
  await expect(btn180).toHaveAttribute("aria-pressed", "false");
  await btn150.click();
  await expect(btn150).toHaveAttribute("aria-pressed", "false");
  await btn180.click();
  await expect(btn180).toHaveAttribute("aria-pressed", "true");
  await btn180.click();
  await expect(btn180).toHaveAttribute("aria-pressed", "false");
  await expect(btn150).toHaveAttribute("aria-pressed", "false");
  await shot(page, "01-durees");

  await muteVoice(page);
  await page.getByTestId("replay-start").click();
  const subtitle = page.getByTestId("film-subtitle");
  await expect(subtitle).toBeVisible({ timeout: 8_000 });
  const sub = (await subtitle.innerText()).trim();
  expect(sub, "sous-titre non vide").not.toBe("");
  expect(sub, "pas de phrase ATMOS").not.toMatch(FILLER);
  await shot(page, "02-recit");

  const budgetNone = await page.evaluate(() => window.__naviguideFilm?.budgetSeconds);
  expect(budgetNone, "aucune durée → pas de budget").toBe(0);

  if (apiUp) {
    const free = await page.request.get("/voyage/official/film?lang=fr&seconds=0", { timeout: 8000 })
      .then((r) => (r.ok() ? r.json() : null))
      .catch(() => null);
    if (!free?.chapters?.length) {
      test.info().annotations.push({
        type: "film vide",
        description: "GET /voyage/official/film?seconds=0 sans chapitres",
      });
    } else {
      const blob = free.chapters.map((c) => c.text || "").join(" ");
      expect(free.targetSeconds, "sans case : pas de budget serveur").toBe(0);
      expect(blob, "pas de phrase ATMOS côté serveur").not.toMatch(FILLER);
      expect(blob, "pas de nm nu").not.toMatch(/\bnm\b/);
      expect(blob, "pas de décimale déclamée").not.toMatch(/\d+[.,]\d{1,2}(?!\d)/);
    }
  }

  const stopBtn = page.getByTestId("replay-stop");
  if (await stopBtn.isVisible().catch(() => false)) await stopBtn.click();
  await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 8_000 });

  await btn150.click();
  await expect(btn150).toHaveAttribute("aria-pressed", "true");
  await muteVoice(page);
  await page.getByTestId("replay-start").click();
  await expect(page.getByTestId("replay-stop")).toBeVisible({ timeout: 8_000 });
  await expect.poll(async () => page.evaluate(() => window.__naviguideFilm?.targetSeconds), {
    timeout: 5_000,
  }).toBe(150);
  expect(await page.evaluate(() => window.__naviguideFilm?.budgetSeconds)).toBe(150);
  await page.waitForTimeout(2500);
  expect(await page.evaluate(() => Boolean(window.__naviguideFilm?.ended))).toBe(false);
  const sub150 = (await subtitle.innerText()).trim();
  expect(sub150).not.toMatch(FILLER);

  if (apiUp) {
    const timed = await page.request.get("/voyage/official/film?lang=fr&seconds=150", { timeout: 8000 })
      .then((r) => (r.ok() ? r.json() : null))
      .catch(() => null);
    if (timed?.chapters?.length) {
      expect(timed.targetSeconds, "budget 150 s").toBe(150);
      const blob = timed.chapters.map((c) => c.text || "").join(" ");
      expect(blob).not.toMatch(FILLER);
    }
  }
});
