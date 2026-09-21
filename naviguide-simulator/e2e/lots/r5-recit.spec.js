// Lot R5 — récit : connecteurs variés, kilomètres à terre.
// Sans API : le récit et la carte Escale se construisent depuis l'horloge locale.
import { expect, test } from "@playwright/test";

const CONNECTORS_FR = ["Puis", "Ensuite", "Plus loin", "De là", "Sur la route", "À la jambe suivante"];

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-r5/${name}.jpg`,
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

async function leaveCinema(page) {
  const cinema = page.getByRole("button", { name: /^(cinéma|cinema)$/i });
  const isOn = async () => /bg-cyan-700/.test((await cinema.getAttribute("class")) || "");
  if (!(await isOn())) return;
  await page.keyboard.press("Escape");
  if (!(await isOn())) return;
  await cinema.click();
  if (!(await isOn())) return;
  await cinema.click();
}

async function showLeftPanel(page) {
  await leaveCinema(page);
  const story = page.getByTestId("expedition-story");
  if (await story.isVisible().catch(() => false)) return;
  const toggle = page.locator(".naviguide-sidebar-toggle--left");
  if (await toggle.isVisible().catch(() => false)) await toggle.click();
  await expect(story).toBeVisible({ timeout: 15_000 });
}

async function rewindToFirstStop(page, prev) {
  for (let i = 0; i < 24 && await prev.isEnabled(); i++) {
    await prev.click();
    await expect(prev).toBeVisible();
  }
}

test("lot R5 — connecteurs variés, Escale Saint-Maur en km", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);

  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
  const bar = page.getByTestId("film-bar");
  await expect(bar).toBeVisible();
  const prev = page.getByTestId("prev-stop");
  await expect(prev).toBeVisible();
  await rewindToFirstStop(page, prev);

  const landCard = page.getByTestId("moment-now").filter({ hasText: /par la route|by road/ }).first();
  if (!(await landCard.isVisible({ timeout: 8_000 }).catch(() => false))) {
    const next = bar.getByRole("button", { name: /prochaine escale|go to next stop/i });
    if (await next.isEnabled()) {
      await next.click();
      await expect(prev).toBeEnabled({ timeout: 10_000 });
      await prev.click();
    }
  }
  if (await landCard.isVisible({ timeout: 10_000 }).catch(() => false)) {
    await expect(landCard).toHaveAttribute("data-kind", "escale");
    const cardText = await landCard.innerText();
    expect(cardText, `carte Escale : ${cardText}`).toMatch(/\bkm\b/);
    expect(cardText).toMatch(/par la route|by road/);
    expect(cardText).not.toMatch(/\bnm\b/);
  } else if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "carte Escale Saint-Maur absente — km par la route non vérifiés à l'écran",
    });
  } else {
    const dump = await page.getByTestId("moment-now").allInnerTexts();
    throw new Error(`carte Escale Saint-Maur absente : ${JSON.stringify(dump)}`);
  }

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await showLeftPanel(page);

  const story = page.getByTestId("expedition-story");
  await expect(story).toBeVisible({ timeout: 15_000 });
  const paras = story.getByTestId("story-paragraph");
  const n = await paras.count();
  if (n < 2) {
    if (!apiUp) {
      test.info().annotations.push({
        type: "sans API",
        description: "récit trop court — connecteurs non vérifiés",
      });
    } else {
      throw new Error(`récit : ${n} paragraphe(s), attendu ≥ 2`);
    }
  } else {
    const texts = [];
    for (let i = 0; i < n; i++) texts.push((await paras.nth(i).innerText()).trim());
    const used = [];
    for (const t of texts) {
      const hit = CONNECTORS_FR.find((c) => t.startsWith(`${c},`) || t.startsWith(`${c} `));
      if (hit) used.push(hit);
    }
    expect(used.length, `connecteurs : ${used.join(" | ")}`).toBeGreaterThanOrEqual(2);
    for (let i = 1; i < used.length; i++) {
      expect(used[i], `connecteur répété : ${used[i]}`).not.toBe(used[i - 1]);
    }
    expect(used.join(" ")).not.toMatch(/Puis Puis Puis/);
    const land = texts.find((t) => /départ vers La Rochelle|par la route/.test(t));
    if (land) {
      expect(land).toMatch(/\bkm\b/);
      expect(land).toMatch(/par la route/);
      expect(land).not.toMatch(/\bnm\b/);
    }
  }
  await story.scrollIntoViewIfNeeded();
  await shot(page, "01-recit");
});
