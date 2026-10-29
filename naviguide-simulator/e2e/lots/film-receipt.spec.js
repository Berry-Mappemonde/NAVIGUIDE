// Idée n° 3 : reçu « Comment ce film a été fait » sous le film Rédigé.
// Les compteurs viennent du serveur (receipt) ; sans reçu servi, rien n'est affiché.
import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema, probeOfficial } from "../helpers.js";

const RECEIPT = {
  llmCalls: 7, cacheHits: 0, ruleFallbacks: 0,
  models: [
    { model: "nvidia/Nemotron-3.5-Super-VL", source: "nemotron-super", tier: "write", calls: 4, cached: 0 },
    { model: "nvidia/Nemotron-3-Ultra", source: "nemotron-ultra", tier: "deep", calls: 2, cached: 0 },
    { model: "nvidia/Nemotron-3.5-Lightning", source: "nemotron-lightning", tier: "fast", calls: 1, cached: 0 },
  ],
  rewritten: 12, fallen: 1, super: 1, ultra_edit: 1, ultra_judge: 1, reviewed: true,
  reread: "pass", reread_en: "pass", lightning: 1, at: "2026-10-29T13:40:00Z",
};

function filmPayload({ written, seconds = 150, lang = "fr", receipt }) {
  return {
    status: "ready",
    lang,
    style: written ? "written" : "raw",
    hasWritten: written,
    source: written ? "nemotron-super" : "rules",
    reviewedBy: written ? "nemotron-ultra" : undefined,
    writtenAt: written ? "2026-10-29T13:40:00Z" : undefined,
    targetSeconds: seconds,
    chapters: [{ text: "Le 15 mai, Berry-Mappemonde quitte La Rochelle.", anchors: [{ t: 0, i: 0 }] }],
    ...(written && receipt ? { receipt } : {}),
  };
}

async function openWritten(page, lang, receipt) {
  await page.addInitScript((l) => localStorage.setItem("naviguide_lang_v4", l), lang);
  const cached = new Set();
  await page.route("**/voyage/**/film**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const style = url.searchParams.get("style") || "raw";
    const seconds = Number(url.searchParams.get("seconds") || 0);
    const key = `${url.searchParams.get("lang") || lang}:${seconds}`;
    if (req.method() === "POST") cached.add(key);
    const written = req.method() === "POST" || (style === "written" && cached.has(key));
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(filmPayload({ written, seconds, lang, receipt })),
    });
  });
  const official = await probeOfficial(page);
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  test.skip(!official, "GET /voyage/official absent : pas de film à rédiger");
  await leaveCinema(page);
  await page.getByTestId("view-suivre").click();
  const written = page.getByTestId("film-style-written");
  await expect(written).toBeEnabled({ timeout: 15_000 });
  await written.click();
  await expect(page.getByTestId("film-source")).toContainText("Nemotron", { timeout: 8_000 });
}

for (const [lang, title, calls, rewritten] of [
  ["fr", "Comment ce film a été fait", "Nemotron 3.5 Super VL · Token Factory : 4 appel(s)", "Phrases réécrites par Nemotron : 12"],
  ["en", "How this film was made", "Nemotron 3.5 Super VL · Token Factory: 4 call(s)", "Sentences rewritten by Nemotron: 12"],
]) {
  test(`${lang} : le reçu du film rédigé montre les compteurs servis`, async ({ page }) => {
    test.setTimeout(90_000);
    await openWritten(page, lang, RECEIPT);
    const receipt = page.getByTestId("film-receipt");
    await expect(receipt).toBeVisible();
    await expect(receipt.locator("summary")).toHaveText(title);
    await receipt.locator("summary").click();
    await expect(page.getByTestId("film-receipt-model")).toHaveCount(3);
    await expect(page.getByTestId("film-receipt-models")).toContainText(calls);
    await expect(page.getByTestId("film-receipt-models")).toContainText("Nemotron 3 Ultra");
    await expect(page.getByTestId("film-receipt-models")).toContainText("Nemotron 3.5 Lightning");
    await expect(page.getByTestId("film-receipt-filmReceiptRewritten")).toContainText(rewritten);
    await expect(page.getByTestId("film-receipt-filmReceiptRereadPass")).toBeVisible();
    // Aucun défaut servi : aucune ligne de défauts inventée.
    await expect(page.getByTestId("film-receipt-filmReceiptFaults")).toHaveCount(0);
  });
}

test("sans reçu servi, aucun reçu affiché", async ({ page }) => {
  test.setTimeout(90_000);
  await openWritten(page, "fr", null);
  await expect(page.getByTestId("film-receipt")).toHaveCount(0);
});

test("affiche les sources Tavily quand webSourceCount > 0", async ({ page }) => {
  test.setTimeout(90_000);
  const receiptWithTavily = { ...RECEIPT, webSourceCount: 3 };
  await openWritten(page, "fr", receiptWithTavily);
  const receipt = page.getByTestId("film-receipt");
  await expect(receipt).toBeVisible();
  await expect(receipt.locator("summary")).toHaveText("Comment ce film a été fait");
  await receipt.locator("summary").click();
  // Vérifie que la ligne Tavily s'affiche avec le bon testid
  const tavilyLine = page.getByTestId("film-receipt-filmReceiptTavily");
  await expect(tavilyLine).toBeVisible();
  await expect(tavilyLine).toContainText("Sources web Tavily affichées avec le film : 3");
});
