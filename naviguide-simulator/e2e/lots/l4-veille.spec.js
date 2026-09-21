// Lot L4 — veille Tavily : carte FREE news de fixture (lien + data-kind).
// Sans API / sans clés : on injecte une carte FREE. La recette réelle
// (Suivre, prochaine escale, phrase Tavily) demande TAVILY_API_KEY
// et NEBIUS_API_KEY sur le VPS.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-l4/${name}.jpg`,
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

async function hideSidebarForFloatingCard(page) {
  const cinema = page.getByRole("button", { name: /^cinéma$/i });
  const chat = page.getByTestId("logbook-chat");
  if (await chat.isVisible().catch(() => false) && await cinema.isVisible().catch(() => false)) {
    await cinema.click();
  }
}

test("lot L4 — carte news de fixture : data-kind=news et un lien", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });
  await hideSidebarForFloatingCard(page);

  await page.evaluate(() => {
    window.__naviguideNewsFixture = {
      key: "fixture:news-l4",
      kind: "news",
      type: "news",
      severity: "info",
      title: "Nouméa · veille du 20 sept.",
      text: "Travaux annoncés à la marina de Motu Uta (portautonome.nc).",
      entity: {
        kind: "escale",
        name: "Nouméa",
        url: "https://www.portautonome.nc/avis",
        lat: -22.2758,
        lon: 166.4483,
      },
    };
    window.dispatchEvent(new Event("naviguide-news-fixture"));
  });

  const card = page.getByTestId("moment-free");
  await expect(card).toBeVisible({ timeout: 10_000 });
  await expect(card).toHaveAttribute("data-kind", "news");
  const link = page.getByTestId("moment-link-site");
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute("href", /portautonome\.nc/);
  await expect(card).toContainText(/Nouméa/);
  await expect(card).toContainText(/veille/i);
  await shot(page, "01-veille");
});
