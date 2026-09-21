import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { cleanStoryText, climatologySentence, climatologyShownOnBanner, narrateIci, narrateIciSegments, phraseForEvent } from "./iciBriefing.js";
import { KNOWN_SOURCES, SOURCE_URLS, segmentSources } from "./briefingLinks.js";

const here = dirname(fileURLToPath(import.meta.url));

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

    assert.match(text, /Le bateau navigue dans/);
    assert.match(text, /formalités d’entrée passent par des ports officiels/);
    assert.match(text, /La Rochelle/);
    assert.match(text, /Ports d’entrée officiels les plus proches : La Rochelle \(1,2 nm\)/);
    assert.match(text, /Fiches d’entrée : douane\.gouv\.fr/);
    assert.doesNotMatch(text, /https:\/\/www\.douane\.gouv\.fr\/la-rochelle/);
    assert.match(text, /30 milles/);
    assert.match(text, /Pertuis/);
    assert.match(text, /On vient d’entrer/);
    assert.match(text, /Cap sur Fort-de-France[^.]*depuis La Rochelle/);
    assert.match(text, /7,2 nœuds/);
    assert.match(text, /de mer/);
    assert.equal((text.match(/Polaire chargée/g) || []).length, 1);
    assert.match(text, /Données scientifiques disponibles autour du bateau/);
    assert.match(text, /Pertuis charentais bathymétrie \(6 nm\)/);
    assert.match(text, /6901234 \(18 nm\)/);
    assert.doesNotMatch(text, /\(sextant\)|\(argo\)|sextant\.ifremer\.fr/); // source + host live in the link
    assert.doesNotMatch(text, FORBIDDEN);
    assert.doesNotMatch(text, /4500|mappemonde entière|toute la carte/i);
  });

  it("does not call a sea leg overland just because the boat is in port", () => {
    const text = narrateIci({
      zee: { name: "À terre (France)", mrgid: null, gold: false, ashore: true },
      nearby: { marinas: [], capitaineries: [], wpi: [] },
      polar: { boat: "Leopard 46", etaHours: 313.95 },
      marks: [{
        kind: "leg",
        from: "La Rochelle",
        to: "Ajaccio (Corse)",
        vehicle: "land",
      }],
      sources: { zee: "marineregions", bi: "ok" },
    }, "fr");
    assert.match(text, /Cap sur Ajaccio \(Corse\) depuis La Rochelle/);
    assert.match(text, /13 jours de mer/);
    assert.doesNotMatch(text, /pas encore en mer/);
    assert.doesNotMatch(text, /313 h/);
  });

  it("treats Berry → La Rochelle as overland even if the ZEE bag is empty", () => {
    const text = narrateIci({
      zee: null,
      nearby: { marinas: [], capitaineries: [], wpi: [] },
      polar: { etaHours: 4 },
      marks: [{
        kind: "leg",
        from: "Saint-Maur (Berry, Indre)",
        to: "La Rochelle",
        vehicle: "main",
      }],
      sources: { zee: "error" },
    }, "fr");
    assert.match(text, /Étape terrestre de Saint-Maur \(Berry, Indre\) vers La Rochelle/);
    assert.match(text, /encore 4 h de route/);
    assert.match(text, /pas encore en mer/);
    assert.doesNotMatch(text, /encore 4 h de mer/);
  });

  it("calls Saint-Maur → La Rochelle overland, not sea time", () => {
    const id = "S2B_MSIL2A_20260914T105619_N0512_R094_T31TDM_20260914T145142";
    const text = narrateIci({
      zee: { name: "À terre (France)", mrgid: null, gold: false, ashore: true },
      poe: [],
      nearby: { marinas: [], capitaineries: [], wpi: [] },
      polar: { boat: "Leopard 46", etaHours: 4 },
      marks: [{
        kind: "leg",
        from: "Saint-Maur (Berry, Indre)",
        to: "La Rochelle",
        vehicle: "land",
      }],
      satellites: {
        kind: "observation",
        scene: { product: "sentinel-2-l2a", id, datetime: "2026-09-14T10:56:19Z" },
      },
      sources: { zee: "marineregions", bi: "ok" },
    }, "fr");
    assert.match(text, /Étape terrestre de Saint-Maur \(Berry, Indre\) vers La Rochelle/);
    assert.match(text, /encore 4 h de route/);
    assert.match(text, /pas encore en mer/);
    assert.doesNotMatch(text, /encore 4 h de mer/);
    // the raw scene id no longer floods the box: satellite, tile and date are written instead
    assert.match(text, /Sentinel-2 \(S2B, tuile T31TDM\) du 14 septembre 2026 \(observation\)/);
    assert.doesNotMatch(text, new RegExp(id));
    assert.doesNotMatch(text, FORBIDDEN);
  });

  it("keeps the ICI briefing inside the sidebar box", () => {
    const sidebar = readFileSync(join(here, "../components/Sidebar.jsx"), "utf8");
    assert.match(sidebar, /ici-briefing/);
    assert.match(sidebar, /overflow-x-hidden/);
    assert.match(sidebar, /overflow-wrap:anywhere/);
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
    assert.match(text, /hors de toute ZEE/);
    assert.doesNotMatch(text, /Ports d’entrée officiels/);
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
    assert.doesNotMatch(text, /Marine Regions\/VLIZ n’a pas répondu/);
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
    assert.doesNotMatch(text, /Ports d’entrée officiels/);
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

  it("lot T : une perle mince ne raconte pas l’échec BI", () => {
    const thin = {
      pearl: "thin",
      thin: true,
      zee: { name: "Mauritanian Exclusive Economic Zone", mrgid: 8492 },
      poe: [],
      amp: [],
      projects: [],
      nearby: { marinas: [], capitaineries: [], wpi: [] },
      sources: { zee: "marineregions", bi: "unavailable" },
    };
    const text = narrateIci(thin, "fr");
    assert.doesNotMatch(text, /Blue Intelligence n’ont pas répondu/);
    assert.doesNotMatch(text, /ports WPI sont conservés/);
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
          wave: { hs_p50_m: 1.4, hs_p90_m: 2.8, period_s: 4.1, dir_deg: 284.6 },
          current: { speed_knots: 0.4, direction_to_deg: 270 },
          cyclone: { crossings_if_leg: { count: 2 } },
        },
      },
      sources: { zee: "marineregions", bi: "ok", climatology: "atlas" },
    }, "fr");
    assert.equal(climatologyShownOnBanner({
      climatology: {
        kind: "climatology", source: "atlas", month: 6,
        point: { wind_atlas: { most_likely: { speed_knots: 16.2, dir_deg: 55 } } },
      },
    }), true);
    assert.doesNotMatch(text, /Climatologie de/);
    const climo = climatologySentence({
      climatology: {
        kind: "climatology",
        source: "atlas",
        month: 6,
        period: "1980-2020",
        doi: { wind: "10.48670/moi-00183" },
        point: {
          kind: "climatology",
          wind_atlas: { most_likely: { speed_knots: 16.2, dir_deg: 55 } },
          wave: { hs_p50_m: 1.4, hs_p90_m: 2.8, period_s: 4.1, dir_deg: 284.6 },
          current: { speed_knots: 0.4, direction_to_deg: 270 },
          cyclone: { crossings_if_leg: { count: 2 } },
        },
      },
    }, "fr");
    assert.match(climo, /Climatologie de/);
    assert.match(climo, /atlas Copernicus Marine/);
    assert.match(climo, /vent typique 16,2 kn/);
    assert.match(climo, /mer 1,4 m en moyenne, 2,8 m les jours agités \(P90\)/);
    assert.match(climo, /période 4,1 s/);
    assert.match(climo, /de ONO \(285°\)/);
    assert.match(climo, /courant 0,4/);
    assert.match(climo, /IBTrACS/);
    assert.doesNotMatch(climo, /forecast|GRIB/i);
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
        wave: { kind: "forecast", hs: 1.1, dirDeg: 270, periodS: 6.5 },
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
    assert.match(text, /Aires marines protégées à moins de 30 milles : Pertuis charentais/);
    assert.doesNotMatch(text, /parc-marin\.fr/); // visit / manager pages are links now
    assert.match(text, /Mouillage des Minimes/);
    assert.match(text, /Balisage \(OpenStreetMap\) : Feu des Minimes/);
    assert.match(text, /Dernière image satellite \(CDSE\) : Sentinel-2/);
    assert.match(text, /\(observation\)/);
    assert.match(text, /pas encore calculé/);
    assert.doesNotMatch(text, /not_generated|sentinel-2-l2a/);
    assert.match(text, /Prévision météo/);
    assert.match(text, /vent 12,4 kn de O \(280°\)/);
    assert.match(text, /mer 1,1 m de O \(270°\), période 6,5 s/);
    assert.match(text, /courant 0,58 kn vers OSO \(247°\) \(NOAA\/RTOFS\)/);
    assert.match(text, /EMODnet/);
    assert.match(text, /18,4/);
    assert.doesNotMatch(text, /Climatologie de|rose des vents disponible/);
    const climo = climatologySentence({
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
    }, "fr");
    assert.match(climo, /rose des vents disponible/);
    assert.match(climo, /calme 4/);
    assert.match(climo, /courant 0,4 kn vers O \(270°\)/);
    assert.match(climo, /cyclones historiques \(IBTrACS\) : aucun à proximité/);
    assert.match(text, /formalités ZEE vérifiées, règles AMP non vérifiées/);
    assert.doesNotMatch(text, FORBIDDEN);
  });

  it("lot P: a rich pearl tells seabed and aids to navigation; weather, satellite and the sheet stay live-only", () => {
    const pearl = {
      pearl: "rich",
      zee: { name: "French Exclusive Economic Zone", mrgid: 5677 },
      amp: [],
      nearby: { marinas: [], capitaineries: [], wpi: [], anchorages: [] },
      aton: { nearby: [{ name: "Feu des Minimes", nm: 0.8 }], source: "osm-overpass" },
      emodnet: { kind: "observation", bathy: { depth_m: 18.4 }, seabed: { label: "sand" }, cables: { nearby: false, reason: "no_feature_at_point" } },
      weather: { kind: null, reason: "not_in_along_pearl" },
      satellites: { kind: null, reason: "not_in_along_pearl" },
      review: { reason: "not_in_along_pearl" },
      sources: { zee: "marineregions", bi: "ok" },
    };
    const rich = narrateIci(pearl, "fr");
    assert.match(rich, /Balisage \(OpenStreetMap\) : Feu des Minimes/);
    assert.match(rich, /EMODnet/);
    assert.match(rich, /18,4/);
    assert.doesNotMatch(rich, /perle|pearl|météo|satellite|Sentinel|Gold|fiche de vérification/i);
    // A thin pearl (the server sends empty seabed / aids with a reason) says nothing about them.
    const thin = narrateIci({ ...pearl, pearl: "thin", aton: { nearby: [], reason: "not_in_along_pearl" }, emodnet: { reason: "not_in_along_pearl" } }, "fr");
    assert.doesNotMatch(thin, /EMODnet|18,4|Balisage/);
    assert.doesNotMatch(thin, /perle|pearl|météo|satellite/i);
  });

  it("says weather is loading while the shared pipeline is pending", () => {
    const text = narrateIci({
      zee: { name: "Haute mer", mrgid: null, gold: false },
      nearby: { marinas: [], capitaineries: [], wpi: [], anchorages: [] },
      weather: { kind: "forecast", status: "pending", refreshing: true, wind: null, wave: null },
      sources: { zee: "marineregions" },
    }, "fr");
    assert.match(text, /Prévision météo : chargement/);
    assert.doesNotMatch(text, /vide/);
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
    assert.match(text, /Aucune image satellite récente ici \(cdse_stac_unavailable/);
    assert.match(text, /Prévision météo/);
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
    assert.match(text, /courant : hors de la grille du modèle/);
    assert.doesNotMatch(text, /off_grid|null/);
    assert.doesNotMatch(text, /rtofs_not_ingested/);
    assert.doesNotMatch(text, FORBIDDEN);
  });

  it("says fonds null when EMODnet has a map footprint but no Folk class", () => {
    const text = narrateIci({
      zee: { name: "French Exclusive Economic Zone", mrgid: 5677, gold: true },
      nearby: { marinas: [], capitaineries: [], wpi: [], anchorages: [] },
      emodnet: {
        kind: "observation",
        bathy: { depth_m: 2.3 },
        seabed: { label: null, reason: "no_substrate_class" },
        cables: { nearby: false, reason: "no_feature_at_point" },
      },
      sources: { zee: "marineregions", bi: "ok" },
    }, "fr");
    assert.match(text, /Fond \(EMODnet, observation\) : 2,3 m sur la carte ; nature du fond non classée ici/);
    assert.doesNotMatch(text, /no_substrate_class|DTM/);
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

  it("a story about the machinery is cleaned, or replaced by the local phrase (revue du 19 sept.)", () => {
    const verbose = phraseForEvent({
      type: "poe-ahead",
      phrase: "Port d’entrée officiel devant : Porto-Vecchio (292 nm).",
      story: {
        status: "ready",
        text: "**Briefing nautique**\n\nLe port d’entrée officiel se situe à Porto-Vecchio, à 292,3 nm. "
          + "L’évènement est classé comme poe-ahead et porte l’identifiant poe-ahead:5682. "
          + "Il a été jugé now avec la raison playhead. Le navire, un Leopard 46 de 14 m et 1,4 m de tirant d’eau, est en croisière. "
          + "Aucune information supplémentaire sur la période ou un DOI n’est disponible.",
      },
    }, "fr");
    assert.equal(verbose, "Le port d’entrée officiel se situe à Porto-Vecchio, à 292,3 nm.");
    const onlyMeta = phraseForEvent({
      type: "zee-exit",
      phrase: "Retour en haute mer — plus de ZEE à déclarer.",
      story: { status: "ready", text: "L’événement zee-exit est classé info. La décision a été prise immédiatement (juge)." },
    }, "fr");
    assert.equal(onlyMeta, "Retour en haute mer — plus de ZEE à déclarer.");
    assert.equal(cleanStoryText(null), "");
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

const FULL_BAG = {
  zee: { name: "French Exclusive Economic Zone", mrgid: 5677, gold: true, territory: "france_metropolitaine" },
  poe: [{ name: "La Rochelle", nm: 1.2, url: "https://www.douane.gouv.fr/la-rochelle" }],
  amp: [{ name: "Pertuis charentais", nm: 8 }],
  nearby: { marinas: [{ name: "Port des Minimes", nm: 2 }], capitaineries: [], wpi: [] },
  aton: { nearby: [{ name: "Feu des Minimes", nm: 0.8 }], source: "osm-overpass" },
  satellites: {
    kind: "observation",
    source: "cdse-stac",
    scene: {
      product: "sentinel-2-l2a",
      id: "S2B_MSIL2A_20260914T105619_N0512_R094_T31TDM_20260914T145142",
      datetime: "2026-09-14T10:56:19Z",
    },
  },
  weather: {
    kind: "forecast",
    source: "openmeteo-gfs",
    model: "GFS 0.25° (Open-Meteo)",
    wind: { kind: "forecast", speedKnots: 12.4, dirFromDeg: 280 },
    current: { kind: "forecast", source: "noaa-rtofs", speedKnots: 0.58, dirToDeg: 247 },
  },
  emodnet: { kind: "observation", bathy: { depth_m: 18.4 }, seabed: { label: "sand" } },
  depthOffshore: -3200,
  climatology: {
    kind: "climatology",
    source: "atlas",
    month: 6,
    point: { wind_atlas: { most_likely: { speed_knots: 16.2, dir_deg: 55 } } },
  },
  polar: { boat: "Leopard 46", speedKnots: 7.2, etaHours: 42 },
  marks: [{ kind: "leg", from: "La Rochelle", to: "Fort-de-France", vehicle: "main" }],
  sources: { zee: "error", bi: "ok" },
};

function briefingSentences(text) {
  return text.split(/\n\n+|(?<=\.)\s+/).map((s) => s.trim()).filter(Boolean);
}

describe("lot M — sources liées, pas de redite", () => {
  it("chaque source connue produit un lien", () => {
    const cited = KNOWN_SOURCES.join(" · ");
    const segs = segmentSources(cited);
    assert.equal(segs.map((s) => s.text).join(""), cited);
    for (const name of KNOWN_SOURCES) {
      const hit = segs.find((s) => s.text === name && s.entity);
      assert.ok(hit, `${name} doit produire un lien`);
      assert.equal(hit.entity.url, SOURCE_URLS[name]);
      assert.equal(hit.entity.kind, "source");
    }
    const live = narrateIciSegments(FULL_BAG, "fr");
    assert.equal(live.map((s) => s.text).join(""), narrateIci(FULL_BAG, "fr"));
    const linked = new Set(live.filter((s) => s.entity?.kind === "source").map((s) => s.text));
    for (const name of ["Open-Meteo", "NOAA/RTOFS", "EMODnet", "GEBCO", "Marine Regions/VLIZ", "OpenStreetMap", "douane.gouv.fr", "CDSE"]) {
      assert.ok(linked.has(name), `${name} cité dans le sac doit être un lien`);
    }
  });

  it("aucune phrase dupliquée dans un briefing complet ; polaire une fois, climatologie hors briefing", () => {
    const text = narrateIci(FULL_BAG, "fr");
    const sentences = briefingSentences(text);
    assert.equal(new Set(sentences).size, sentences.length, `doublon : ${sentences.join(" | ")}`);
    assert.equal((text.match(/Polaire chargée/g) || []).length, 1);
    assert.doesNotMatch(text, /Polaire chargée[\s\S]*Polaire chargée/);
    assert.equal(climatologyShownOnBanner(FULL_BAG), true);
    assert.doesNotMatch(text, /Climatologie de/);
    const silent = narrateIci({
      ...FULL_BAG,
      climatology: { source: "unavailable", month: 6 },
    }, "fr");
    assert.match(silent, /atlas de climatologie n’a pas répondu/);
    assert.equal((silent.match(/atlas de climatologie n’a pas répondu/g) || []).length, 1);
  });
});

