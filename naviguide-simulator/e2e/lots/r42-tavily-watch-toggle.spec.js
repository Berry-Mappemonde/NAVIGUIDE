// R42 : interrupteur « Veille Tavily » des réglages de la barre de droite.
// Effet réel : le drapeau watch_enabled du serveur change, et survit au rechargement.
import { expect, test } from "@playwright/test";
import { dismissNotForNav, showRightPanel } from "../helpers.js";

const API = `http://127.0.0.1:${process.env.PW_API_PORT || 8010}`;

for (const [lang, label] of [["fr", "Veille Tavily"], ["en", "Tavily watch"]]) {
  test(`R42 ${lang} : l'interrupteur change la veille sur le serveur et reste après rechargement`, async ({ page, request }) => {
    test.setTimeout(90_000);
    const api = await request.get(`${API}/escale/watch/settings`).catch(() => null);
    test.skip(!api?.ok(), "API hors ligne absente");
    const before = (await api.json()).enabled;
    await page.addInitScript((l) => localStorage.setItem("naviguide_lang_v4", l), lang);
    await page.goto("/");
    await dismissNotForNav(page);
    await showRightPanel(page);
    const sw = page.getByRole("switch", { name: label });
    await sw.scrollIntoViewIfNeeded();
    await expect(sw).toHaveAttribute("data-testid", "tavily-watch-toggle");
    await expect(sw).toHaveAttribute("aria-checked", String(before));
    await sw.click();
    await expect(sw).toHaveAttribute("aria-checked", String(!before));
    const after = await (await request.get(`${API}/escale/watch/settings`)).json();
    expect(after).toMatchObject({ enabled: !before, source: "setting" });
    await page.reload();
    await dismissNotForNav(page);
    await showRightPanel(page);
    await expect(page.getByTestId("tavily-watch-toggle")).toHaveAttribute("aria-checked", String(!before));
    // Remet l'état de départ.
    await page.getByTestId("tavily-watch-toggle").click();
    await expect(page.getByTestId("tavily-watch-toggle")).toHaveAttribute("aria-checked", String(before));
  });
}
