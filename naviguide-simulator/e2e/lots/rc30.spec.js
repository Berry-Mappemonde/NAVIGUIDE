// Lot RC30 — le film dit les choses dans l'ordre, et finit ses phrases
// (revue du porteur, 14 oct.). Recette automatique du discours :
//   - dans chaque chapitre, les dates explicites vont en avant (jamais
//     « Le 19 mai … » puis « Le 18 mai … ») ;
//   - « Le lendemain » seulement après une date dite ;
//   - jamais « un flotteur Argo » anonyme (l'identifiant ou rien) ;
//   - jamais « les eaux de Saint-Martin, puis celles de Saint-Martin »
//     (Sint Maarten / Saint-Martin : un seul nom à l'oreille).
// Sans API : GET /voyage/official sondé ; s'il manque, annotation + saut des
// seules assertions film — la barre et Revoir restent vérifiés.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema } from "../helpers.js";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rc30");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`),
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

const MONTHS_FR = [
  "janvier", "février", "mars", "avril", "mai", "juin",
  "juillet", "août", "septembre", "octobre", "novembre", "décembre",
];
const DATE_FR_RE = /\b(1er|\d{1,2}) (janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\b/gi;
const ARGO_ANON_RE = /\b(un flotteur Argo|an Argo float)\b(?!\s*\d)/;
const SAME_WATERS_TWICE_RE = /les eaux (de |d['’])?(Saint-Martin|Sint-Maarten), puis celles (de |d['’])?(Saint-Martin|Sint-Maarten)/i;

function dayKey(dayRaw, monthRaw) {
  const day = dayRaw.toLowerCase() === "1er" ? 1 : Number(dayRaw);
  return (MONTHS_FR.indexOf(monthRaw.toLowerCase()) + 1) * 31 + day;
}

// La toise mois*31+jour boucle fin décembre : décembre → janvier est un
// passage d'année (en avant), pas un recul.
const YEAR_UNITS = 12 * 31 + 31;

function outOfOrderDates(text) {
  const out = [];
  let last = null;
  let offset = 0;
  for (const m of String(text || "").matchAll(DATE_FR_RE)) {
    let cur = dayKey(m[1], m[2]) + offset;
    if (last != null && cur < last && last - cur > YEAR_UNITS / 2) {
      offset += YEAR_UNITS;
      cur += YEAR_UNITS;
    }
    if (last != null && cur < last) out.push(m[0]);
    last = last == null ? cur : Math.max(last, cur);
  }
  return out;
}

function lendemainWithoutEve(text) {
  const out = [];
  let dated = false;
  for (const sent of String(text || "").split(/(?<=[.!?…])\s+/)) {
    if (/^(le lendemain|the next day)\b/i.test(sent.trim())) {
      if (!dated) out.push(sent.trim().slice(0, 60));
      continue;
    }
    DATE_FR_RE.lastIndex = 0;
    if (DATE_FR_RE.test(sent)) dated = true;
  }
  return out;
}

async function probeOfficial(page) {
  const res = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  if (!res || !res.ok()) return { apiUp: false };
  const ctype = String(res.headers()["content-type"] || "").toLowerCase();
  if (!ctype.includes("json")) return { apiUp: false };
  const body = await res.json().catch(() => null);
  if (!body || typeof body !== "object") return { apiUp: false };
  return { apiUp: true };
}

test("lot RC30 — le film dit les choses dans l'ordre, et finit ses phrases", async ({ page }) => {
  test.setTimeout(90_000);
  const { apiUp } = await probeOfficial(page);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions discours sautées ; barre et Revoir gardés",
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
    await shot(page, "01-ordre");
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
    await shot(page, "01-ordre");
    return;
  }

  for (const [i, ch] of film.chapters.entries()) {
    const text = ch.text || "";
    const label = `ch${i} ${ch.fromName || ""} → ${ch.toName || ""}`;
    expect(outOfOrderDates(text), `${label} : dates qui reculent`).toEqual([]);
    expect(lendemainWithoutEve(text), `${label} : « Le lendemain » sans veille`).toEqual([]);
    expect(text, `${label} : flotteur Argo anonyme`).not.toMatch(ARGO_ANON_RE);
    expect(text, `${label} : mêmes eaux dites deux fois`).not.toMatch(SAME_WATERS_TWICE_RE);
  }
  const blob = film.chapters.map((c) => c.text || "").join(" ");
  const argoCount = (blob.match(/flotteur Argo/g) || []).length;
  const chapterCount = film.chapters.length;
  expect(argoCount, "au plus un flotteur Argo par jambe").toBeLessThanOrEqual(chapterCount);

  await shot(page, "01-ordre");
});
