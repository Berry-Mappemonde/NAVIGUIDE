// Lot F4 — bulle événement ancrée au bateau (mode sans voix).
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-f4/${name}.jpg`,
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

async function dismissNotForNav(page) {
  const ok = page.getByRole("button", { name: /compris|j.ai compris|ok|continuer|accepter/i }).first();
  if (await ok.isVisible({ timeout: 3000 }).catch(() => false)) {
    const ack = page.getByTestId("not-for-nav-ack");
    if (await ack.isVisible().catch(() => false)) await ack.check();
    await ok.click();
  }
}

async function muteFilmVoice(page) {
  const listen = page.getByTestId("listen");
  if (await listen.isVisible().catch(() => false)) {
    if (await listen.getAttribute("aria-pressed") === "true") await listen.click();
  }
}

function bubbleNearBoat() {
  const bubble = document.querySelector("[data-testid='event-bubble']");
  const scene = window.__naviguideScene;
  const marker = scene?.mainBoatMarker?.();
  const map = scene?.map;
  if (!bubble || !marker || !map) return { ok: false, dist: Infinity, kind: "" };
  const boat = map.latLngToContainerPoint(marker.getLatLng());
  const popup = scene.eventBubble?.popup;
  const pll = popup?.getLatLng?.();
  const tip = pll ? map.latLngToContainerPoint(pll) : boat;
  const tipDist = Math.hypot(tip.x - boat.x, tip.y - boat.y);
  const icon = typeof marker.getElement === "function" ? marker.getElement() : null;
  const m = icon ? icon.getBoundingClientRect() : null;
  const b = bubble.getBoundingClientRect();
  let boxDist = Infinity;
  if (m && m.width > 2 && m.height > 2 && b.width > 2) {
    const mx = m.left + m.width / 2;
    const my = m.top + m.height / 2;
    const cx = Math.max(b.left, Math.min(mx, b.right));
    const cy = Math.max(b.top, Math.min(my, b.bottom));
    boxDist = Math.hypot(cx - mx, cy - my);
  }
  const dist = Math.min(tipDist, boxDist);
  return {
    ok: dist <= 60,
    dist,
    tipDist,
    boxDist,
    kind: bubble.getAttribute("data-kind") || "",
  };
}

test("lot F4 — bulle visible dès le premier événement, ancrée au bateau", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 15_000 });

  await muteFilmVoice(page);
  await page.getByTestId("replay-start").click();
  await muteFilmVoice(page);

  const bubble = page.getByTestId("event-bubble");
  await page.waitForFunction(() => Boolean(window.__naviguideFilm?.startedAt), { timeout: 8_000 });
  await expect(bubble).toBeVisible({ timeout: 1_000 });

  await page.waitForFunction(() => Boolean(window.__naviguideScene?.mainBoatMarker?.()), { timeout: 10_000 });
  const pos = await page.evaluate(bubbleNearBoat);
  expect(pos.ok, `distance bulle→bateau ${pos.dist} px`).toBeTruthy();
  expect(pos.dist).toBeLessThan(60);

  const kind1 = (await bubble.getAttribute("data-kind")) || "stop";
  await shot(page, "01-bulle-escale");

  const firstId = await page.evaluate(() => window.__naviguideFilm?.bubbleId || "");
  await page.waitForFunction((id) => {
    const el = document.querySelector("[data-testid='event-bubble']");
    const kind = el?.getAttribute("data-kind") || "";
    const cur = window.__naviguideFilm?.bubbleId || "";
    return kind === "wx" || kind === "climo" || kind === "sci" || (cur && id && cur !== id);
  }, firstId, { timeout: 8_000 }).catch(() => {});

  const kind2 = (await bubble.getAttribute("data-kind")) || kind1;
  await shot(page, kind2 === "wx" ? "02-bulle-coup-de-vent" : `02-bulle-${kind2 || "kind"}`);
});
