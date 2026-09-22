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

  it("lot RB8 — info-bulle de vitesse d'époque", () => {
    assert.equal(fr.traveledEraSpeed, "{knots} kn");
    assert.equal(en.traveledEraSpeed, "{knots} kn");
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

  it("lot R5 — unités terrestres km / h de route", () => {
    assert.equal(fr.unitKm, "km");
    assert.equal(en.unitKm, "km");
    assert.equal(fr.unitRoadHours, "h de route");
    assert.equal(en.unitRoadHours, "h on the road");
    assert.equal(fr.byRoad, "par la route");
    assert.equal(en.byRoad, "by road");
  });

  it("lot R11 — fourchette d'arrivée sans p10 ni membres à l'écran", () => {
    assert.equal(fr.etaRange, "arrivée entre le {p10} et le {p90}");
    assert.equal(en.etaRange, "arrival between {p10} and {p90}");
    assert.equal(fr.etaRangeTitle, "p10–p90, {n} membres");
    assert.equal(en.etaRangeTitle, "p10–p90, {n} members");
  });

  it("les libellés plein écran film existent dans les deux langues", () => {
    assert.match(fr.filmFullscreen, /Plein écran film/);
    assert.match(en.filmFullscreen, /fullscreen/i);
    assert.ok(fr.filmFullscreenExit);
    assert.ok(en.filmFullscreenExit);
  });
});
