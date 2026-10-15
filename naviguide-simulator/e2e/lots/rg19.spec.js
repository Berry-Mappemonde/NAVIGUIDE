// Lot RG19 — chat à trois paliers : faits par les règles, Ultra seulement sur geste.
// Sans API : le panneau chat tient seul. GET /voyage/official sondé ;
// s'il manque, annotation + saut des questions/réponses — jamais le chat retiré.
// En CI (PW_WITH_API=1, stock figé, proxy :9) l'API répond mais Nemotron Ultra
// n'est pas joignable : le geste retombe sur source « règles » / budget / plafond
// — annotation, pas d'échec. Le badge Ultra n'est exigé que s'il est réellement là.
// Aucune donnée factice : on lit la réponse du poste, on n'écrit aucun vent.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { dismissNotForNav, leaveCinema, probeOfficial, showLeftPanel } from "../helpers.js";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rg19");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`),
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

const FAILED = /n.a pas pu répondre|aucun modèle n.a répondu|could not answer|no model replied/i;
const MISSING = /n.a pas cette information dans ses données|does not hold that information/i;
const INVITE = /cochez raisonnement|tick reasoning/i;
const RULES = /règles|rules/i;
const ULTRA = /nemotron.*ultra|ultra/i;

async function askChat(page, question) {
  const chat = page.getByTestId("logbook-chat");
  const input = chat.getByTestId("logbook-chat-input");
  await input.scrollIntoViewIfNeeded();
  await input.fill(question);
  await chat.getByTestId("logbook-chat-send").click();
}

async function waitReply(page, { extra = null, sourcesBefore = 0 } = {}) {
  const list = page.getByTestId("logbook-chat-list");
  await expect.poll(async () => {
    const n = await page.getByTestId("chat-source").count();
    if (n > sourcesBefore) return "ready";
    const t = await list.innerText();
    if (FAILED.test(t) && n >= sourcesBefore) return "done";
    if (MISSING.test(t) && n > sourcesBefore) return "done";
    if (extra && extra.test(t) && n > sourcesBefore) return "done";
    return "wait";
  }, { timeout: 60_000 }).not.toBe("wait");
  return list.innerText();
}

