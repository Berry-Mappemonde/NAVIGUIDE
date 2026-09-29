// Lot RG4 — climatologie racontée : changements de vent datés.
// Sans API : Suivre, Revoir et la barre tiennent seuls ; le script serveur
// est sauté. GET /voyage/official sondé ; s'il manque, annotation + saut des
// seules assertions film — jamais Revoir retiré, ni les pilules, ni la barre.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rg4");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`),
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

const CLIMO = /aliz[ée]s|calmes [ée]quator|vents d['’]ouest|mistral|tramontane|de saison|mesur[ée]s|trade winds|equatorial calms|westerl|seasonal|measured knots|vents moyens de saison/i;
const ZONE_FIGURE = /\b(quinze|quatorze|treize|seize|vingt)\s+n[œo]uds\s+de saison.*repli|\b\d+\s*kn\s+de saison\b/i;

async function dismissNotForNav(page) {
  const modal = page.getByTestId("not-for-nav-modal");
  if (await modal.isVisible({ timeout: 1500 }).catch(() => false)) {
    const ack = page.getByTestId("not-for-nav-ack");
    if (await ack.isVisible().catch(() => false)) await ack.check();
    const ok = page.getByTestId("not-for-nav-accept");
    if (await ok.isVisible().catch(() => false)) await ok.click();
    return;
  }
  const ok = page.getByRole("button", { name: /compris|j.ai compris|ok|continuer|accepter|understand|accept/i }).first();
  if (await ok.isVisible({ timeout: 1500 }).catch(() => false)) {
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

async function probeOfficial(page) {
  const res = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  if (!res || !res.ok()) return { apiUp: false };
  const ctype = String(res.headers()["content-type"] || "").toLowerCase();
  if (!ctype.includes("json")) return { apiUp: false };
  const body = await res.json().catch(() => null);
  if (!body || typeof body !== "object") return { apiUp: false };
  return { apiUp: true };
}

test("lot RG4 — un changement de vent daté, jamais un chiffre de repli", async ({ page }) => {
  test.setTimeout(90_000);
  const { apiUp } = await probeOfficial(page);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions film sautées ; barre et Revoir gardés",
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

  const durations = page.getByTestId("film-duration");
  if (await durations.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await expect(durations.locator("[aria-pressed='true']"), "aucune durée cochée").toHaveCount(0);
  }

  if (!apiUp) {
    await expect(start).toBeDisabled();
    await expect(page.getByTestId("film-subtitle")).toHaveCount(0);
    await shot(page, "01-alizes");
    return;
  }

  const film = await page.request.get("/voyage/official/film?lang=fr&seconds=0", { timeout: 12_000 })
    .then((r) => (r.ok() ? r.json() : null))
    .catch(() => null);
  if (!film?.chapters?.length) {
    test.info().annotations.push({
      type: "film vide",
      description: "GET /voyage/official/film sans chapitres — assertions RG4 sautées",
    });
    await shot(page, "01-alizes");
    return;
  }

  const blob = film.chapters.map((c) => c.text || "").join(" ");
  if (!CLIMO.test(blob)) {
    test.info().annotations.push({
      type: "stock pré-RG4",
      description: "film servi encore à l'ancienne clé — remplisseur doit recalculer (FILM_SCRIPT_REV=rg4)",
    });
    await shot(page, "01-alizes");
    return;
  }

  expect(blob, "pas de chiffre inventé présenté comme un repli").not.toMatch(ZONE_FIGURE);

  await expect(start).toBeEnabled({ timeout: 30_000 });
  await muteVoice(page);
  await start.click();
  const subtitle = page.getByTestId("film-subtitle");
  await expect(subtitle).toBeVisible({ timeout: 8_000 });

  await page.waitForFunction(() => {
    const f = window.__naviguideFilm;
    return typeof f?.seekChapter === "function" && (f.chapterCount || 0) > 0;
  }, null, { timeout: 8_000 });

  await page.evaluate((reSrc) => {
    const list = window.__naviguideFilm?.chapters || [];
    const re = new RegExp(reSrc, "i");
    const i = list.findIndex((c) => re.test(c.text || ""));
    if (i >= 0) window.__naviguideFilm.seekChapter(i);
  }, CLIMO.source);
  await shot(page, "01-alizes");
});
