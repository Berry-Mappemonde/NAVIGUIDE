import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema } from "../helpers.js";

// À valider hors sandbox : Playwright requires the local preview/API servers.
const TECHNICAL = /overpass_unavailable|Traceback|\bundefined\b|\bNaN\b|\[object Object\]/i;

for (const lang of ["fr", "en"]) {
  test(`${lang} : replay expedition hors ligne jusqu'à la fin`, async ({ page }) => {
    test.setTimeout(90_000);
    const consoleErrors = [];
    const pageErrors = [];
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });
    page.on("pageerror", (error) => pageErrors.push(error.message));
    await page.clock.install();
    await page.addInitScript((locale) => {
      localStorage.setItem("naviguide_lang_v4", locale);
      // Keep chapter transitions deterministic and independent of browser voices.
      const synth = window.speechSynthesis;
      if (synth) {
        synth.speak = (utterance) => queueMicrotask(() => utterance.onend?.());
        synth.cancel = () => {};
        Object.defineProperty(synth, "speaking", { configurable: true, get: () => false });
      }
    }, lang);

    await page.route("**/voyage/official/film**", async (route) => {
      const url = new URL(route.request().url());
      const requestedLang = url.searchParams.get("lang") || lang;
      const written = url.searchParams.get("style") === "written";
      const chapters = [0, 1, 2].map((i) => ({
        id: `offline-${i}`,
        text: requestedLang === "fr" ? `Chapitre ${i + 1} de l'expédition.` : `Expedition chapter ${i + 1}.`,
        tA: i * 1_000,
        tB: (i + 1) * 1_000,
        anchors: [{ t: i * 1_000, i: 0 }, { t: (i + 1) * 1_000, i: 30 }],
      }));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "ready", lang: requestedLang, style: written ? "written" : "raw",
          source: written ? "offline-fixture" : "rules", hasWritten: true,
          targetSeconds: 0, chapters,
        }),
      });
    });

    await page.goto(`/?lang=${lang}`);
    await dismissNotForNav(page);
    await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
    await leaveCinema(page);
    await page.getByTestId("view-suivre").click();
    const start = page.getByTestId("replay-start");
    await expect(start).toBeVisible({ timeout: 15_000 });
    const raw = page.getByTestId("film-style-raw");
    const written = page.getByTestId("film-style-written");
    await expect(raw).toBeVisible();
    await expect(written).toBeVisible();
    await expect(raw).toHaveAttribute("aria-pressed", "true");
    await written.click();
    await expect(written).toHaveAttribute("aria-pressed", "true");
    await raw.click();
    await expect(raw).toHaveAttribute("aria-pressed", "true");
    await expect(written).toHaveAttribute("aria-pressed", "false");

    await expect(start).toBeEnabled({ timeout: 20_000 });
    await start.click();
    await expect(page.getByTestId("replay-stop")).toBeVisible({ timeout: 8_000 });
    await expect(page.getByTestId("film-subtitle")).toBeVisible();
    const listen = page.getByTestId("listen");
    if (await listen.count()) await expect(listen).toBeVisible();

    // Capture the active bar at 100%, then let the replay settle into its ended state.
    for (let i = 0; i < 12; i += 1) {
      if (await page.evaluate(() => Boolean(window.__naviguideFilm?.ended))) break;
      await page.clock.fastForward(5_000);
    }
    const reachedEnd = await page.evaluate(() => Boolean(window.__naviguideFilm?.ended));
    expect(reachedEnd, "la relecture a atteint sa fin").toBe(true);
    await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 8_000 });

    const visibleText = await page.locator("body").innerText();
    expect(visibleText).not.toMatch(TECHNICAL);
    expect(consoleErrors, "erreurs console").toEqual([]);
    expect(pageErrors, "erreurs page").toEqual([]);
  });
}
