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
  await page.getByTestId("view-tracer").click();
  await expect(page.getByTestId("view-tracer")).toHaveAttribute("aria-checked", "true");
}

// DM1 : la pilule s'appelle Tracer à l'écran ; le mode interne (VIEW_SIMULATION)
// ne change qu'en DM3. Alias pour les specs à venir.
export const enterTracerMode = enterSimulation;

export async function enterTracer(page) {
  // DM6 : entrer en Tracer ouvre le dessin (brouillon vide ou déjà là).
  await showLeftPanel(page);
  const tracer = page.getByTestId("view-tracer");
  if ((await tracer.getAttribute("aria-checked")) !== "true") {
    await tracer.click();
  }
  await expect(tracer).toHaveAttribute("aria-checked", "true");
  const box = page.getByTestId("drawing-box");
  const points = page.getByTestId("drawing-points");
  const drawingOpen = (await box.isVisible().catch(() => false))
    || (await points.isVisible().catch(() => false));
  if (!drawingOpen) {
    const drawBtn = page.getByRole("button", {
      name: /Berry-Mappemonde.*Tracer votre propre route|Tracer votre propre route|Draw your own route/i,
    });
    await expect(drawBtn).toBeVisible({ timeout: 10_000 });
    await drawBtn.scrollIntoViewIfNeeded();
    // Sous charge (tranches CI), le bouton peut être hors du cadre de la fenêtre au moment du clic
    // (panneau en transition) : le clic DOM ne dépend pas de la géométrie.
    await drawBtn.click({ force: true, timeout: 5_000 }).catch(() => drawBtn.evaluate((el) => el.click()));
  }
  await expect.poll(async () => (
    (await box.isVisible().catch(() => false))
    || (await points.isVisible().catch(() => false))
  ), { timeout: 15_000 }).toBe(true);
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

/** Cadrage Suivre (lot DM4) : zoom plancher + distance pixel bateau → centre. */
export async function mapFollowCadrage(page) {
  return page.evaluate(() => {
    const scene = window.__naviguideScene;
    const map = scene?.map;
    if (!map) return null;
    const center = map.getCenter();
    const live = scene.config?.live;
    const marker = scene.mainBoatMarker?.()?.getLatLng?.();
    const lat = Number(marker?.lat ?? live?.lat);
    const lng = Number(marker?.lng ?? live?.lon);
    const boat = Number.isFinite(lat) && Number.isFinite(lng) ? { lat, lon: lng } : null;
    let boatPx = null;
    if (boat) {
      const c = map.latLngToContainerPoint(center);
      const b = map.latLngToContainerPoint([boat.lat, boat.lon]);
      boatPx = Math.hypot(b.x - c.x, b.y - c.y);
    }
    const box = map.getContainer().getBoundingClientRect();
    const cx = box.left + box.width / 2;
    const cy = box.top + box.height / 2;
    let iconPx = null;
    for (const el of document.querySelectorAll(".catamaran-divicon--live, .catamaran-divicon")) {
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      const d = Math.hypot(r.left + r.width / 2 - cx, r.top + r.height / 2 - cy);
      if (iconPx == null || d < iconPx) iconPx = d;
    }
    const px = Number.isFinite(boatPx) ? boatPx : iconPx;
    return {
      zoom: map.getZoom(),
      minZoom: map.getMinZoom(),
      cx: center.lat,
      cy: center.lng,
      boat,
      boatPx: Number.isFinite(px) ? px : boatPx,
      iconPx,
    };
  });
}

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

/** Recentre la carte sur le drapeau d'une escale : en Suivre la caméra est sur le bateau (Pacifique) et
 *  un drapeau des Antilles ou de Corse est hors cadre — un clic « force » n'y atteint rien (28 sept.). */
export async function centerOnFlag(page, namePattern, zoom = 7) {
  const source = namePattern instanceof RegExp ? namePattern.source : String(namePattern);
  await page.evaluate(([src, z]) => {
    const scene = window.__naviguideScene;
    if (!scene?.map || !scene.waypointMarkers) return false;
    const re = new RegExp(src, "i");
    for (const marker of scene.waypointMarkers.values()) {
      if (re.test(marker._naviguideWaypoint?.name || "")) {
        scene.map.setView(marker.getLatLng(), z, { animate: false });
        return true;
      }
    }
    return false;
  }, [source, zoom]);
  await page.waitForTimeout(300);
}
