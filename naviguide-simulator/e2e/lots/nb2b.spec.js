// Barre du film : une ligne « Modèles » / « Models » nomme le modèle qui a
// répondu, en texte seul. Sans API, les assertions qui lisent le film rédigé
// sont sautées ; l'absence de logo reste exigée.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema } from "../helpers.js";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/nb2b");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.webp`),
  type: "webp",
  quality: 85,
  fullPage: false,
});

const LOGO_RE = /nvidia|nebius|token[\s-]?factory/i;

async function thirdPartyLogoHits(page) {
  return page.evaluate((source) => {
    const re = new RegExp(source, "i");
    const hits = [];
    for (const el of document.querySelectorAll("img, svg, [style*='url(']")) {
      const blob = [
        el.tagName,
        el.getAttribute("src"),
        el.getAttribute("alt"),
        el.getAttribute("aria-label"),
        el.getAttribute("style"),
      ].filter(Boolean).join(" ");
      if (re.test(blob)) hits.push(blob.slice(0, 180));
    }
    return hits;
  }, LOGO_RE.source);
}

test("ligne Modèles du film : le modèle nommé, aucun logo", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);
  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");

  expect(await thirdPartyLogoHits(page), "image de logo NVIDIA, Nebius ou Token Factory").toEqual([]);
  await shot(page, "01-suivre");

  const official = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  if (!official || !official.ok()) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — libellé du film rédigé sauté ; absence de logo gardée",
    });
    return;
  }

  const written = page.getByTestId("film-style-written");
  const enabled = await written.isEnabled().catch(() => false);
  if (!enabled) {
    test.info().annotations.push({
      type: "film rédigé absent",
      description: "pilule Rédigé inactive — ligne Modèles sautée ; absence de logo gardée",
    });
    return;
  }

  await written.click();
  const source = page.getByTestId("film-source");
  const visible = await source.isVisible().catch(() => false);
  if (!visible) {
    test.info().annotations.push({
      type: "film rédigé absent",
      description: "ligne source masquée — libellé sauté ; absence de logo gardée",
    });
    return;
  }

  const text = (await source.innerText()).replace(/\s+/g, " ").trim();
  expect(text).toMatch(/Modèles|Models/);
  expect(text).toMatch(/Nemotron|NVIDIA NIM|OpenRouter|Claude|règles|rules/);
  await expect(source.locator("img, svg")).toHaveCount(0);
  expect(await thirdPartyLogoHits(page)).toEqual([]);
  await shot(page, "02-modeles");
});
