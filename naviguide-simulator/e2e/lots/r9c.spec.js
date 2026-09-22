// Lot R9c — le film raconte le journal (ordre de la route, 2 min 30, rédigé prêt).
// Sans API : le brut local tient debout. GET /voyage/official sondé ; s'il
// manque, on annote et on saute seulement les assertions du script serveur.
import { expect, test } from "@playwright/test";

const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-r9c/${name}.jpg`,
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

async function dismissNotForNav(page) {
  const ok = page.getByRole("button", { name: /compris|j.ai compris|ok|continuer|accepter|understand|accept/i }).first();
  if (await ok.isVisible({ timeout: 3000 }).catch(() => false)) {
    const ack = page.getByTestId("not-for-nav-ack");
    if (await ack.isVisible({ timeout: 500 }).catch(() => false)) await ack.check();
    await ok.click();
  }
}

test("lot R9c — Revoir : le film raconte le journal, dans l'ordre", async ({ page }) => {
  test.setTimeout(90_000);
  const apiUp = await page.request.get("/voyage/official", { timeout: 5000 }).then((r) => r.ok()).catch(() => false);
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — script serveur /film non exigé",
    });
  }

  const errors = [];
  page.on("pageerror", (err) => errors.push(String(err)));

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 15_000 });

  await page.getByTestId("replay-start").click();
  await expect(page.getByTestId("replay-stop")).toBeVisible({ timeout: 8_000 });
  const subtitle = page.getByTestId("film-subtitle");
  await expect(subtitle).toBeVisible({ timeout: 8_000 });

  await expect.poll(async () => page.evaluate(() => Boolean(window.__naviguideFilm?.startedAt)), {
    timeout: 5_000,
  }).toBe(true);
  expect(await page.evaluate(() => Boolean(window.__naviguideFilm?.ended))).toBe(false);

  const localText = (await subtitle.innerText()).trim();
  if (localText) {
    await expect(subtitle).toContainText(/Saint-Maur|La Rochelle|Ajaccio|Fort-de-France|Nouméa/i);
  }

  if (apiUp) {
    const film = await page.request.get("/voyage/official/film?lang=fr&seconds=150", { timeout: 8_000 })
      .then((r) => (r.ok() ? r.json() : null))
      .catch(() => null);
    if (!film || !Array.isArray(film.chapters) || !film.chapters.length) {
      test.info().annotations.push({
        type: "film vide",
        description: "GET /voyage/official/film sans chapitres — ordre serveur non exigé",
      });
    } else {
      const blob = film.chapters.map((c) => c.text || "").join(" ");
      expect(film.targetSeconds, "durée cible 150 s").toBe(150);
      expect(blob, "pas de nm nu").not.toMatch(/\bnm\b/);
      const hits = ["Saint-Maur", "La Rochelle", "Ajaccio", "Fort-de-France"]
        .map((n) => ({ n, i: blob.toLowerCase().indexOf(n.toLowerCase()) }))
        .filter((h) => h.i >= 0);
      expect(hits.length, "escales dans le script").toBeGreaterThanOrEqual(2);
      for (let i = 1; i < hits.length; i += 1) {
        expect(hits[i - 1].i, `${hits[i].n} avant ${hits[i - 1].n}`).toBeLessThan(hits[i].i);
      }
      const sea = film.chapters.filter((c) => c.events && c.events.length);
      expect(sea.length, "chapitres avec bulles").toBeGreaterThanOrEqual(1);
      if (typeof film.hasWritten === "boolean" && film.style === "written") {
        expect(film.hasWritten, "rédigé déjà en cache").toBe(true);
      }
    }
  }

  await shot(page, "01-film");
  expect(errors, `erreurs de page : ${errors.join(" | ")}`).toEqual([]);
});
