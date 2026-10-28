import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { GENERIC_WORDS, REASON_WORDS, SOURCE_DOWN_WORDS, markReasons, reasonWords } from "./reasonWords.js";
import { narrateIci, narrateIciSegments } from "./iciBriefing.js";

const here = dirname(fileURLToPath(import.meta.url));
const read = (rel) => readFileSync(join(here, rel), "utf8");
// Same net as e2e/lots/judge-path.spec.js, plus any snake_case code.
const TECHNICAL = /HTTPStatusError|Traceback|ConnectError|[a-z]+_[a-z_]+|Exception:/;

describe("reasonWords — codes du serveur en mots", () => {
  it("dit en clair les deux codes vus dans « Ici maintenant », en anglais et en français", () => {
    const aton = "outside_us_enc;overpass_unavailable:ConnectError";
    assert.deepEqual(reasonWords(aton, "en"), {
      text: "NOAA charts not read in this area; map server unreachable right now",
      code: aton,
      known: true,
    });
    assert.equal(
      reasonWords(aton, "fr").text,
      "cartes NOAA non consultées dans cette zone ; serveur de cartes injoignable pour l’instant",
    );
    assert.equal(reasonWords("no_sample_at_point", "en").text, "no sounding at this point");
    assert.equal(reasonWords("no_sample_at_point", "fr").text, "pas de sondage à ce point");
    assert.equal(reasonWords("no_feature_at_point", "en").text, "no data at this point");
    for (const lang of ["fr", "en"]) {
      assert.doesNotMatch(reasonWords(aton, lang).text, TECHNICAL);
      assert.equal(reasonWords("no_sample_at_point", lang).code, "no_sample_at_point");
    }
  });

  it("un code inconnu : phrase générique, le code brut reste à côté", () => {
    assert.deepEqual(reasonWords("quantum_flux", "en"), { text: GENERIC_WORDS[1], code: "quantum_flux", known: false });
    assert.deepEqual(reasonWords("quantum_flux", "fr"), { text: GENERIC_WORDS[0], code: "quantum_flux", known: false });
    const mixed = reasonWords("outside_us_enc;mystery:42", "en");
    assert.equal(mixed.text, `NOAA charts not read in this area; ${GENERIC_WORDS[1]}`);
    assert.equal(mixed.code, "outside_us_enc;mystery:42");
    assert.equal(mixed.known, false);
    // Unknown source down: still « unreachable », never the code itself.
    assert.equal(reasonWords("gebco_unavailable:ReadTimeout", "en").text, "source unreachable right now");
  });

  it("détail connu après « : », statut HTTP, ou rien : le préfixe ou le détail parlent", () => {
    assert.equal(reasonWords("cdse_stac_unavailable:503", "en").text, "image catalogue unreachable right now");
    assert.equal(reasonWords("cdse_stac_unavailable:no_scene_in_bbox", "en").text, "no recent image here");
    assert.equal(reasonWords("openmeteo_unavailable:no_data", "fr").text, "pas de donnée");
    assert.equal(reasonWords("openmeteo_unavailable:HTTPStatusError", "fr").text, "service météo sans réponse");
    assert.equal(reasonWords("rtofs_unavailable:Error", "en").text, "currents service did not answer");
    assert.equal(reasonWords("review_unavailable", "fr").text, "service de vérification injoignable pour l’instant");
  });

  it("jamais d'exception dans le code montré ; des mots déjà écrits restent tels quels", () => {
    const r = reasonWords("aton_unavailable:HTTPStatusError", "en");
    assert.equal(r.code, "aton_unavailable");
    assert.equal(reasonWords("HTTPStatusError", "fr").text, "indisponible");
    assert.doesNotMatch(reasonWords("Traceback (most recent call last):\n boom", "en").code, /Traceback|boom/);
    assert.deepEqual(reasonWords(null, "en"), { text: "no data", code: null, known: true });
    assert.deepEqual(reasonWords("Le service répond plus tard", "fr"), { text: "Le service répond plus tard", code: null, known: true });
    assert.equal(reasonWords("hors ligne", "en").text, "offline");
  });

  it("chaque code écrit par ici_layers.py a ses mots", () => {
    const src = read("../../server/ici_layers.py");
    const prefixes = [...src.matchAll(/layer_code\(\s*"([a-z_]+)"/g)].map((m) => m[1]);
    const plain = [...src.matchAll(/"reason"\]?\s*[:=]\s*f?"([a-z_]+)[";]/g)].map((m) => m[1]);
    assert.ok(prefixes.length >= 5 && plain.length >= 5, "le motif lit encore le serveur");
    for (const code of [...new Set([...prefixes, ...plain])]) {
      const said = reasonWords(code, "en");
      assert.equal(said.known, true, `${code} sans mots`);
      assert.ok(REASON_WORDS[code] || SOURCE_DOWN_WORDS[code] || /_unavailable$/.test(code), code);
    }
  });
});

