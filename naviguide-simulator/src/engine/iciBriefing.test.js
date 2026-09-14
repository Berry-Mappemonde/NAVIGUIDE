import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { narrateIci } from "./iciBriefing.js";

const FORBIDDEN = /Ports\s*\/\s*Sécurité|AgentPanel|\/agents\/|Cruisers|Nemotron|Tavily/i;

describe("narrateIci", () => {
  it("raconte le sac à La Rochelle, pas toute la carte", () => {
    const text = narrateIci({
      zee: {
        name: "French Exclusive Economic Zone",
        mrgid: 5677,
        territory: "france_metropolitaine",
        gold: true,
      },
      poe: [
        { name: "La Rochelle", nm: 1.2, url: "https://www.douane.gouv.fr/la-rochelle" },
        { name: "Rochefort", nm: 18 },
      ],
      amp: [{ name: "Pertuis charentais", nm: 8 }],
      projects: [{ name: "Récif sentinelle", nm: 12 }],
      nearby: {
        marinas: [{ name: "Port des Minimes", nm: 2 }],
        capitaineries: [{ name: "Capitainerie La Rochelle", nm: 1 }],
        wpi: [{ name: "LA ROCHELLE", nm: 1.1 }],
      },
      polar: { boat: "Leopard 46", speedKnots: 7.2, etaHours: 42 },
      marks: [{ kind: "leg", from: "La Rochelle", to: "Fort-de-France", vehicle: "main" }],
      event: { type: "zee-enter", name: "French Exclusive Economic Zone", mrgid: 5677 },
      sources: { zee: "marineregions", bi: "ok" },
    }, "fr");

    assert.match(text, /Ici, le bateau/);
    assert.match(text, /Gold/);
    assert.match(text, /La Rochelle/);
    assert.match(text, /douane\.gouv\.fr/);
    assert.match(text, /30 milles/);
    assert.match(text, /Pertuis/);
    assert.match(text, /On vient d’entrer/);
    assert.match(text, /Fort-de-France/);
    assert.match(text, /7\.2 nœuds/);
    assert.doesNotMatch(text, FORBIDDEN);
    assert.doesNotMatch(text, /4500|mappemonde entière|toute la carte/i);
  });

  it("dit la haute mer sans inventer des ports d’entrée", () => {
    const text = narrateIci({
      zee: { name: "Haute mer", mrgid: null, gold: false },
      poe: [],
      amp: [],
      projects: [],
      nearby: { marinas: [], capitaineries: [], wpi: [] },
      sources: { zee: "marineregions", bi: "ok" },
    }, "fr");
    assert.match(text, /haute mer/i);
    assert.doesNotMatch(text, /ports d’entrée officiels les plus proches/);
    assert.doesNotMatch(text, FORBIDDEN);
  });

  it("reste honnête si Blue Intelligence est muet", () => {
    const text = narrateIci({
      zee: { name: "French Exclusive Economic Zone", mrgid: 5677, territory: "france_metropolitaine", gold: false },
      poe: [],
      amp: [],
      projects: [],
      nearby: { marinas: [], capitaineries: [], wpi: [{ name: "LA ROCHELLE", nm: 1 }] },
      sources: { zee: "marineregions", bi: "unavailable" },
    }, "fr");
    assert.match(text, /Blue Intelligence n’ont pas répondu/);
    assert.match(text, /LA ROCHELLE/);
    assert.doesNotMatch(text, FORBIDDEN);
  });

  it("ne dump pas une liste de projets", () => {
    const projects = Array.from({ length: 40 }, (_, i) => ({ name: `Projet ${i}`, nm: i + 1 }));
    const text = narrateIci({
      zee: { name: "French Exclusive Economic Zone", mrgid: 5677, gold: true },
      poe: [],
      amp: [],
      projects,
      nearby: { marinas: [], capitaineries: [], wpi: [] },
      sources: { zee: "marineregions", bi: "ok" },
    }, "fr");
    assert.match(text, /Projet 0/);
    assert.doesNotMatch(text, /Projet 10/);
    assert.doesNotMatch(text, FORBIDDEN);
  });

  it("a un récit anglais du même sac", () => {
    const text = narrateIci({
      zee: { name: "French Exclusive Economic Zone", mrgid: 5677, territory: "guyane", gold: true },
      poe: [{ name: "Cayenne", nm: 2 }],
      amp: [],
      projects: [],
      nearby: { marinas: [], capitaineries: [], wpi: [] },
      marks: [{ kind: "leg", from: "Cayenne", vehicle: "plane", phase: "air-out" }],
      sources: { zee: "marineregions", bi: "ok" },
    }, "en");
    assert.match(text, /French Guiana/);
    assert.match(text, /at the dock/);
    assert.doesNotMatch(text, FORBIDDEN);
  });
});
