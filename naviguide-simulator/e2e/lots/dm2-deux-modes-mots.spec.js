// Lot DM2 — les mots des deux modes (après DM1, docs/PLAN_DEUX_MODES_2026-09-29.md) :
// chaque texte visible ou lu dit Suivre / Tracer (FR) et Follow / Plot (EN) ;
// aucun mot « Simulation » à l'écran, ni dans les title / aria-label.
// Le comportement ne change pas ; le mode interne (VIEW_SIMULATION) est renommé par DM3.
// Sans API : tout tient seul (textes, commutateur, ordres skipper, langue) —
// GET /voyage/official est sondé mais aucune assertion n'en dépend.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema, probeOfficial, showLeftPanel } from "../helpers.js";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-dm2");
mkdirSync(recetteDir, { recursive: true });
const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`), type: "jpeg", quality: 70, fullPage: false,
});

// Aucun élément dont le texte, le title ou l'aria-label contient « simulation »
// (insensible à la casse : couvre « Quitter la simulation », « Exit simulation »…).
async function expectNoSimulationWord(page, where) {
  expect(await page.getByText(/simulation/i).count(), `texte « Simulation » (${where})`).toBe(0);
  expect(
    await page.locator('[title*="simulation" i], [aria-label*="simulation" i]').count(),
    `title/aria-label « Simulation » (${where})`,
  ).toBe(0);
}

async function showToolsPanel(page) {
  await leaveCinema(page);
  const orders = page.getByTestId("skipper-orders");
  if (await orders.isVisible({ timeout: 1500 }).catch(() => false)) return;
  const toggle = page.locator(".naviguide-sidebar-toggle--right");
  if (await toggle.isVisible().catch(() => false)) await toggle.evaluate((el) => el.click());
  await expect(orders).toBeVisible({ timeout: 15_000 });
}

test("lot DM2 — Suivre / Tracer dans chaque texte, aucun « Simulation » à l'écran (FR puis EN)", async ({ page }) => {
  test.setTimeout(120_000);
  const errors = [];
  page.on("pageerror", (err) => errors.push(String(err)));

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await probeOfficial(page); // sonde seulement : aucune assertion ne dépend de l'API

  // (a) Accueil FR : le commutateur s'annonce « Suivre l'expédition ou Tracer » ;
  // l'info-bulle de la pilule Tracer dit Tracer, jamais Simulation.
  await expect(page.getByTestId("film-view-switch")).toHaveAttribute(
    "aria-label", "Suivre l’expédition ou Tracer",
  );
  await expect(page.getByTestId("view-tracer")).toHaveAttribute(
    "title", "Tracer — jouer la route Berry-Mappemonde ou la vôtre : date de départ, Play, calculs",
  );

  // (b) Panneaux ouverts, accueil FR : aucun mot « Simulation » nulle part.
  await showLeftPanel(page);
  await expectNoSimulationWord(page, "accueil FR");
  await shot(page, "01-accueil");

  // (c) Tracer + panneau droit : les ordres skipper disent « cette jambe (Tracer) ».
  await page.getByTestId("view-tracer").click();
  await expect(page.getByTestId("view-tracer")).toHaveAttribute("aria-checked", "true");
  await showToolsPanel(page);
  await page.getByTestId("skipper-orders").evaluate((el) => { el.open = true; });
  await expect(page.getByTestId("skipper-horizon")).toContainText("cette jambe (Tracer)");
  await expectNoSimulationWord(page, "Tracer FR, panneaux ouverts");

  // (d) Anglais : Follow / Plot partout, toujours aucun « Simulation ».
  const en = page.getByTestId("lang-en");
  await expect(en).toBeVisible({ timeout: 10_000 });
  await en.click();
  await expect(page.getByTestId("view-suivre")).toContainText(/Follow/i, { timeout: 10_000 });
  await expect(page.getByTestId("film-view-switch")).toHaveAttribute(
    "aria-label", "Follow the expedition or Plot",
  );
  await expect(page.getByTestId("view-tracer")).toHaveText("Plot");
  await expect(page.getByTestId("skipper-horizon")).toContainText("this leg (Plot)");
  await expectNoSimulationWord(page, "Tracer EN");

  // (e) Retour à l'accueil (Suivre) en anglais pour la capture.
  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await leaveCinema(page); // Suivre rouvre le cinéma (RF7)
  await showLeftPanel(page);
  await expectNoSimulationWord(page, "accueil EN");
  await shot(page, "02-en");

  expect(errors, `erreurs de page : ${errors.join(" | ")}`).toEqual([]);
});