describe("briefing « Ici » — mots à l'écran, code en info-bulle", () => {
  const BAG = {
    zee: { name: "Haute mer", mrgid: null, gold: false },
    nearby: { marinas: [], capitaineries: [], wpi: [], anchorages: [] },
    aton: { nearby: [], source: null, reason: "outside_us_enc;overpass_unavailable:ConnectError" },
    emodnet: {
      kind: "observation",
      bathy: { value: null, reason: "no_sample_at_point" },
      seabed: { value: null, reason: "no_feature_at_point" },
      cables: { nearby: false, reason: "no_feature_at_point" },
    },
    sources: { zee: "marineregions", bi: "ok" },
  };

  it("le texte dit les raisons sans code, en anglais et en français", () => {
    const en = narrateIci(BAG, "en");
    assert.match(en, /No aid to navigation recorded here \(NOAA charts not read in this area; map server unreachable right now\)\./);
    assert.match(en, /Seabed \(EMODnet, observation\): depth: no sounding at this point; seabed: no data at this point/);
    assert.doesNotMatch(en, TECHNICAL);
    const fr = narrateIci(BAG, "fr");
    assert.match(fr, /Pas de balisage recensé ici \(cartes NOAA non consultées dans cette zone ; serveur de cartes injoignable pour l’instant\)\./);
    assert.match(fr, /profondeur : pas de sondage à ce point/);
    assert.doesNotMatch(fr, TECHNICAL);
  });

  it("les segments gardent le texte exact et accrochent chaque code à ses mots", () => {
    for (const lang of ["fr", "en"]) {
      const segs = narrateIciSegments(BAG, lang);
      assert.equal(segs.map((s) => s.text).join(""), narrateIci(BAG, lang));
      const codes = segs.filter((s) => s.reason).map((s) => s.reason.code);
      assert.deepEqual(codes, ["outside_us_enc;overpass_unavailable:ConnectError", "no_sample_at_point", "no_feature_at_point"], lang);
      assert.ok(segs.every((s) => !(s.reason && s.entity)), "un code ne remplace jamais un lien");
    }
  });

  it("markReasons ne coupe pas un mot et laisse les liens", () => {
    const segs = markReasons(
      [{ text: "EMODnet", entity: { kind: "source" } }, { text: " no dataset; no data." }],
      [{ text: "no data", code: "null_x" }, { text: "EMODnet", code: "x" }],
    );
    assert.deepEqual(segs, [
      { text: "EMODnet", entity: { kind: "source" } },
      { text: " no dataset; " },
      { text: "no data", reason: { code: "null_x" } },
      { text: "." },
    ]);
  });

  it("le panneau montre le code au survol, pas dans le texte", () => {
    const sidebar = read("../components/Sidebar.jsx");
    assert.match(sidebar, /seg\.reason\?\.code/);
    assert.match(sidebar, /title=\{t\("briefingReasonCode", \{ code: seg\.reason\.code \}\)\}/);
    assert.match(sidebar, /data-testid="briefing-reason"/);
  });
});

describe("reasonWords — review fixes", () => {
  it("names no source, so the phrase stays a plain span that can carry its code", () => {
    for (const [fr, en] of Object.values(SOURCE_DOWN_WORDS)) {
      assert.doesNotMatch(`${fr} ${en}`, /Open-Meteo|RTOFS/);
    }
  });

  it("maps stale_pending", () => {
    assert.equal(reasonWords("stale_pending", "en").text, "forecast being refreshed");
  });

  it("hangs codes in the order the reasons were written", () => {
    const segs = [{ text: "Weather unavailable; currents unavailable." }];
    const out = markReasons(segs, [
      { text: "unavailable", code: "first" },
      { text: "unavailable", code: "second" },
    ]);
    assert.deepEqual(out.filter((s) => s.reason).map((s) => s.reason.code), ["first", "second"]);
    assert.equal(out.map((s) => s.text).join(""), segs[0].text);
  });
});
