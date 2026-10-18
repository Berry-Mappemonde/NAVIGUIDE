import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it } from "node:test";
import { tileAttribution } from "./styles.js";
import { SCIENCE_WMS_LAYERS } from "./scienceWms.js";
import {
  EMODNET_ACTIVITIES_ATTRIBUTION,
  EMODNET_BATHYMETRY_ATTRIBUTION,
  EMODNET_GEOLOGY_ATTRIBUTION,
  OPENSEAMAP_ATTRIBUTION,
  OSM_COPYRIGHT_HREF,
  VLIZ_EEZ_ATTRIBUTION,
  bindTileCredit,
  creditsForLayers,
} from "./tileAttributions.js";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "../index.css"), "utf8");
const toggleSrc = readFileSync(join(here, "useToggleLayers.js"), "utf8");

function fakeMap() {
  const counts = new Map();
  return {
    counts,
    attributionControl: {
      addAttribution(text) {
        counts.set(text, (counts.get(text) || 0) + 1);
      },
      removeAttribution(text) {
        counts.set(text, (counts.get(text) || 0) - 1);
      },
    },
  };
}

describe("crédits tuiles / WMS", () => {
  it("crédite OpenStreetMap sur le fond, avec le lien copyright", () => {
    const html = tileAttribution("fr");
    assert.match(html, /OpenStreetMap contributors/);
    assert.match(html, new RegExp(`href="${OSM_COPYRIGHT_HREF.replace(/\//g, "\\/")}"`));
    assert.match(tileAttribution("en"), /OpenStreetMap contributors/);
  });

  it("affiche le crédit d'une couche tant qu'elle est active, et le retire ensuite", () => {
    assert.deepEqual(creditsForLayers({}), []);
    assert.deepEqual(creditsForLayers({ balisage: true }), [OPENSEAMAP_ATTRIBUTION]);
    assert.equal(OPENSEAMAP_ATTRIBUTION, "© OpenSeaMap contributors");
    assert.deepEqual(creditsForLayers({ bathymetry: true }), [EMODNET_BATHYMETRY_ATTRIBUTION]);
    assert.deepEqual(
      creditsForLayers({ balisage: true, bathymetry: true, fonds: true, cables: true, zee: true }),
      [
        OPENSEAMAP_ATTRIBUTION,
        EMODNET_BATHYMETRY_ATTRIBUTION,
        EMODNET_GEOLOGY_ATTRIBUTION,
        EMODNET_ACTIVITIES_ATTRIBUTION,
        VLIZ_EEZ_ATTRIBUTION,
      ],
    );
    assert.deepEqual(creditsForLayers({ balisage: false, zee: true }), [VLIZ_EEZ_ATTRIBUTION]);
  });

  it("la bathymétrie affichée est le WMS EMODnet, pas le sondage GEBCO", () => {
    const bathy = SCIENCE_WMS_LAYERS.find((spec) => spec.id === "bathymetry");
    assert.equal(bathy.url, "https://ows.emodnet-bathymetry.eu/wms");
    assert.equal(bathy.layers, "mean_multicolour");
    assert.equal(bathy.attribution, EMODNET_BATHYMETRY_ATTRIBUTION);
    assert.match(bathy.attribution, /EMODnet Bathymetry Consortium/);
    assert.match(bathy.attribution, /CC-BY 4\.0/);
    assert.doesNotMatch(bathy.attribution, /GEBCO/);
    const substrate = SCIENCE_WMS_LAYERS.find((spec) => spec.id === "substrate");
    const cables = SCIENCE_WMS_LAYERS.find((spec) => spec.id === "cables");
    assert.equal(substrate.attribution, EMODNET_GEOLOGY_ATTRIBUTION);
    assert.equal(cables.attribution, EMODNET_ACTIVITIES_ATTRIBUTION);
    assert.match(VLIZ_EEZ_ATTRIBUTION, /Flanders Marine Institute \(VLIZ\)/);
    assert.match(VLIZ_EEZ_ATTRIBUTION, /https:\/\/www\.marineregions\.org\//);
  });

  it("pose le crédit sur le contrôle et le retire une seule fois", () => {
    const map = fakeMap();
    const release = bindTileCredit(map, OPENSEAMAP_ATTRIBUTION);
    assert.equal(map.counts.get(OPENSEAMAP_ATTRIBUTION), 1);
    release();
    release();
    assert.equal(map.counts.get(OPENSEAMAP_ATTRIBUTION), 0);
    assert.equal(typeof bindTileCredit(null, OPENSEAMAP_ATTRIBUTION), "function");
  });

  it("branche le contrôle sur OpenSeaMap, la ZEE et les WMS, pas sur l'option de couche", () => {
    assert.match(toggleSrc, /bindTileCredit\(map, OPENSEAMAP_ATTRIBUTION\)/);
    assert.match(toggleSrc, /bindTileCredit\(map, VLIZ_EEZ_ATTRIBUTION\)/);
    assert.match(toggleSrc, /bindTileCredit\(map, spec\.attribution\)/);
    assert.doesNotMatch(toggleSrc, /attribution:\s*"© OpenSeaMap contributors"/);
    assert.doesNotMatch(toggleSrc, /attribution:\s*spec\.attribution/);
  });

  it("laisse les crédits se replier dans la carte visible, sans recouvrir le zoom", () => {
    const rule = css.match(/\.leaflet-container \.leaflet-bottom\.leaflet-right \.leaflet-control-attribution \{[^}]+\}/);
    assert.ok(rule, "règle d'attribution introuvable");
    assert.match(rule[0], /min-height:\s*var\(--map-control-h\)/);
    assert.match(rule[0], /flex-wrap:\s*wrap/);
    assert.match(rule[0], /max-width:\s*calc\(100% - \(var\(--map-control-h\) \* 2\) - 8px\)/);
    assert.match(rule[0], /white-space:\s*normal/);
    assert.match(rule[0], /overflow-wrap:\s*break-word/);
    assert.doesNotMatch(rule[0], /overflow-wrap:\s*anywhere/);
    assert.match(rule[0], /min-width:\s*min\(220px, 100vw - 16px\)/);
    assert.match(rule[0], /height:\s*auto/);
    assert.doesNotMatch(rule[0], /white-space:\s*nowrap/);
    assert.match(css, /\.leaflet-container \.leaflet-bottom\.leaflet-right \{[^}]*left:\s*var\(--sim-inset-left/);
  });
});