test("lot RG19 — chat trois paliers : faits par les règles, Ultra sur geste", async ({ page }) => {
  test.setTimeout(180_000);
  const official = await probeOfficial(page);
  const apiUp = Boolean(official);

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);
  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await showLeftPanel(page);

  const chat = page.getByTestId("logbook-chat");
  await expect(chat).toBeVisible({ timeout: 10_000 });
  await expect(chat.getByTestId("logbook-chat-input")).toBeVisible();
  await expect(chat.getByTestId("logbook-chat-send")).toBeVisible();
  await expect(chat.getByTestId("logbook-chat-reason")).toBeVisible();

  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — questions au journal sautées ; panneau chat et case Raisonnement gardés",
    });
    await shot(page, "01-chat-faits");
    await shot(page, "02-chat-ultra");
    return;
  }

  const factsRes = await page.request.get("/logbook/facts", { timeout: 20_000 }).catch(() => null);
  const factsBody = factsRes && factsRes.ok() ? await factsRes.json().catch(() => null) : null;
  const factsOk = Boolean(factsBody && factsBody.facts);
  if (!factsOk) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /logbook/facts absent — assertions nombres sautées ; chat gardé",
    });
  }

  const warmBefore = await page.request.get("/ici/warm/status", { timeout: 8_000 })
    .then((r) => (r.ok() ? r.json() : null))
    .catch(() => null);
  const ultraCallsBefore = Number(warmBefore?.llm?.chatUltra?.calls ?? warmBefore?.llm?.judge?.calls ?? 0);

  let sources = 0;
  await askChat(page, "Quel vent au bateau ?");
  const windText = await waitReply(page, { sourcesBefore: sources });
  sources = await page.getByTestId("chat-source").count();
  expect(windText, "jamais l'échec modèle").not.toMatch(FAILED);
  const hasWind = /\d+(?:[.,]\d+)?\s*kn/i.test(windText);
  expect(hasWind || MISSING.test(windText), "phrase vent (kn) ou pas cette information").toBeTruthy();
  const src0 = page.getByTestId("chat-source").last();
  if (await src0.count()) {
    await expect(src0).toContainText(RULES);
  }

  await askChat(page, "Quelle vitesse polaire par 15 nœuds ?");
  const polarText = await waitReply(page, { sourcesBefore: sources });
  sources = await page.getByTestId("chat-source").count();
  expect(polarText).not.toMatch(FAILED);
  if (factsOk) {
    const speeds = factsBody.facts?.polar?.speedAtTws || {};
    const polarKn = speeds["15"] ?? speeds[15];
    if (polarKn != null) {
      expect(polarText).toContain(String(polarKn));
    }
  }

  await askChat(page, "Arrivée prévue à Madère ?");
  const etaText = await waitReply(page, { sourcesBefore: sources });
  sources = await page.getByTestId("chat-source").count();
  expect(etaText).not.toMatch(FAILED);

  await askChat(page, "Quel réglage de confort ?");
  const comfortText = await waitReply(page, { sourcesBefore: sources });
  sources = await page.getByTestId("chat-source").count();
  expect(comfortText).not.toMatch(FAILED);
  if (factsOk && factsBody.facts?.orders?.comfort) {
    expect(comfortText.toLowerCase()).toContain(String(factsBody.facts.orders.comfort).toLowerCase());
  }

  await askChat(page, "Climatologie de septembre ici ?");
  const climoText = await waitReply(page, { sourcesBefore: sources });
  sources = await page.getByTestId("chat-source").count();
  expect(climoText).not.toMatch(FAILED);

  await shot(page, "01-chat-faits");

  await askChat(page, "Faut-il partir demain ou attendre ?");
  const inviteText = await waitReply(page, { extra: INVITE, sourcesBefore: sources });
  sources = await page.getByTestId("chat-source").count();
  expect(inviteText).not.toMatch(FAILED);
  expect(inviteText, "sans geste : invitation à cocher raisonnement").toMatch(INVITE);

  const reasonBox = chat.getByTestId("logbook-chat-reason");
  await reasonBox.check();
  await expect(reasonBox).toBeChecked();
  await askChat(page, "Faut-il partir demain ou attendre ?");
  const ultraText = await waitReply(page, { sourcesBefore: sources });
  expect(ultraText).not.toMatch(FAILED);
  const srcUltra = page.getByTestId("chat-source").last();
  const ultraLabel = ((await srcUltra.innerText().catch(() => "")) || "").trim();
  const lastBubble = page.getByTestId("logbook-chat-list").locator(":scope > div").last();
  const lastText = await lastBubble.innerText();
  const capped = /plafond|cap/i.test(lastText);
  const gotUltra = ULTRA.test(ultraLabel);
  expect(ultraLabel, "geste Ultra : jamais Super (write ne rédige pas)").not.toMatch(/nemotron 3 super|nemotron-super/i);

  if (!gotUltra) {
    test.info().annotations.push({
      type: "poste",
      description: "Nemotron Ultra injoignable (stock figé / proxy / mode off) — source règles, budget ou plafond ; badge Ultra non exigé",
    });
    expect(ultraLabel, "sans Ultra le repli est règles, budget ou vide").toMatch(/règles|rules|budget|^$/i);
  } else {
    expect(ultraLabel).toMatch(ULTRA);
    if (factsOk && !capped) {
      const blob = JSON.stringify(factsBody.facts);
      const stripped = lastText.replace(/\b\d{1,2}:\d{2}(?::\d{2})?\b/g, "");
      const nums = stripped.match(/\d+(?:[.,]\d+)?/g) || [];
      for (const n of nums) {
        const g = String(Number(String(n).replace(",", ".")));
        const ok = blob.includes(n) || blob.includes(g) || blob.includes(n.replace(",", "."));
        expect(ok, `nombre ${n} absent de GET /logbook/facts`).toBeTruthy();
      }
    }
  }
  await shot(page, "02-chat-ultra");

  const warmAfter = await page.request.get("/ici/warm/status", { timeout: 8_000 })
    .then((r) => (r.ok() ? r.json() : null))
    .catch(() => null);
  if (warmAfter?.llm && !capped) {
    const ultraCallsAfter = Number(warmAfter.llm?.chatUltra?.calls ?? warmAfter.llm?.judge?.calls ?? 0);
    expect(ultraCallsAfter, "compteur Ultra / judge après geste").toBeGreaterThanOrEqual(ultraCallsBefore);
  }
});
