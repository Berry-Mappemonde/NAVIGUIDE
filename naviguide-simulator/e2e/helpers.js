// Contrats UI actuels (RF7, RD9, RE3, RF8, RC18) — partagés par les specs de lots.
import { expect } from "@playwright/test";

export async function dismissNotForNav(page) {
  const modal = page.getByTestId("not-for-nav-modal");
  if (await modal.isVisible({ timeout: 1500 }).catch(() => false)) {
    const ack = page.getByTestId("not-for-nav-ack");
    if (await ack.isVisible().catch(() => false)) await ack.check();
    const ok = page.getByTestId("not-for-nav-accept");
    if (await ok.isVisible().catch(() => false)) {
      await ok.click();
      return;
    }
  }
  const ok = page.getByRole("button", {
    name: /compris|j.ai compris|ok|continuer|accepter|understand|accept/i,
  }).first();
  if (await ok.isVisible({ timeout: 2000 }).catch(() => false)) {
    const ack = page.getByTestId("not-for-nav-ack");
    if (await ack.isVisible().catch(() => false)) await ack.check();
    await ok.click();
  }
}

export function cinemaButton(page) {
  return page.getByRole("button", { name: /^(cinéma|cinema)$/i });
}

export async function cinemaPressed(page) {
  return /bg-cyan-700/.test((await cinemaButton(page).getAttribute("class")) || "");
}

export async function leaveCinema(page) {
  const cinema = cinemaButton(page);
  if (!(await cinema.isVisible().catch(() => false))) return;
  if (!(await cinemaPressed(page))) return;
  await page.keyboard.press("Escape");
  if (!(await cinemaPressed(page))) return;
  await cinema.evaluate((el) => el.click());
}

export async function panelClosed(page, side) {
  const loc = side === "left"
    ? page.locator(".naviguide-sidebar-panel.left-0").first()
    : page.locator(".naviguide-sidebar-panel.right-0").first();
  const cls = (await loc.getAttribute("class")) || "";
  return cls.includes("translate-x-full");
}

export async function showLeftPanel(page) {
  await leaveCinema(page);
  const box = page.getByTestId("ici-maintenant");
  if (await box.isVisible().catch(() => false)) return;
  const toggle = page.locator(".naviguide-sidebar-toggle--left");
  if (await toggle.isVisible().catch(() => false)) await toggle.evaluate((el) => el.click());
  await expect(box).toBeVisible({ timeout: 15_000 });
}

export async function showRightPanel(page) {
  await leaveCinema(page);
  if (!(await panelClosed(page, "right").catch(() => true))) {
    await bringOffscreenFlagsIntoView(page);
    return;
  }
  const toggle = page.locator(".naviguide-sidebar-toggle--right");
  if (await toggle.isVisible().catch(() => false)) await toggle.evaluate((el) => el.click());
  await expect.poll(() => panelClosed(page, "right"), { timeout: 10_000 }).toBe(false);
  await bringOffscreenFlagsIntoView(page);
}

/** Drapeaux Leaflet hors cadre : le scroll de page ne les ramène pas (lot R7). */
export async function bringOffscreenFlagsIntoView(page) {
  await page.evaluate(() => {
    const scene = window.__naviguideScene;
    const map = scene?.map;
    if (!map || !scene.waypointMarkers?.size) return;
    const box = map.getContainer().getBoundingClientRect();
    const off = [];
    for (const marker of scene.waypointMarkers.values()) {
      const el = marker.getElement?.() || marker._icon;
      const r = el?.getBoundingClientRect?.();
      const ll = marker.getLatLng?.();
      if (!ll) continue;
      if (!r || r.width === 0 || r.right < box.left || r.left > box.right || r.bottom < box.top || r.top > box.bottom) {
        off.push([ll.lat, ll.lng]);
      }
    }
    if (!off.length) return;
    map.fitBounds(off, { padding: [48, 48], maxZoom: 7, animate: false });
  });
}

export async function openIciTab(page, testId, slotTestId) {
  await showLeftPanel(page);
  const tab = page.getByTestId(testId);
  await expect(tab).toBeVisible({ timeout: 10_000 });
  await tab.evaluate((el) => el.click());
  if (slotTestId) {
    await expect(tab).toHaveAttribute("aria-selected", "true");
    await expect(page.getByTestId(slotTestId)).toBeAttached({ timeout: 10_000 });
  }
}

export async function openReviewTab(page) {
  await openIciTab(page, "ici-tab-review", "ici-review-slot");
  await expect(page.getByTestId("plan-review")).toBeVisible({ timeout: 10_000 });
  await ensureReviewOpen(page);
}

