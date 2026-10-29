import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { DEMO_STEP_IDS, getDemoSteps } from "./demoWalkthrough.js";
import en from "../i18n/en.js";
import fr from "../i18n/fr.js";

const tr = (dict) => (key, vars = {}) => Object.entries(vars).reduce(
  (s, [k, v]) => s.replace(`{${k}}`, v),
  dict[key] ?? en[key] ?? key,
);

describe("visite guidée des juges", () => {
  it("7 étapes stables, chaque texte vient d'une clé demo* (fr et en)", () => {
    for (const dict of [en, fr]) {
      for (const opts of [{}, { custom: true }, { replayState: "ready" }, { replayState: "playing" }]) {
        const steps = getDemoSteps(tr(dict), opts);
        assert.deepEqual(steps.map((s) => s.id), DEMO_STEP_IDS);
        for (const s of steps) {
          assert.ok(s.title && !/^demo|^replay/.test(s.title), `titre traduit : ${s.id}`);
          assert.ok(s.body && !/^demo/.test(s.body), `texte traduit : ${s.id}`);
        }
      }
    }
  });

  it("titre de l'étape film = replayStart, comme la barre du film", () => {
    assert.equal(getDemoSteps(tr(fr)).find((s) => s.id === "replay").title, fr.replayStart);
    assert.equal(getDemoSteps(tr(en)).find((s) => s.id === "replay").title, en.replayStart);
  });

  it("route de l'utilisateur : ni « film officiel » ni « suit la route Berry-Mappemonde »", () => {
    for (const dict of [en, fr]) {
      for (const replayState of ["ready", "unavailable", "playing"]) {
        const steps = getDemoSteps(tr(dict), { custom: true, replayState });
        const all = steps.map((s) => s.body).join(" ");
        assert.doesNotMatch(all, /film officiel|official film|stock officiel|official store/i);
        assert.doesNotMatch(steps.find((s) => s.id === "live").body, /^La carte suit la route Berry|^The map follows the Berry/);
        assert.doesNotMatch(steps.find((s) => s.id === "trace").body, /Cliquez sur la carte|Click the map/);
      }
    }
  });

  it("trois états du film : prêt, en lecture, indisponible (sans faux film)", () => {
    const body = (replayState) => getDemoSteps(tr(fr), { replayState }).find((s) => s.id === "replay").body;
    assert.match(body("ready"), /bouton ci-dessous/);
    assert.equal(body("playing"), fr.demoPlaying);
    assert.doesNotMatch(body("playing"), /bouton ci-dessous/);
    assert.match(body("unavailable"), /faux film/);
  });

  it("formulation honnête de la position (calculée, pas observée)", () => {
    assert.doesNotMatch(fr.demoWelcomeBody, /données réelles/);
    assert.match(fr.demoWelcomeBody, /calculée à partir du plan officiel/);
    assert.match(en.demoWelcomeBody, /computed from the official plan/);
  });

  it("un seul nom en anglais, et aucun bouton qui ressemble à Terminer / Finish", () => {
    const enDemo = Object.entries(en).filter(([k]) => k.startsWith("demo")).map(([, v]) => v).join(" ");
    assert.doesNotMatch(enDemo, /walkthrough|guided demo/i);
    for (const dict of [en, fr]) {
      for (const k of ["demoEnd", "demoExit", "demoClose", "demoPrev", "demoNext"]) {
        assert.doesNotMatch(dict[k], /terminer|finish/i, `${k} ne doit pas matcher les specs du tracé`);
      }
    }
  });

  it("panneau du côté opposé au panneau que l'étape ouvre", () => {
    const side = Object.fromEntries(getDemoSteps(tr(en)).map((s) => [s.id, s.side]));
    assert.equal(side.layers, "left");
    assert.equal(side.trace, "left");
    assert.equal(side.briefing, "right");
  });
});
