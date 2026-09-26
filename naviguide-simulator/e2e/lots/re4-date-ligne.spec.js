// Lot RE4 — changer la date de la barre (Suivre) recalcule la ligne d'état
// (année, jour de voyage) ; remettre le défaut restaure la ligne LIVE ;
// le départ de la Simulation ne bouge pas.
// Sans API : champ date, ligne d'état (horloge locale) et départ Simulation
// tiennent seuls. GET /voyage/official sondé ; s'il manque, annotation +
// saut des seules assertions qui en dépendent — jamais le champ, ni le
// décalage d'année, ni l'indépendance du départ Simulation.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-re4");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`),
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

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

function rightPanelOpen(page) {
  return page.locator(".naviguide-sidebar-panel.right-0").first().evaluate((el) => (
    !el.className.includes("translate-x-full")
  ));
}

async function showToolsPanel(page) {
  await leaveCinema(page);
  if (await rightPanelOpen(page).catch(() => false)) return;
  const toggle = page.locator(".naviguide-sidebar-toggle--right");
  if (await toggle.isVisible().catch(() => false)) await toggle.click();
  await expect.poll(() => rightPanelOpen(page), { timeout: 10_000 }).toBe(true);
}

function dateInput(page, testId) {
  return page.getByTestId(testId).locator("input").first();
}

async function probeOfficial(request) {
  const official = await request.get("/voyage/official", { timeout: 4000 }).catch(() => null);
  if (!official || !official.ok()) return null;
  const ct = official.headers()["content-type"] || "";
  if (!ct.includes("json")) return null;
  const body = await official.json().catch(() => null);
  return body && typeof body === "object" ? body : null;
}

test("lot RE4 — date de la barre pilote la ligne d'état, Simulation inchangée", async ({ page, request }) => {
  test.setTimeout(90_000);
  const officialBody = await probeOfficial(request);
  const apiUp = Boolean(officialBody);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions LIVE serveur sautées",
    });
  }

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("scene-load-mask").waitFor({ state: "hidden", timeout: 25_000 }).catch(() => {});

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await leaveCinema(page);
  await expect(page.getByTestId("replay-departure")).toBeVisible({ timeout: 15_000 });
  const replayDate = dateInput(page, "replay-departure-field");
  await expect(replayDate).toHaveValue("15/05/2026");

  const clock = page.getByTestId("clock-line");
  await expect(clock).toBeVisible({ timeout: 15_000 });
  const lineBefore = (await clock.innerText()).trim();
  expect(lineBefore, "ligne d'état initiale").toMatch(/j\d+|d\d+/);
  if (/\d{4}/.test(lineBefore)) {
    expect(lineBefore).toMatch(/2026/);
  }

  await replayDate.fill("15/05/2025");
  await expect(replayDate).toHaveValue("15/05/2025");

  await expect.poll(async () => (await clock.innerText()).trim(), { timeout: 8_000 })
    .toMatch(/2025/);
  const line2025 = (await clock.innerText()).trim();
  expect(line2025, "année 2025 après changement de date").toMatch(/2025/);
  expect(line2025, "jour de voyage toujours dérivé").toMatch(/j\d+|d\d+/);
  expect(line2025, "la ligne a changé, pas seulement le champ").not.toBe(lineBefore);
  if (apiUp && /LIVE/.test(lineBefore)) {
    expect(line2025, "LIVE reste sur la ligne décalée").toMatch(/LIVE/);
  }
  await shot(page, "01-ligne-2025");

  await replayDate.fill("15/05/2026");
  await expect(replayDate).toHaveValue("15/05/2026");
  await expect.poll(async () => (await clock.innerText()).trim(), { timeout: 8_000 })
    .toBe(lineBefore);
  const lineRestored = (await clock.innerText()).trim();
  expect(lineRestored, "retour au défaut = ligne d'origine").toBe(lineBefore);
  if (/\d{4}/.test(lineRestored)) {
    expect(lineRestored).toMatch(/2026/);
  }
  await shot(page, "02-retour");

  await page.getByTestId("view-simulation").click();
  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
  await showToolsPanel(page);
  const simDate = dateInput(page, "departure-field");
  await expect(simDate).toBeVisible({ timeout: 15_000 });
  const simValue = await simDate.inputValue();
  expect(simValue, "départ Simulation distinct du replay 2025").not.toBe("15/05/2025");
});
