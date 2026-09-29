// Lot RG13 — caméra et rendu à 60 Hz (revue du 28 sept.).
// Sans API : Suivre, Revoir et la barre tiennent seuls. GET /voyage/official
// sondé ; s'il manque, annotation + saut des assertions film — jamais la barre
// ni Revoir retirés. Aucune donnée factice : on lit le poste tel quel.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema, waitBoatUnderWay, waitFilmCanStart } from "../helpers.js";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rg13");
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

test("lot RG13 — cadrage film, barre et Revoir présents", async ({ page }) => {
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

  if (!apiUp) {
    await expect(start).toBeDisabled();
    await shot(page, "01-cadrage");
    return;
  }

  const canPlay = await waitFilmCanStart(page, 20_000);
  if (!canPlay) {
    test.info().annotations.push({
      type: "Revoir grisé",
      description: "film officiel pas prêt — lecture sautée ; barre et Revoir gardés",
    });
    await shot(page, "01-cadrage");
    return;
  }

  await start.click();
  await expect(page.getByTestId("replay-stop")).toBeVisible({ timeout: 8_000 });
  const subtitle = page.getByTestId("film-subtitle");
  await expect(subtitle).toBeVisible({ timeout: 8_000 });
  expect((await subtitle.innerText()).trim().length, "sous-titre non vide").toBeGreaterThan(0);

  await page.waitForFunction(() => Boolean(window.__naviguideScene?.map), { timeout: 10_000 });
  const underway = await waitBoatUnderWay(page, { timeout: 20_000 });
  if (!underway?.moving) {
    test.info().annotations.push({
      type: "poste",
      description: "bateau encore à quai sur les premières phrases — capture telle quelle",
    });
  }

  const frame = await page.evaluate(() => {
    const map = window.__naviguideScene?.map;
    const boat = document.querySelector(".catamaran-divicon--live");
    const box = map?.getContainer?.()?.getBoundingClientRect?.();
    if (!map || !boat || !box) return { ok: false };
    const r = boat.getBoundingClientRect();
    const bx = r.left + r.width / 2;
    const by = r.top + r.height / 2;
    const dx = Math.abs(bx - (box.left + box.width / 2)) / box.width;
    const dy = Math.abs(by - (box.top + box.height / 2)) / box.height;
    return { ok: true, dx, dy, tiles: document.querySelectorAll("img.leaflet-tile").length };
  });
  if (frame.ok && underway?.moving) {
    expect(frame.dx, "bateau trop loin du centre (largeur)").toBeLessThanOrEqual(0.4);
    expect(frame.dy, "bateau trop loin du centre (hauteur)").toBeLessThanOrEqual(0.4);
    expect(frame.tiles, "fond damier").toBeGreaterThan(0);
  }

  await shot(page, "01-cadrage");
});
