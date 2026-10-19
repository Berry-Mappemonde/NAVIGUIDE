// La revue d'image ne change pas l'écran. Sans API, les boutons de la barre restent vérifiés.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { dismissNotForNav } from "../helpers.js";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/fr1");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.webp`),
  type: "webp",
  quality: 85,
  fullPage: false,
});

test("La barre film garde Suivre, Revoir et Cinéma", async ({ page }) => {
  test.setTimeout(60_000);
  const official = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  const apiUp = Boolean(official && official.ok());
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — lecture du film sautée ; barre et boutons gardés",
    });
  }

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByRole("button", { name: /Suivre l.expédition/ })).toBeVisible();
  await expect(page.getByTestId("replay-start")).toBeVisible();
  await expect(page.getByRole("button", { name: /Revoir l.expédition/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /^(Cinéma|Cinema)$/ })).toBeVisible();
  await expect(page.getByTestId("film-bar")).toBeVisible();
  if (apiUp) {
    const film = await page.request.get("/voyage/official/film?lang=fr&seconds=150", { timeout: 12_000 })
      .then((response) => (response.ok() ? response.json() : null))
      .catch(() => null);
    const chapters = Array.isArray(film?.chapters) ? film.chapters.length : 0;
    if (!film || film.status !== "ready" || !chapters) {
      test.info().annotations.push({
        type: "film absent",
        description: "film 2:30 sans chapitres prêts — pilule non affirmée",
      });
    } else {
      await expect(page.getByRole("button", { name: "2:30", exact: true })).toBeVisible({ timeout: 20_000 });
    }
  }
  await shot(page, "01-suivre");

  await page.getByTestId("view-tracer").click();
  await expect(page.getByTestId("view-tracer")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "false");
  await expect(page.getByRole("button", { name: "Tracer", exact: true })).toBeVisible();
  await shot(page, "02-tracer");
});
