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

  it("les libellés plein écran film existent dans les deux langues", () => {
    assert.match(fr.filmFullscreen, /Plein écran film/);
    assert.match(en.filmFullscreen, /fullscreen/i);
    assert.ok(fr.filmFullscreenExit);
    assert.ok(en.filmFullscreenExit);
  });
});
