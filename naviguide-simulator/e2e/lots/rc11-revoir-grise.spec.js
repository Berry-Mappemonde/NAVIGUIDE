// Lot RC11 — Revoir et la date restent visibles ; plus de film Simulation
// si l'API manque. GET /voyage/official sondé ; s'il manque, annotation +
// saut des seules assertions du /film ready — jamais Revoir, ni le champ
// date, ni « non cliquable ».
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rc11");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`),
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

const FORBIDDEN = /station croisée\s*:\s*Station croisée|Aucun port d'entr[ée]e|entrée dans Entrée dans/i;

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

function wordCount(text) {
  return (String(text || "").match(/\S+/g) || []).length;
}

function isRe7Film(free) {
  const chapters = free?.chapters || [];
  if (!chapters.length) return false;
  const blob = chapters.map((c) => c.text || "").join(" ");
  if (wordCount(blob) > 800) return false;
  if (FORBIDDEN.test(blob)) return false;
  if (/milles nautiques du départ|Bay of Biscay/.test(blob)) return false;
  return true;
}

async function waitRe7Film(page, { timeout = 45_000 } = {}) {
  const t0 = Date.now();
  let last = null;
  while (Date.now() - t0 < timeout) {
    const free = await page.request.get("/voyage/official/film?lang=fr&seconds=0", { timeout: 12_000 })
      .then((r) => (r.ok() ? r.json() : null))
      .catch(() => null);
    if (free?.chapters?.length) {
      last = free;
      if (isRe7Film(free)) return { film: free, stale: false };
      return { film: free, stale: true };
    }
    await page.waitForTimeout(800);
  }
  return last ? { film: last, stale: !isRe7Film(last) } : null;
}

test("lot RC11 — Revoir grisé tant que /film n'est pas prêt, date toujours là", async ({ page }) => {
  test.setTimeout(120_000);
  const official = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  const apiUp = Boolean(official && official.ok());
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions /film ready sautées",
    });
  }

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");

  const start = page.getByTestId("replay-start");
  await expect(start).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("replay-departure")).toBeVisible();

  if (!apiUp) {
    await expect(start).toBeDisabled();
    await expect(page.getByTestId("film-duration")).toHaveCount(0);
    await expect(page.getByTestId("replay-stop")).toHaveCount(0);
    await expect(page.getByTestId("film-subtitle")).toHaveCount(0);
    const started = await page.evaluate(() => Boolean(window.__naviguideFilm?.startedAt));
    expect(started, "pas de récit Ajaccio sans /film").toBe(false);
    await shot(page, "01-revoir-grise");
    return;
  }

  const probed = await waitRe7Film(page);
  if (!probed?.film?.chapters?.length || probed.stale) {
    test.info().annotations.push({
      type: probed?.stale ? "API hors checkout" : "film vide",
      description: "GET /film pas encore RE7 — Revoir reste grisé, date visible",
    });
    await expect(start).toBeDisabled();
    await expect(page.getByTestId("replay-departure")).toBeVisible();
    await expect(page.getByTestId("film-duration")).toHaveCount(0);
    await shot(page, "01-revoir-grise");
    return;
  }

  await expect(start).toBeEnabled({ timeout: 30_000 });
  await expect(page.getByTestId("replay-departure")).toBeVisible();
  const durations = page.getByTestId("film-duration");
  await expect(durations).toBeVisible();
  await expect(durations.locator("[aria-pressed='true']"), "aucune durée cochée").toHaveCount(0);
  await muteVoice(page);
  await start.click();
  const subtitle = page.getByTestId("film-subtitle");
  await expect(subtitle).toBeVisible({ timeout: 8_000 });
  const sub = (await subtitle.innerText()).trim();
  expect(sub, "sous-titre non vide").not.toBe("");
  expect(sub, "pas de phrase interdite").not.toMatch(FORBIDDEN);
  expect(sub, "récit officiel en tête").toMatch(/Saint-Maur/);
  await shot(page, "02-revoir-actif");

  const stopBtn = page.getByTestId("replay-stop");
  if (await stopBtn.isVisible().catch(() => false)) await stopBtn.click();
  await expect(start).toBeVisible({ timeout: 8_000 });
});
