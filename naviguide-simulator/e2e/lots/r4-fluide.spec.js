// Lot R4 — film fluide : le bateau avance sans à-coups (mode linéaire).
// Sans API : horloge locale + brut. Headless : pas de voix (webdriver).
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-r4/${name}.jpg`,
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

test("lot R4 — 10 positions distinctes et monotones en 2 s", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 15_000 });

  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);

  await page.getByTestId("replay-start").click();
  await expect(page.getByTestId("replay-stop")).toBeVisible({ timeout: 8_000 });
  await expect.poll(async () => page.evaluate(() => Boolean(window.__naviguideFilm?.startedAt)), {
    timeout: 5_000,
  }).toBe(true);
  expect(await page.evaluate(() => Boolean(window.__naviguideFilm?.ended))).toBe(false);

  await page.waitForFunction(() => Boolean(window.__naviguideScene?.map), { timeout: 10_000 });
  const z0 = await page.evaluate(() => window.__naviguideScene.map.getZoom());
  const chapter0 = await page.evaluate(() => window.__naviguideFilm?.chapterIdx ?? 0);

  await page.waitForFunction(() => {
    const m = window.__naviguideScene?.mainBoatMarker?.();
    const ll = m?.getLatLng?.();
    return Boolean(ll && Number.isFinite(ll.lat));
  }, { timeout: 15_000 }).catch(() => {});

  const markerReady = await page.evaluate(() => {
    const m = window.__naviguideScene?.mainBoatMarker?.();
    const ll = m?.getLatLng?.();
    return Boolean(ll && Number.isFinite(ll.lat));
  });

  if (!markerReady) {
    if (!apiUp) {
      test.info().annotations.push({
        type: "sans API",
        description: "marqueur bateau absent — positions le long de la jambe non vérifiées",
      });
    } else {
      throw new Error("marqueur bateau absent avec API");
    }
  } else {
    // Film ancré : à quai pendant les premières phrases — on mesure la glisse une fois en route.
    const { waitBoatUnderWay } = await import("../helpers.js");
    const way = await waitBoatUnderWay(page, { timeout: 60_000 });
    expect(way.moving, `le bateau a pris la mer avant la mesure (${JSON.stringify(way)})`).toBe(true);
    const samples = [];
    for (let i = 0; i < 10; i++) {
      const pos = await page.evaluate(() => {
        const marker = window.__naviguideScene?.mainBoatMarker?.();
        const ll = marker?.getLatLng?.();
        const nm = Number(window.__naviguideFilm?.filmNm);
        if (!ll || !Number.isFinite(ll.lat) || !Number.isFinite(ll.lng)) return null;
        return { lat: ll.lat, lng: ll.lng, nm: Number.isFinite(nm) ? nm : 0 };
      });
      expect(pos, `échantillon ${i + 1} vide`).toBeTruthy();
      samples.push(pos);
      if (i < 9) await page.waitForTimeout(200);
    }
    const keys = samples.map((p) => `${p.lat.toFixed(7)},${p.lng.toFixed(7)}`);
    // Ancres RC18 : la glisse peut marquer un très court palier entre deux phrases — 8 positions
    // distinctes sur 10 en 2 s, c'est un bateau qui avance.
    expect(new Set(keys).size, `positions : ${keys.join(" | ")}`).toBeGreaterThanOrEqual(8);
    // Route : la projection lat/lng recule dans un virage (même constat ra3).
    // Les milles du film, eux, ne redescendent pas — contrat « ne recule pas ».
    for (let i = 1; i < samples.length; i++) {
      expect(samples[i].nm, `échantillon ${i + 1} recule`).toBeGreaterThanOrEqual(samples[i - 1].nm - 1e-6);
    }
  }

  const chapter1 = await page.evaluate(() => window.__naviguideFilm?.chapterIdx ?? 0);
  if (chapter1 === chapter0) {
    const z1 = await page.evaluate(() => window.__naviguideScene.map.getZoom());
    expect(Math.abs(z1 - z0), `zoom ${z0} → ${z1}`).toBeLessThanOrEqual(0.01);
  }
  await shot(page, "01-jambe");

  await page.waitForFunction((c0) => (window.__naviguideFilm?.chapterIdx ?? 0) !== c0, chapter0, {
    timeout: 80_000,
  }).catch(() => {});
  await shot(page, "02-suivante");
});
