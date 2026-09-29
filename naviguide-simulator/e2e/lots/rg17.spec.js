// Lot RG17 — fourchette sous la prochaine escale, ou une ligne de raison.
// Sans API : Suivre + légende tiennent seuls. GET /voyage/official sondé ;
// s'il manque, annotation + saut des seules assertions fourchette / raison —
// jamais la légende retirée, jamais une date inventée.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema, showRightPanel } from "../helpers.js";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rg17");
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
  return { apiUp: true, body };
}

function nextStopName(official) {
  const marks = official?.clock?.marks || official?.marks || [];
  const now = Date.now();
  for (const m of marks) {
    const ts = Date.parse(m?.iso || "");
    if (Number.isFinite(ts) && ts > now && m?.name) return String(m.name);
  }
  return "";
}

test("lot RG17 — fourchette ou raison sous la prochaine escale", async ({ page }) => {
  test.setTimeout(90_000);
  const { apiUp, body: official } = await probeOfficial(page);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — fourchette / raison sautées ; légende gardée",
    });
  }

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await showRightPanel(page);

  const legend = page.getByTestId("escale-legend");
  await expect(legend).toBeVisible({ timeout: 20_000 });
  await legend.scrollIntoViewIfNeeded();

  const legendEta = page.getByTestId("eta-range");

  if (!apiUp) {
    await expect(legendEta).toHaveCount(0);
    await shot(page, "01-legende-escale");
    return;
  }

  const stop = nextStopName(official);
  let eta = null;
  if (stop) {
    const etaRes = await page.request.get(
      `/voyage/official/eta?stop=${encodeURIComponent(stop)}`,
      { timeout: 8000 },
    ).catch(() => null);
    if (etaRes && etaRes.ok()) {
      eta = await etaRes.json().catch(() => null);
    }
  }

  if (!eta || eta.status === "preparing") {
    test.info().annotations.push({
      type: "poste",
      description: "famille eta encore absente du stock figé — aucune date inventée",
    });
    if (eta) {
      expect(eta.members || 0, "sans membres, pas de fourchette").toBe(0);
      expect(eta.p10, "sans membres, pas de p10 inventé").toBeFalsy();
      expect(eta.p90, "sans membres, pas de p90 inventé").toBeFalsy();
    }
    await expect(legendEta).toHaveCount(0);
    await shot(page, "01-legende-escale");
    return;
  }

  expect(eta.status, "plus jamais preparing après une passe").toMatch(/^(ready|unavailable)$/);
  if (eta.status === "ready") {
    expect(Number(eta.members) > 0, "ready sans membres").toBeTruthy();
    expect(eta.p10 && eta.p90, "ready sans fourchette").toBeTruthy();
  } else {
    expect(Number(eta.members || 0), "unavailable avec membres").toBe(0);
    expect(eta.p10, "unavailable n'invente pas p10").toBeFalsy();
    expect(eta.reason, "unavailable sans raison").toBeTruthy();
    expect(eta.nextRetry, "unavailable sans nextRetry").toBeTruthy();
  }

  await expect(legendEta.first()).toBeVisible({ timeout: 25_000 });
  const a = (await legendEta.first().innerText()).trim();
  if (Number(eta.members) > 0) {
    expect(a).toMatch(/arrivée entre le|arrival between/i);
    expect(a).not.toMatch(/p10|membres|members/i);
  } else {
    expect(a).toMatch(/fourchette indisponible|arrival window unavailable/i);
    expect(a).toMatch(/nouvel essai|retry on/i);
    expect(a).not.toMatch(/arrivée entre le|arrival between/i);
  }
  expect(await legendEta.count(), "une seule ligne sous la prochaine escale").toBe(1);
  await legendEta.first().scrollIntoViewIfNeeded();
  await shot(page, "01-legende-escale");
});
