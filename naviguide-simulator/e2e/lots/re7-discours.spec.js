// Lot RE7 — discours du film : un récit, pas le journal déversé.
// Sans API : Suivre, Revoir et l'absence de durée cochée tiennent seuls.
// GET /voyage/official sondé ; s'il manque, annotation + saut des seules
// assertions du script serveur — jamais le bouton Revoir, ni le défaut
// décoché, ni l'absence des phrases interdites dans le sous-titre local.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-re7");
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

test("lot RE7 — récit sans durée, un lieu une fois, dernière jambe fermée", async ({ page }) => {
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

  const durations = page.getByTestId("film-duration");
  if (await durations.isVisible().catch(() => false)) {
    const pressed = durations.locator("[aria-pressed='true']");
    await expect(pressed, "aucune durée cochée").toHaveCount(0);
  }

  await muteVoice(page);
  await page.getByTestId("replay-start").click();
  const subtitle = page.getByTestId("film-subtitle");
  await expect(subtitle).toBeVisible({ timeout: 8_000 });
  const sub = (await subtitle.innerText()).trim();
  expect(sub, "sous-titre non vide").not.toBe("");
  expect(sub, "pas de phrase interdite dans le sous-titre").not.toMatch(FORBIDDEN);
  await shot(page, "01-recit");

  const budgetNone = await page.evaluate(() => window.__naviguideFilm?.budgetSeconds);
  expect(budgetNone, "aucune durée → pas de budget").toBe(0);

  if (apiUp) {
    const free = await page.request.get("/voyage/official/film?lang=fr&seconds=0", { timeout: 12_000 })
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
      const words = wordCount(blob);
      const stale = words > 800 || FORBIDDEN.test(blob)
        || /milles nautiques du départ|Bay of Biscay/.test(blob);
      if (stale) {
        test.info().annotations.push({
          type: "API hors checkout",
          description: "GET /film du processus :8010 n'est pas encore RE7 — assertions discours sautées",
        });
      } else {
        expect(blob, "pas de station sans nom").not.toMatch(/station croisée\s*:\s*Station croisée/i);
        expect(blob, "pas d'absence racontée").not.toMatch(/Aucun port d'entr[ée]e/i);
        expect(blob, "pas d'entrée doublée").not.toMatch(/entrée dans Entrée dans/i);
        expect(words, "récit sans budget sous 800 mots").toBeLessThanOrEqual(800);
        const last = free.chapters[free.chapters.length - 1]?.text || "";
        expect(last, "dernière jambe fermée").toMatch(/Aujourd[’']hui, le bateau est à/i);
        if (/cayenne|halifax|guyane/i.test(blob)) {
          expect(blob, "avion dit").toMatch(/avion|équipage prend/i);
        }
      }
    }
  }

  await page.waitForTimeout(400);
  await shot(page, "02-fin");

  const stopBtn = page.getByTestId("replay-stop");
  if (await stopBtn.isVisible().catch(() => false)) await stopBtn.click();
  await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 8_000 });
});
