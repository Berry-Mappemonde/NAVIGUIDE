// Lot RB5 — le film dit le voyage officiel (Saint-Maur, 15 mai 2026, milles nautiques).
// Sans API : récit local + script brut local. Les assertions de départ / unités
// tiennent seules. GET /voyage/official/film : seulement si l'API répond.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-rb5/${name}.jpg`,
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

const ROUTE = ["Saint-Maur", "La Rochelle", "Ajaccio", "Fort-de-France"];

function firstIndex(text, needle) {
  return String(text).search(new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"));
}

function assertRouteOrder(text, label) {
  const hits = ROUTE.map((n) => ({ n, i: firstIndex(text, n) })).filter((h) => h.i >= 0);
  expect(hits.length, `${label} : escales manquantes`).toBeGreaterThanOrEqual(2);
  for (let i = 1; i < hits.length; i++) {
    expect(hits[i - 1].i, `${label} : ${hits[i].n} avant ${hits[i - 1].n}`).toBeLessThan(hits[i].i);
  }
}

function assertOfficialDepart(text, lang, { spoken = false } = {}) {
  expect(text, "Saint-Maur en tête").toMatch(/Saint-Maur/);
  if (lang === "en") {
    expect(text, "date officielle EN").toMatch(/15 May 2026/);
  } else {
    expect(text, "date officielle FR").toMatch(/15 mai 2026/);
  }
  expect(text, "pas de 2027").not.toMatch(/2027/);
  expect(text, "pas un départ de La Rochelle").not.toMatch(/quitté La Rochelle|left La Rochelle/i);
  if (spoken) expect(text, "pas de nm nu dans le texte déclamé").not.toMatch(/\bnm\b/);
}

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
  const isOn = async () => /bg-cyan-700/.test((await cinema.getAttribute("class")) || "");
  if (!(await cinema.isVisible().catch(() => false))) return;
  if (!(await isOn())) return;
  await page.keyboard.press("Escape");
  if (!(await isOn())) return;
  await cinema.click();
}

async function showLeftPanel(page) {
  await leaveCinema(page);
  const story = page.getByTestId("expedition-story");
  if (await story.isVisible().catch(() => false)) return;
  const toggle = page.locator(".naviguide-sidebar-toggle--left");
  if (await toggle.isVisible().catch(() => false)) await toggle.click();
  await expect(story).toBeVisible({ timeout: 15_000 });
}

async function showRightPanel(page) {
  const heading = page.getByText(/^(Escales|Stops)$/i).first();
  if (await heading.isVisible().catch(() => false)) return;
  const toggle = page.locator(".naviguide-sidebar-toggle--right");
  if (await toggle.isVisible().catch(() => false)) await toggle.click();
}

async function switchLang(page, code) {
  const btn = page.getByTestId(`lang-${code}`);
  if (!(await btn.isVisible().catch(() => false))) {
    const right = page.locator(".naviguide-sidebar-toggle--right");
    if (await right.isVisible().catch(() => false)) await right.click();
  }
  await expect(btn).toBeVisible({ timeout: 15_000 });
  await btn.click();
}

async function muteVoice(page) {
  const listen = page.getByTestId("listen");
  if (await listen.isVisible().catch(() => false)) {
    if (await listen.getAttribute("aria-pressed") === "true") await listen.click();
  }
}

async function probeOfficial(page) {
  for (let i = 0; i < 8; i += 1) {
    const ok = await page.request.get("/voyage/official", { timeout: 4000 }).then((r) => r.ok()).catch(() => false);
    if (ok) return true;
    await page.waitForTimeout(400);
  }
  return false;
}

async function legendNames(page) {
  await showRightPanel(page);
  return page.evaluate(() => {
    const head = [...document.querySelectorAll("div")].find((el) => /^(Escales|Stops)$/i.test((el.textContent || "").trim()));
    const list = head?.parentElement?.querySelector("ul");
    if (!list) return [];
    return [...list.querySelectorAll("li span.font-medium")].map((n) => (n.textContent || "").trim()).filter(Boolean);
  });
}

