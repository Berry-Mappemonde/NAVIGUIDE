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
  if (!(await panelClosed(page, "right").catch(() => true))) return;
  const toggle = page.locator(".naviguide-sidebar-toggle--right");
  if (await toggle.isVisible().catch(() => false)) await toggle.evaluate((el) => el.click());
  await expect.poll(() => panelClosed(page, "right"), { timeout: 10_000 }).toBe(false);
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
