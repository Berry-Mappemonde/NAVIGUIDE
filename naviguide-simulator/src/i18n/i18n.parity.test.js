import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fr from "./fr.js";
import en from "./en.js";

describe("i18n parity (lot F5)", () => {
  it("chaque clé fr a sa clé en, et inversement", () => {
    const frKeys = Object.keys(fr);
    const enKeys = Object.keys(en);
    const missingEn = frKeys.filter((k) => !(k in en));
    const missingFr = enKeys.filter((k) => !(k in fr));
    assert.deepEqual(missingEn, [], `clés fr sans en : ${missingEn.join(", ")}`);
    assert.deepEqual(missingFr, [], `clés en sans fr : ${missingFr.join(", ")}`);
    assert.equal(fr._lang, "fr");
    assert.equal(en._lang, "en");
  });

  it("lot R1 — plus de clés d'aide (logbook, revue, chiffres)", () => {
    for (const k of ["logbookChatHint", "planReviewSummary", "skipperExpertHint"]) {
      assert.equal(fr[k], undefined, `fr.${k} ne doit plus exister`);
      assert.equal(en[k], undefined, `en.${k} ne doit plus exister`);
    }
  });

  it("lot R2 — Escale précédente et info-bulles de régime", () => {
    assert.equal(fr.previousEscale, "Escale précédente");
    assert.equal(en.previousEscale, "Previous stop");
    assert.match(fr.regimeTooltipHindcast, /vraiment rencontré/);
    assert.match(fr.regimeTooltipForecast, /10 jours/);
    assert.match(fr.regimeTooltipClimatology, /moyenne du mois/);
    assert.match(en.regimeTooltipHindcast, /actually met/);
    assert.match(en.regimeTooltipForecast, /10 days/);
    assert.match(en.regimeTooltipClimatology, /monthly average/);
  });

  it("les libellés plein écran film existent dans les deux langues", () => {
    assert.match(fr.filmFullscreen, /Plein écran film/);
    assert.match(en.filmFullscreen, /fullscreen/i);
    assert.ok(fr.filmFullscreenExit);
    assert.ok(en.filmFullscreenExit);
  });
});
