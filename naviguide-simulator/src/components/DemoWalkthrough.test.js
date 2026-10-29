import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  DEMO_STEP_IDS, TOUR_DEFAULT_MODELS, describeModelRoles, getDemoSteps, modelDisplayName, wantsTourFromUrl,
} from "./demoWalkthrough.js";
import en from "../i18n/en.js";
import fr from "../i18n/fr.js";

const tr = (dict) => (key, vars = {}) => Object.entries(vars).reduce(
  (s, [k, v]) => s.replace(`{${k}}`, v),
  dict[key] ?? en[key] ?? key,
);

describe("visite guidée des juges", () => {
  it("8 étapes stables, chaque texte vient d'une clé demo* (fr et en)", () => {
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

  it("étape 2 « Qui fait quoi » : Nemotron, Token Factory et Tavily nommés (fr et en)", () => {
    assert.equal(DEMO_STEP_IDS.length, 8);
    assert.equal(DEMO_STEP_IDS[1], "models");
    for (const dict of [en, fr]) {
      const step = getDemoSteps(tr(dict)).find((s) => s.id === "models");
      assert.ok(step, "étape models présente");
      assert.match(step.body, /Nemotron/);
      assert.match(step.body, /Nebius Token Factory/);
      assert.match(dict.demoModelsTavily, /^Tavily/);
      assert.equal(step.side, "right");
    }
    assert.match(en.demoModelsTitle, /^Who does what/);
    assert.match(fr.demoModelsTitle, /^Qui fait quoi/);
  });

  it("statut en direct : noms lus dans configuredModels, compteurs du jour", () => {
    const llm = {
      configuredModels: {
        nano: "nvidia/Nemotron-3_5-Lightning",
        fast: "nvidia/Nemotron-3_5-Lightning",
        write: "nvidia/Nemotron-3.5-Super-VL",
        deep: "nvidia/Nemotron-3-Ultra-550b-a55b",
        judge: "nvidia/Nemotron-3-Ultra-550b-a55b",
      },
      nano: { calls: 2 }, fast: { calls: 3 }, write: { calls: 1 }, deep: { calls: 0 }, judge: { calls: 4 },
      tavily: { calls: 5, credits: 5 },
    };
    const out = describeModelRoles(llm, tr(en));
    assert.equal(out.live, true);
    assert.deepEqual(out.rows.map((r) => r.id), ["quick", "write", "deep", "tavily"]);
    assert.match(out.rows[0].text, /^Nemotron 3\.5 Lightning: /);
    assert.match(out.rows[1].text, /^Nemotron 3\.5 Super VL: writes the film/);
    assert.match(out.rows[2].text, /^Nemotron 3 Ultra: edits and re-reads/);
    assert.match(out.rows[3].text, /^Tavily: /);
    assert.equal(out.today, "Today on this server: 10 Nemotron calls, 5 Tavily searches.");
  });

  it("override serveur : un id inconnu reste brut, deux modèles d'un même rôle sont tous deux cités", () => {
    const out = describeModelRoles({ configuredModels: { nano: "nvidia/nemotron-3-nano-30b-a3b", write: "acme/x-1" } }, tr(fr));
    assert.match(out.rows[0].text, /^Nemotron 3 Nano 30B \+ Nemotron 3\.5 Lightning : /);
    assert.match(out.rows[1].text, /^acme\/x-1 : /);
    assert.equal(modelDisplayName(""), "");
  });

  it("sans statut : défauts du code signalés (live=false), aucun compteur inventé", () => {
    const out = describeModelRoles(null, tr(en));
    assert.equal(out.live, false);
    assert.equal(out.today, null);
    assert.match(out.rows[1].text, /^Nemotron 3\.5 Super VL/);
    assert.equal(TOUR_DEFAULT_MODELS.write, "nvidia/Nemotron-3.5-Super-VL");
  });

  it("lien profond ?tour=1", () => {
    assert.equal(wantsTourFromUrl("?tour=1"), true);
    assert.equal(wantsTourFromUrl("?lang=en&tour=true"), true);
    assert.equal(wantsTourFromUrl("?tour=0"), false);
    assert.equal(wantsTourFromUrl(""), false);
    assert.equal(wantsTourFromUrl(undefined), false);
  });
});
