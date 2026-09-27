// Lot RC13 — GET /film sert le script RF5 (avion aller et retour).
// Sans API : Suivre, Revoir et la barre tiennent seuls ; le script serveur
// est sauté. GET /voyage/official sondé ; s'il manque, annotation + saut des
// seules assertions avion — jamais Revoir retiré, ni les pilules, ni la barre.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rc13");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`),
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

const AIR_OUT = /prend l'avion pour|the crew flies to/i;
const AIR_BACK = /retour en avion vers|return flight to/i;

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

async function waitOfficialFilm(page) {
  const t0 = Date.now();
  let last = null;
  while (Date.now() - t0 < 20_000) {
    const r = await page.request.get("/voyage/official/film?lang=fr&seconds=0", { timeout: 12_000 })
      .then((x) => (x.ok() ? x.json() : null))
      .catch(() => null);
    last = r;
    if (r?.chapters?.length && r.status !== "preparing") return r;
    await page.waitForTimeout(800);
  }
  return last;
}

test("lot RC13 — GET /film dit l'avion aller et retour si Cayenne et Halifax", async ({ page }) => {
  test.setTimeout(90_000);
  const official = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  const apiUp = Boolean(official && official.ok());
  const officialBody = apiUp ? await official.json().catch(() => null) : null;
  const markBlob = JSON.stringify([
    ...((officialBody && officialBody.marks) || []),
    ...((officialBody && officialBody.escales) || []),
  ]);
  const routeHasCayenne = /cayenne/i.test(markBlob);
  const routeHasAir = routeHasCayenne && /halifax/i.test(markBlob);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions avion sautées ; Suivre et Revoir gardés",
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

  const durations = page.getByTestId("film-duration");
  if (await durations.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await expect(durations.locator("[aria-pressed='true']"), "aucune durée cochée").toHaveCount(0);
  }

  if (!apiUp) {
    await expect(page.getByTestId("replay-departure")).toBeVisible();
    await shot(page, "01-avion");
    return;
  }

  const film = await waitOfficialFilm(page);
  if (!film?.chapters?.length) {
    test.info().annotations.push({
      type: "film en préparation",
      description: "GET /voyage/official/film sans chapitres — assertions avion sautées",
    });
    await shot(page, "01-avion");
    return;
  }

  const blob = film.chapters.map((c) => c.text || "").join(" ");
  expect(film.targetSeconds, "sans case : pas de budget serveur").toBe(0);
  // Marques officielles : Cayenne + Halifax. Ou Cayenne en marques et Halifax
  // déjà dans le script calculé depuis l'itinéraire Berry (route.geojson).
  if (routeHasAir || (routeHasCayenne && /halifax/i.test(blob))) {
    expect(blob, "avion aller").toMatch(AIR_OUT);
    expect(blob, "avion retour").toMatch(AIR_BACK);
  }

  if (await start.isEnabled().catch(() => false)) {
    await muteVoice(page);
    await start.click();
    const subtitle = page.getByTestId("film-subtitle");
    await expect(subtitle).toBeVisible({ timeout: 8_000 });
    await page.waitForFunction(() => {
      const f = window.__naviguideFilm;
      return typeof f?.seekChapter === "function" && (f.chapterCount || 0) > 0;
    }, null, { timeout: 8_000 }).catch(() => null);
    const airIdx = await page.evaluate(() => {
      const re = /prend l'avion|retour en avion|the crew flies|return flight/i;
      const list = window.__naviguideFilm?.chapters || [];
      const i = list.findIndex((c) => re.test(c.text || ""));
      if (i >= 0) window.__naviguideFilm.seekChapter(i);
      return i;
    });
    if (airIdx >= 0) {
      await expect(subtitle).toContainText(/avion/i, { timeout: 8_000 });
    }
  }
  await shot(page, "01-avion");
});