/** RD9 : dans l'onglet, PlanReview est un `div` (startOpen), plus un `<details>`. */
export async function ensureReviewOpen(page) {
  const review = page.getByTestId("plan-review");
  await expect(review).toBeVisible({ timeout: 10_000 });
  const summary = review.locator("summary");
  if ((await summary.count()) === 0) return;
  const isOpen = await review.evaluate((el) => el.tagName.toLowerCase() !== "details" || el.open);
  if (!isOpen) await summary.click();
}

export async function openStoryTab(page) {
  await openIciTab(page, "ici-tab-story", "ici-story-slot");
}

export async function openJournalTab(page) {
  await openIciTab(page, "ici-tab-journal", "ici-journal-slot");
}

export async function enterSimulation(page) {
  await page.getByTestId("view-simulation").click();
  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
}

export async function enterTracer(page) {
  await showLeftPanel(page);
  const drawBtn = page.getByRole("button", {
    name: /Berry-Mappemonde.*Tracer votre propre route|Tracer votre propre route|Draw your own route/i,
  });
  await expect(drawBtn).toBeVisible({ timeout: 10_000 });
  await drawBtn.scrollIntoViewIfNeeded();
  await drawBtn.click({ force: true });
  await expect(page.getByTestId("drawing-box")).toBeVisible({ timeout: 15_000 });
  await page.evaluate(() => window.__naviguideScene?.beginDrawingWorld?.());
}

export async function probeOfficial(requestOrPage) {
  const req = requestOrPage.request || requestOrPage;
  const official = await req.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  if (!official || !official.ok()) return null;
  const ct = official.headers()["content-type"] || "";
  if (!ct.includes("json")) return null;
  const body = await official.json().catch(() => null);
  return body && typeof body === "object" ? body : null;
}

export async function mapZoom(page) {
  return page.evaluate(() => window.__naviguideScene?.map?.getZoom?.() ?? null);
}

/** Plancher RC18 sur le viewport Playwright 1280×800 : 2.5. */
export const FOLLOW_ZOOM_FLOOR = 2.5;

export async function waitFilmCanStart(page, timeout = 25_000) {
  const start = page.getByTestId("replay-start");
  await expect(start).toBeVisible({ timeout: 15_000 });
  await page.waitForFunction(() => {
    const b = document.querySelector("[data-testid='replay-start']");
    return Boolean(b && !b.disabled && b.getAttribute("aria-disabled") !== "true");
  }, null, { timeout }).catch(() => null);
  return start.isEnabled();
}

/**
 * Le film ancré (RC18) laisse le bateau à quai pendant les premières phrases (Saint-Maur → La Rochelle
 * par la route — comptée dans filmNm —, puis l'escale) : on ne mesure sa glisse qu'une fois qu'il BOUGE
 * vraiment (plus de `minDeg` degrés entre deux lectures à 500 ms), pas sur les milles déjà au compteur.
 */
export async function waitBoatUnderWay(page, { minDeg = 0.01, timeout = 60_000 } = {}) {
  return page.evaluate(async ([min, limit]) => {
    const read = () => {
      const f = window.__naviguideFilm || {};
      return Number.isFinite(f.lat) && Number.isFinite(f.lon) ? { lat: f.lat, lon: f.lon, nm: Number(f.filmNm) || 0, ended: Boolean(f.ended) } : null;
    };
    const t0 = performance.now();
    let prev = read();
    while (performance.now() - t0 < limit) {
      await new Promise((r) => setTimeout(r, 500));
      const cur = read();
      if (cur?.ended) return { moving: false, ended: true, nm: cur.nm };
      if (prev && cur && Math.abs(cur.lat - prev.lat) + Math.abs(cur.lon - prev.lon) > min) return { moving: true, ended: false, nm: cur.nm };
      prev = cur || prev;
    }
    return { moving: false, ended: false, nm: prev?.nm || 0 };
  }, [minDeg, timeout]);
}

/** Le récit du panneau gauche dans la langue demandée (après une bascule FR/EN, il se recharge). */
export async function waitStoryLang(page, lang, timeout = 20_000) {
  const re = lang === "en" ? /expedition|left|departure|arrival/i : /expédition|quitté|départ|arrivée/i;
  await page.waitForFunction(([pattern, flags]) => {
    const box = document.querySelector("[data-testid='expedition-story']");
    const txt = box ? box.textContent || "" : "";
    const names = ["Saint-Maur", "La Rochelle", "Ajaccio", "Fort-de-France"].filter((n) => txt.includes(n));
    return new RegExp(pattern, flags).test(txt) && names.length >= 3;
  }, [re.source, re.flags], { timeout }).catch(() => null);
}
