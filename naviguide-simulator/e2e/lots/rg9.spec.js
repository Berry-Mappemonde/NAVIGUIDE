// Lot RG9 — client robuste : sans voix, horloge murale ; sous-titre = phrase.
// Sans API : barre et Revoir tiennent seuls. GET /voyage/official sondé ;
// s'il manque, annotation + saut des assertions film — jamais la barre ni Revoir.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema, waitFilmCanStart } from "../helpers.js";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rg9");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`),
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

async function probeOfficial(page) {
  const res = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  if (!res || !res.ok()) return { apiUp: false };
  const ctype = String(res.headers()["content-type"] || "").toLowerCase();
  if (!ctype.includes("json")) return { apiUp: false };
  const body = await res.json().catch(() => null);
  if (!body || typeof body !== "object") return { apiUp: false };
  return { apiUp: true };
}

test("lot RG9 — sans voix le film roule, sous-titre = phrase", async ({ page }) => {
  test.setTimeout(90_000);
  await page.addInitScript(() => {
    try { delete window.speechSynthesis; } catch { /* ignore */ }
    Object.defineProperty(window, "speechSynthesis", { configurable: true, get: () => undefined });
  });

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

  if (!apiUp) {
    await expect(start).toBeDisabled();
    await expect(page.getByTestId("film-subtitle")).toHaveCount(0);
    await shot(page, "01-sous-titre-phrase");
    return;
  }

  const canPlay = await waitFilmCanStart(page, 20_000);
  if (!canPlay) {
    test.info().annotations.push({
      type: "Revoir grisé",
      description: "film officiel pas prêt — lecture sautée ; barre et Revoir gardés",
    });
    await shot(page, "01-sous-titre-phrase");
    return;
  }

  await start.click();
  const subtitle = page.getByTestId("film-subtitle");
  await expect(subtitle).toBeVisible({ timeout: 8_000 });
  await expect(page.getByTestId("replay-stop")).toBeVisible({ timeout: 8_000 });

  const first = (await subtitle.innerText()).trim();
  expect(first.length).toBeGreaterThan(0);
  await page.evaluate((prev) => { window.__rg9FirstSubtitle = prev; }, first);

  await page.waitForTimeout(2500);
  const mid = await page.evaluate(() => {
    const f = window.__naviguideFilm || {};
    return {
      ended: Boolean(f.ended),
      elapsed: Number(f.elapsed) || 0,
      chapterText: String(f.chapterText || ""),
      subtitle: String(f.subtitle || ""),
    };
  });
  expect(mid.ended, "ne doit pas finir à ~2,5 s").toBe(false);
  expect(mid.elapsed).toBeGreaterThan(1.5);
  if (mid.chapterText && mid.subtitle) {
    expect(mid.subtitle.length, "sous-titre = phrase, pas le chapitre").toBeLessThanOrEqual(mid.chapterText.length);
    expect(mid.chapterText.includes(mid.subtitle)).toBeTruthy();
  }

  await page.waitForFunction(() => {
    const el = document.querySelector("[data-testid='film-subtitle']");
    const now = (el?.textContent || "").trim();
    return Boolean(now && now !== window.__rg9FirstSubtitle);
  }, null, { timeout: 30_000 });
  const next = (await subtitle.innerText()).trim();
  expect(next).not.toEqual(first);

  const later = await page.evaluate(() => {
    const f = window.__naviguideFilm || {};
    return { ended: Boolean(f.ended), elapsed: Number(f.elapsed) || 0 };
  });
  expect(later.ended, "sans voix, ended seulement à la fin").toBe(false);
  expect(later.elapsed).toBeGreaterThan(mid.elapsed - 0.2);

  await shot(page, "01-sous-titre-phrase");
});
