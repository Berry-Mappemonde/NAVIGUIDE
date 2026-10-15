// Lot RG18 — une seule plume : fiches « ici » = phrases de règles du film ;
// POST /ici/story seulement sur Rédigé. Sans API (CI) : GET /voyage/official
// sondé ; s'il manque, annotation + saut des assertions sac / film — barre,
// Suivre, Brut et l'absence d'appel /ici/story restent.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema, probeOfficial, showLeftPanel } from "../helpers.js";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rg18");
mkdirSync(recetteDir, { recursive: true });
const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`), type: "jpeg", quality: 70, fullPage: false,
});

test("lot RG18 — une seule plume, Rédigé seulement sur geste", async ({ page }) => {
  test.setTimeout(90_000);
  const storyPosts = [];
  page.on("request", (req) => {
    let path = "";
    try { path = new URL(req.url()).pathname; } catch { path = req.url(); }
    if (req.method() === "POST" && path === "/ici/story") storyPosts.push(req.url());
  });

  const official = await probeOfficial(page);
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);
  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("film-style-raw")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("film-style-written")).toBeVisible();
  expect(storyPosts, "aucun POST /ici/story tant que Brut").toEqual([]);

  if (!official) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions sac/film sautées ; barre, Suivre, Brut et absence /ici/story gardés",
    });
    await showLeftPanel(page);
    await shot(page, "01-fiche-brut");
    await shot(page, "02-fiche-redige");
    return;
  }

  const bag = await page.request.get("/ici?lat=46.15&lon=-1.16&thin=1", { timeout: 12_000 })
    .then((r) => (r.ok() ? r.json() : null))
    .catch(() => null);
  if (bag && typeof bag === "object") {
    expect(bag.filmPhrases, "le sac /ici porte les phrases de règles").toBeTruthy();
  }

  const warm = await page.request.get("/ici/warm/status", { timeout: 8_000 })
    .then((r) => (r.ok() ? r.json() : null))
    .catch(() => null);
  if (warm && typeof warm === "object") {
    const stories = warm.stories || {};
    expect(stories.status, "pas d'étape stories en cours").not.toBe("running");
    if (stories.skipped) expect(stories.skipped).toBe("on-demand");
  }

  await showLeftPanel(page);
  await page.getByTestId("ici-tab-now").click().catch(() => {});
  expect(storyPosts, "toujours aucun POST /ici/story en Brut").toEqual([]);
  await shot(page, "01-fiche-brut");

  const written = page.getByTestId("film-style-written");
  const enabled = await written.isEnabled().catch(() => false);
  if (!enabled) {
    test.info().annotations.push({
      type: "Rédigé",
      description: "pilule Rédigé encore verrouillée (film written pas prêt) — 02 = Brut, pas d'appel Super",
    });
    await shot(page, "02-fiche-redige");
    expect(storyPosts).toEqual([]);
    return;
  }

  await written.click();
  await expect(written).toHaveAttribute("aria-pressed", "true");
  await page.waitForTimeout(2_000);
  await shot(page, "02-fiche-redige");
  const raw = page.getByTestId("film-style-raw");
  await raw.click();
  await expect(raw).toHaveAttribute("aria-pressed", "true");
});