async function storyBlob(page) {
  const paras = page.getByTestId("story-paragraph");
  const n = await paras.count();
  const texts = [];
  for (let i = 0; i < n; i++) texts.push((await paras.nth(i).innerText()).trim());
  return { n, text: texts.join(" ") };
}

test("lot RB5 — film officiel : Saint-Maur le 15 mai 2026, milles nautiques", async ({ page }) => {
  test.setTimeout(90_000);
  const apiUp = await probeOfficial(page);

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await showLeftPanel(page);

  const story = page.getByTestId("expedition-story");
  await expect(story).toBeVisible({ timeout: 15_000 });
  const frStory = await storyBlob(page);
  if (frStory.n >= 1) {
    assertOfficialDepart(frStory.text, "fr");
    assertRouteOrder(frStory.text, "récit FR");
  } else {
    test.info().annotations.push({
      type: "sans récit",
      description: "récit sidebar vide — tête Saint-Maur non vérifiée à l'écran",
    });
  }

  await muteVoice(page);
  await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("replay-start").click();
  const subtitle = page.getByTestId("film-subtitle");
  await expect(subtitle).toBeVisible({ timeout: 8_000 });
  const subFr = (await subtitle.innerText()).trim();
  expect(subFr, "sous-titre chapitre 1").not.toBe("");
  assertOfficialDepart(subFr, "fr", { spoken: true });
  expect(subFr).toMatch(/La Rochelle/);

  const names = await legendNames(page);
  if (names.length >= 2) {
    const blob = `${subFr} ${frStory.text}`;
    assertRouteOrder(blob, "sous-titre + récit vs liste");
    const legendHits = ROUTE.filter((n) => names.some((x) => new RegExp(n, "i").test(x)));
    expect(legendHits[0], `liste droite commence par ${names[0]}`).toBe("Saint-Maur");
  }

  await shot(page, "01-depart");

  if (apiUp) {
    const film = await page.request.get("/voyage/official/film?lang=fr&seconds=150", { timeout: 8000 })
      .then((r) => (r.ok() ? r.json() : null))
      .catch(() => null);
    expect(film?.chapters?.length, "film FR : des chapitres").toBeGreaterThan(0);
    const blob = (film.chapters || []).map((c) => c.text || "").join(" ");
    assertOfficialDepart(film.chapters[0].text || "", "fr", { spoken: true });
    assertRouteOrder(blob, "film API FR");
    expect(blob, "nm nu dans le film API").not.toMatch(/\bnm\b/);
    expect(blob).toMatch(/milles nautiques|mille nautique|Aujourd/i);
  } else {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — chapitres film serveur non vérifiés",
    });
  }

  await switchLang(page, "en");
  await expect(page.getByTestId("view-suivre")).toContainText(/Follow/i);
  const stopBtn = page.getByTestId("replay-stop");
  if (await stopBtn.isVisible().catch(() => false)) await stopBtn.click();
  await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 8_000 });
  await page.getByTestId("replay-start").click();
  await expect(subtitle).toBeVisible({ timeout: 8_000 });
  const subEn = (await subtitle.innerText()).trim();
  if (subEn) {
    assertOfficialDepart(subEn, "en", { spoken: true });
  }

  if (apiUp) {
    const filmEn = await page.request.get("/voyage/official/film?lang=en&seconds=150", { timeout: 8000 })
      .then((r) => (r.ok() ? r.json() : null))
      .catch(() => null);
    expect(filmEn?.chapters?.length, "film EN : des chapitres").toBeGreaterThan(0);
    const blob = (filmEn.chapters || []).map((c) => c.text || "").join(" ");
    assertOfficialDepart(filmEn.chapters[0].text || "", "en", { spoken: true });
    expect(blob, "nm nu dans le film EN").not.toMatch(/\bnm\b/);
  }
});
