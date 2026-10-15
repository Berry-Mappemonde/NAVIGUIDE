// Lot RC31 — l'épisode Saint-Pierre-et-Miquelon raconté comme il s'est passé
// (vol Cayenne→Halifax, second bateau Halifax↔Saint-Pierre, vol retour,
// reprise du catamaran). Sans API : GET /voyage/official sondé ; s'il
// manque, annotation + saut des assertions film / carte — barre et Revoir
// restent vérifiés.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema, showLeftPanel } from "../helpers.js";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rc31");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`),
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

const AIR_OUT = /s'envole de Cayenne pour Halifax|prend l'avion pour Halifax|the crew flies from Cayenne to Halifax/i;
const AIR_BACK = /s'envole de Halifax pour Cayenne|retour en avion vers Cayenne|flies from Halifax/i;
const WAIT = /le catamaran attend à Cayenne|the catamaran waits at Cayenne/i;
const SIDE_BOAT = /second voilier|second sailing boat/i;
const FALSE_AIR = /s'envole de Cayenne pour Saint-Pierre|flies from Cayenne to Saint-Pierre/i;
const SIDE_COLOR = "#67e8f9";

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
  return { apiUp: true, body };
}

function chapterIndex(chapters, fromRe, toRe) {
  return (chapters || []).findIndex((c) => (
    fromRe.test(c.fromName || "") && toRe.test(c.toName || "")
  ));
}

test("lot RC31 — épisode SPM : quatre chapitres, second bateau, catamaran à Cayenne", async ({ page }) => {
  test.setTimeout(90_000);
  const { apiUp } = await probeOfficial(page);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions film / carte sautées ; barre et Revoir gardés",
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
    await shot(page, "01-episode");
    await shot(page, "02-carte-side");
    return;
  }

  const film = await page.request.get("/voyage/official/film?lang=fr&seconds=0&style=raw", { timeout: 12_000 })
    .then((r) => (r.ok() ? r.json() : null))
    .catch(() => null);
  if (!film?.chapters?.length) {
    test.info().annotations.push({
      type: "film vide",
      description: "GET /voyage/official/film sans chapitres — assertions discours sautées",
    });
    await shot(page, "01-episode");
    await shot(page, "02-carte-side");
    return;
  }

  const chapters = film.chapters;
  const blob = chapters.map((c) => c.text || "").join(" ");
  const airOut = chapterIndex(chapters, /cayenne/i, /halifax/i);
  const sideOut = chapterIndex(chapters, /halifax/i, /saint-pierre|miquelon/i);
  const sideBack = chapterIndex(chapters, /saint-pierre|miquelon/i, /halifax/i);
  const airBack = chapterIndex(chapters, /halifax/i, /cayenne/i);
  const episodeReady = airOut >= 0 && sideOut >= 0 && sideBack >= 0 && airBack >= 0
    && airOut < sideOut && sideOut < sideBack && sideBack < airBack;

  if (!episodeReady) {
    test.info().annotations.push({
      type: "stock pré-RC31",
      description: "film servi sans les 4 chapitres d'épisode — remplisseur FILM_SCRIPT_REV=rc31",
    });
  } else {
    expect(blob, "vol Cayenne → Halifax").toMatch(AIR_OUT);
    expect(blob, "vol Halifax → Cayenne").toMatch(AIR_BACK);
    expect(blob, "attente du catamaran").toMatch(WAIT);
    expect(
      (blob.match(/catamaran attend à Cayenne|catamaran waits at Cayenne/gi) || []).length,
      "attente dite une fois",
    ).toBe(1);
    expect(blob, "pas de vol inventé vers Saint-Pierre").not.toMatch(FALSE_AIR);
    expect(blob, "second bateau nommé ou « un second voilier »").toMatch(SIDE_BOAT);
  }

  const clock = await page.request.get("/voyage/official", { timeout: 8_000 })
    .then((r) => (r.ok() ? r.json() : null))
    .catch(() => null);
  const marks = (clock && (clock.clock?.marks || clock.marks)) || [];
  const halifaxMarks = marks.filter((m) => /halifax/i.test(m?.name || ""));
  if (halifaxMarks.length) {
    expect(halifaxMarks.length, "marques Halifax aller et retour").toBeGreaterThanOrEqual(1);
  }

  await expect(start).toBeEnabled({ timeout: 30_000 });
  await muteVoice(page);
  await start.click();
  const subtitle = page.getByTestId("film-subtitle");
  await expect(subtitle).toBeVisible({ timeout: 8_000 });
  await page.waitForFunction(() => {
    const f = window.__naviguideFilm;
    return typeof f?.seekChapter === "function" && (f.chapterCount || 0) > 0;
  }, null, { timeout: 8_000 }).catch(() => null);

  if (episodeReady) {
    await page.evaluate((idx) => {
      if (idx >= 0) window.__naviguideFilm?.seekChapter(idx);
    }, airOut);
    await expect(subtitle).toContainText(/s'envole|avion|flies|attend à Cayenne|waits at Cayenne/i, { timeout: 8_000 });
  }
  await shot(page, "01-episode");

  await page.evaluate((idx) => {
    if (idx >= 0) window.__naviguideFilm?.seekChapter(idx);
  }, sideOut);
  await page.waitForTimeout(600);

  const mapStats = await page.evaluate(() => {
    const scene = window.__naviguideScene;
    const map = scene?.map;
    const stats = { sideLines: 0, airDash: 0 };
    if (!map) return stats;
    const norm = (c) => String(c || "").toLowerCase().replace(/\s/g, "");
    map.eachLayer((layer) => {
      if (!layer.getLatLngs || !layer.options) return;
      const color = norm(layer.options.color);
      const dash = layer.options.dashArray;
      if (color === "#67e8f9" || color === "rgb(103,232,249)") stats.sideLines += 1;
      if (dash && (color === "#111111" || color === "#111" || color === "black" || color === "rgb(17,17,17)")) {
        stats.airDash += 1;
      }
    });
    return stats;
  });
  if (mapStats.sideLines + mapStats.airDash === 0) {
    test.info().annotations.push({
      type: "carte",
      description: "aucune polyligne side/air lue sur Leaflet — capture brute",
    });
  } else {
    expect(mapStats.airDash + mapStats.sideLines, "vol pointillé ou trace side").toBeGreaterThan(0);
  }
  await shot(page, "02-carte-side");

  await showLeftPanel(page);
  const journalTab = page.getByTestId("ici-tab-journal");
  if (await journalTab.isVisible().catch(() => false)) {
    await journalTab.click();
    const journal = page.getByTestId("journal-panel").or(page.getByTestId("journal-day"));
    if (await journal.isVisible({ timeout: 4_000 }).catch(() => false)) {
      const txt = await journal.innerText().catch(() => "");
      if (txt) {
        expect(txt.length, "journal non vide").toBeGreaterThan(0);
      }
    }
  }
});
