// Badge de source : texte seul, aucun logo NVIDIA, Nebius ou Token Factory.
// Sans API : GET /voyage/official sondé ; s'il ne répond pas, les assertions
// qui lisent le film rédigé sont sautées. L'absence de logo reste exigée.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema, probeOfficial } from "../helpers.js";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/nb1");
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

test("source en texte, aucun logo tiers", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);
  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");

  const logos = await thirdPartyLogoHits(page);
  expect(logos, "image de logo NVIDIA, Nebius ou Token Factory").toEqual([]);
  const badges = page.locator("[data-llm-source]");
  const badgeCount = await badges.count();
  for (let i = 0; i < badgeCount; i += 1) {
    await expect(badges.nth(i).locator("img, svg")).toHaveCount(0);
  }
  await shot(page, "01-suivre-sans-logo");

  const official = await probeOfficial(page);
  if (!official) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — libellé du film rédigé sauté ; absence de logo gardée",
    });
    return;
  }

  const filmRes = await page.request.get("/voyage/official/film?lang=fr&style=written&seconds=150", { timeout: 12_000 }).catch(() => null);
  const filmType = String(filmRes?.headers()?.["content-type"] || "").toLowerCase();
  const film = filmRes && filmRes.ok() && filmType.includes("json")
    ? await filmRes.json().catch(() => null)
    : null;
  if (!film?.hasWritten || !film.source) {
    test.info().annotations.push({
      type: "film rédigé absent",
      description: "film rédigé non servi — libellé sauté ; absence de logo gardée",
    });
    return;
  }

  const written = page.getByTestId("film-style-written");
  const enabled = await expect(written).toBeEnabled({ timeout: 15_000 }).then(() => true).catch(() => false);
  if (!enabled) {
    test.info().annotations.push({
      type: "film rédigé absent",
      description: "pilule Rédigé inactive — libellé sauté ; absence de logo gardée",
    });
    return;
  }

  await written.click();
  const source = page.getByTestId("film-source");
  await expect(source).toBeVisible({ timeout: 8_000 });
  await expect(source.locator("img, svg")).toHaveCount(0);
  const text = (await source.innerText()).replace(/\s+/g, " ").trim();
  expect(text.length).toBeGreaterThan(0);
  const id = String(film.source).toLowerCase();
  if (/openrouter|gpt-4o|claude/.test(id)) {
    expect(text).not.toMatch(/Token Factory/);
    expect(text).toMatch(/OpenRouter|Claude/);
  } else if (/gpt-oss|\bnim\b|nvidia-/.test(id)) {
    expect(text).toMatch(/NVIDIA NIM/);
    expect(text).not.toMatch(/Token Factory/);
  } else if (/nemotron|token-factory|lightning|ultra/.test(id)) {
    expect(text).toMatch(/Nemotron/);
    expect(text).toMatch(/Token Factory/);
    expect(text).toMatch(/NVIDIA/);
    expect(text).toMatch(/Nebius/);
  }
  expect(await thirdPartyLogoHits(page)).toEqual([]);
  await shot(page, "02-source-redige");
});
