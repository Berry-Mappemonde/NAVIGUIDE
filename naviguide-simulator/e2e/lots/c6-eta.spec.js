// Lot C6 — fourchette p10–p90 sous la prochaine escale.
// Avec API et ensembles : data-testid="eta-range" contient « p10 » ou « entre ».
// Sans API : fumée (barre film + liste d'escales).
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-c6/${name}.jpg`,
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

test("lot C6 — fourchette p10–p90 sous la prochaine escale", async ({ page }) => {
  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-clock-line")).toBeVisible({ timeout: 30_000 });

  let api = null;
  try {
    const clockRes = await page.request.get("/voyage/official/clock");
    if (clockRes.ok()) {
      const clock = await clockRes.json();
      const now = Date.now();
      const next = (clock.marks || []).find((m) => Date.parse(m.iso) > now);
      if (next?.name) {
        const e = await page.request.get(`/voyage/official/eta?stop=${encodeURIComponent(next.name)}`);
        if (e.ok()) api = await e.json();
      }
    }
  } catch {
    api = null;
  }

  const legend = page.getByText(/Escales|Stops/i).first();
  await legend.scrollIntoViewIfNeeded().catch(() => {});

  if (api && Number(api.members) > 0) {
    const range = page.getByTestId("eta-range");
    await expect(range).toBeVisible({ timeout: 20_000 });
    const text = await range.innerText();
    expect(text).toMatch(/p10|entre/i);
  } else {
    await expect(page.getByTestId("film-bar")).toBeVisible();
  }
  await shot(page, "01-fourchette");
});
