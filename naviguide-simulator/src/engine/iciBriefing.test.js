import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { narrateIci, phraseForEvent } from "./iciBriefing.js";

const FORBIDDEN = /Ports\s*\/\s*Sécurité|AgentPanel|\/agents\/|Cruisers|Nemotron|Tavily/i;

describe("narrateIci", () => {
  it("tells the bag at La Rochelle, not the whole map", () => {
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
      science: {
        nearby: [
          { name: "Pertuis charentais bathymétrie", source: "sextant", nm: 6, url: "https://sextant.ifremer.fr/x" },
          { name: "6901234", source: "argo", kind: "argo_float", wmo: "6901234", nm: 18 },
        ],
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
    assert.match(text, /fiches Science/);
    assert.match(text, /sextant/);
    assert.match(text, /argo/);
    assert.doesNotMatch(text, FORBIDDEN);
    assert.doesNotMatch(text, /4500|mappemonde entière|toute la carte/i);
  });

  it("says inland outside the EEZ without inventing ports of entry", () => {
    const text = narrateIci({
      zee: { name: "À terre (France)", mrgid: null, gold: false, ashore: true },
      poe: [],
      amp: [],
      projects: [],
      nearby: { marinas: [], capitaineries: [], wpi: [] },
      sources: { zee: "marineregions", bi: "ok" },
    }, "fr");
    assert.match(text, /à terre/i);
    assert.match(text, /hors ZEE/);
    assert.doesNotMatch(text, /ports d’entrée officiels les plus proches/);
  });

  it("null ZEE = haute mer, pas une erreur de nommage", () => {
    const text = narrateIci({
      zee: null,
      poe: [],
      nearby: { marinas: [], capitaineries: [], wpi: [] },
      sources: { zee: "error", bi: "ok" },
    }, "fr");
    assert.match(text, /haute mer/i);
    assert.doesNotMatch(text, /pas pu nommer/);
    assert.doesNotMatch(text, /MarineRegions n’a pas répondu/);
  });

  it("says high seas without inventing ports of entry", () => {
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

  it("stays honest if Blue Intelligence is silent", () => {
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

  it("does not dump a list of projects", () => {
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

  it("has an English story of the same bag", () => {
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

  it("cites GEBCO when an offshore sounding is in the bag", () => {
    const text = narrateIci({
      zee: { name: "Haute mer", mrgid: null, gold: false },
      poe: [],
      nearby: { marinas: [], capitaineries: [], wpi: [] },
      depthOffshore: -3200,
      sources: { zee: "marineregions", bi: "ok" },
    }, "fr");
    assert.match(text, /GEBCO/);
    assert.match(text, /3200/);
    const silent = narrateIci({
      zee: { name: "Haute mer", mrgid: null, gold: false },
      nearby: { marinas: [], capitaineries: [], wpi: [] },
      depthOffshore: 0,
      sources: { zee: "marineregions", bi: "ok" },
    }, "fr");
    assert.doesNotMatch(silent, /GEBCO/);
  });

  it("tells the atlas point under the boat, not a forecast", () => {
    const text = narrateIci({
      zee: { name: "Haute mer", mrgid: null, gold: false },
      nearby: { marinas: [], capitaineries: [], wpi: [] },
      climatology: {
        kind: "climatology",
        source: "atlas",
        month: 6,
        period: "1980-2020",
        doi: { wind: "10.48670/moi-00183" },
        point: {
          kind: "climatology",
          wind_atlas: { most_likely: { speed_knots: 16.2, dir_deg: 55 } },
          wave: { hs_p50_m: 1.4, hs_p90_m: 2.8 },
          current: { speed_knots: 0.4, direction_to_deg: 270 },
          cyclone: { crossings_if_leg: { count: 2 } },
        },
      },
      sources: { zee: "marineregions", bi: "ok", climatology: "atlas" },
    }, "fr");
    assert.match(text, /kind climatology/);
    assert.match(text, /16\.2 kn/);
    assert.match(text, /Hs P50 1\.4/);
    assert.match(text, /Hs P90 2\.8/);
    assert.match(text, /courant 0\.4/);
    assert.match(text, /IBTrACS/);
    assert.doesNotMatch(text, /forecast|GRIB/i);
  });

  it("tells visit vs manager, OSM moorings, AtoN, satellite observation and forecast weather", () => {
    const text = narrateIci({
      zee: { name: "French Exclusive Economic Zone", mrgid: 5677, gold: true },
      amp: [{
        name: "Pertuis charentais",
        nm: 8,
        visit_url: "https://parc-marin.fr/visite",
        manager_url: "https://parc-marin.fr",
      }],
      nearby: {
        marinas: [],
        capitaineries: [],
        wpi: [],
        anchorages: [{ name: "Mouillage des Minimes", nm: 1.2 }],
      },
      aton: { nearby: [{ name: "Feu des Minimes", nm: 0.8 }], source: "osm-overpass" },
      satellites: {
        kind: "observation",
        source: "cdse-stac",
        scene: {
          kind: "observation",
          product: "sentinel-2-l2a",
          id: "S2C_MSIL2A_X",
          datetime: "2026-09-12T11:06:31Z",
        },
        derived: {
          coastline: { value: null, reason: "not_generated" },
          sdb: { value: null, reason: "not_generated" },
        },
      },
      weather: {
        kind: "forecast",
        source: "openmeteo-gfs",
        model: "GFS 0.25° / GFS-Wave 0.25° (Open-Meteo)",
        wind: { kind: "forecast", speedKnots: 12.4, dirFromDeg: 280 },
        wave: { kind: "forecast", hs: 1.1 },
        current: { kind: "forecast", source: "noaa-rtofs", speedKnots: 0.58, dirToDeg: 247 },
        current_reason: null,
      },
      emodnet: {
        kind: "observation",
        bathy: { depth_m: 18.4 },
        seabed: { label: "sand" },
        cables: { nearby: false, reason: "no_feature_at_point" },
      },
      review: { zee: { gold_on: true }, amp: { gold_on: false } },
      climatology: {
        kind: "climatology",
        source: "atlas",
        month: 6,
        period: "1980-2020",
        doi: { wind: "10.48670/moi-00183" },
        rose: { stat: "rose", directions_from: [{ dir_deg: 45, pct: 22 }], calm_pct: 4, gale_pct: 1.5 },
        point: {
          kind: "climatology",
          wind_atlas: { most_likely: { speed_knots: 16.2, dir_deg: 55 } },
          current: { speed_knots: 0.4, direction_to_deg: 270 },
          cyclone: { nearby: 0 },
        },
      },
      sources: { zee: "marineregions", bi: "ok" },
    }, "fr");
    assert.match(text, /visite parc-marin\.fr/);
    assert.match(text, /gestionnaire parc-marin\.fr/);
    assert.match(text, /Mouillage des Minimes/);
    assert.match(text, /AtoN/);
    assert.match(text, /kind observation/);
    assert.match(text, /sentinel-2-l2a/);
    assert.match(text, /not_generated/);
    assert.match(text, /kind forecast/);
    assert.match(text, /12\.4 kn/);
    assert.match(text, /0\.58 kn \/ 247° \(RTOFS, kind forecast\)/);
    assert.match(text, /EMODnet/);
    assert.match(text, /18\.4/);
    assert.match(text, /rose 8 secteurs/);
    assert.match(text, /calme 4/);
    assert.match(text, /vers 270/);
    assert.match(text, /IBTrACS nearby 0/);
    assert.match(text, /Gold oui/);
    assert.doesNotMatch(text, FORBIDDEN);
  });

  it("does not invent a satellite scene when the product is missing", () => {
    const text = narrateIci({
      zee: { name: "Haute mer", mrgid: null, gold: false },
      nearby: { marinas: [], capitaineries: [], wpi: [], anchorages: [] },
      satellites: {
        kind: "observation",
        scene: null,
        reason: "cdse_stac_unavailable:HTTPStatusError",
        derived: { coastline: { value: null, reason: "not_generated" } },
      },
      weather: { kind: "forecast", wind: null, reason: "openmeteo_unavailable:HTTPStatusError" },
      sources: { zee: "marineregions", bi: "ok" },
    }, "fr");
    assert.match(text, /kind observation/);
    assert.match(text, /aucune scène générée/);
    assert.match(text, /cdse_stac_unavailable/);
    assert.match(text, /kind forecast/);
    assert.doesNotMatch(text, /Sentinel-2 L2A 20/);
    assert.doesNotMatch(text, FORBIDDEN);
  });

  it("says current null only when RTOFS is dead or off-grid", () => {
    const text = narrateIci({
      zee: { name: "Haute mer", mrgid: null, gold: false },
      nearby: { marinas: [], capitaineries: [], wpi: [], anchorages: [] },
      weather: {
        kind: "forecast",
        wind: { kind: "forecast", speedKnots: 8, dirFromDeg: 90 },
        current: null,
        current_reason: "off_grid",
      },
      sources: { zee: "marineregions" },
    }, "fr");
    assert.match(text, /courant null \(off_grid\)/);
    assert.doesNotMatch(text, /rtofs_not_ingested/);
    assert.doesNotMatch(text, FORBIDDEN);
  });

  it("cites kind on a wind-shift and never mentions Nemotron", () => {
    const text = narrateIci({
      zee: { name: "Haute mer", mrgid: null, gold: false },
      nearby: { marinas: [], capitaineries: [], wpi: [] },
      event: {
        type: "wind-shift",
        payload: {
          tws: 18,
          twd: 240,
          dTws: 10,
          kind: "forecast",
          source: "GFS",
          tavily: null,
          nvidia: null,
        },
      },
      sources: { zee: "marineregions" },
    }, "fr");
    assert.match(text, /Vent 18 kn \/ 240°/);
    assert.match(text, /kind: forecast/);
    assert.match(text, /\+10 kn/);
    assert.doesNotMatch(text, FORBIDDEN);
  });

  it("tells a Suivre rain refuge from the pack, not a model", () => {
    const text = phraseForEvent({
      type: "marina-refuge",
      payload: {
        harbour: { name: "Port des Minimes", nm: 6 },
        rainMm: 6,
        kind: "forecast",
      },
    }, "fr");
    assert.match(text, /Pluie 6 mm\/h \(GFS\)/);
    assert.match(text, /Repli : Port des Minimes à 6 nm/);
    assert.doesNotMatch(text, FORBIDDEN);
  });

  it("prefers a ready story over the local template", () => {
    const text = phraseForEvent({
      type: "zee-enter",
      name: "Spain",
      phrase: "On vient d’entrer dans Spain.",
      story: { status: "ready", text: "Récit NIM : entrée dans la ZEE espagnole." },
    }, "fr");
    assert.equal(text, "Récit NIM : entrée dans la ZEE espagnole.");
    assert.doesNotMatch(text, FORBIDDEN);
  });

  it("tells a ZEE ahead on the track", () => {
    const text = phraseForEvent({
      type: "zee-ahead",
      whenNm: 40,
      name: "Spanish Exclusive Economic Zone",
      payload: { zee: { name: "Spanish Exclusive Economic Zone", mrgid: 8462 }, whenNm: 40 },
    }, "fr");
    assert.match(text, /Devant dans 40 nm/);
    assert.match(text, /Spanish Exclusive Economic Zone/);
    assert.doesNotMatch(text, FORBIDDEN);
  });

  it("tells an AMP ahead on the track", () => {
    const text = phraseForEvent({
      type: "amp-ahead",
      whenNm: 40,
      payload: {
        amp: { name: "Cabrera", visitable: true },
        visitable: true,
        whenNm: 40,
      },
    }, "fr");
    assert.match(text, /AMP sur le trait dans 40 nm/);
    assert.match(text, /Cabrera/);
    assert.doesNotMatch(text, FORBIDDEN);
  });

  it("summarises a group digest", () => {
    const text = phraseForEvent({
      type: "group",
      digest: { fr: "Depuis cette jambe : zee-enter + amp-enter.", en: "Along this leg: zee-enter + amp-enter." },
      payload: { members: ["zee-enter", "amp-enter"] },
    }, "fr");
    assert.match(text, /zee-enter \+ amp-enter/);
  });

  it("says shelf or grounding with the skipper's depth threshold, never haut-fond for 15 m", () => {
    const shelf = phraseForEvent({
      type: "depth-alert",
      payload: { depthM: 12.4, source: "emodnet", alertM: 15, label: "plateau" },
    }, "fr");
    assert.match(shelf, /^On approche du plateau : 12\.4 m sondés, sous 15 m/);
    assert.doesNotMatch(shelf, /Haut-fond/);
    const ground = phraseForEvent({
      type: "depth-alert",
      payload: { depthM: 4.1, source: "gebco", alertM: 5, label: "talonnage" },
    }, "en");
    assert.match(ground, /^Grounding risk: 4\.1 m sounded, under 5 m/);
    const legacy = phraseForEvent({ type: "depth-alert", payload: { depthM: 9, source: "emodnet" } }, "fr");
    assert.match(legacy, /^Haut-fond 9 m/);
  });
});
