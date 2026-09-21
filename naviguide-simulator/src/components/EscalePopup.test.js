import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  ESCALE_POPUP_MAX_HEIGHT,
  ESCALE_POPUP_MAX_WIDTH,
  createEscalePopupOptions,
  ensureEscalePopup,
  findWaypointMarker,
  handleWaypointMarkerClick,
} from "./escalePopup.js";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "EscalePopup.jsx"), "utf8");
const sheet = readFileSync(join(here, "EscaleSheet.jsx"), "utf8");
const sceneSrc = readFileSync(join(here, "..", "map", "MapSceneController.js"), "utf8");
const sidebar = readFileSync(join(here, "Sidebar.jsx"), "utf8");
const app = readFileSync(join(here, "..", "App.jsx"), "utf8");

function fakePopup() {
  return {
    ll: null,
    content: null,
    setLatLng(v) {
      this.ll = Array.isArray(v) ? { lat: v[0], lng: v[1] } : v;
      return this;
    },
    getLatLng() { return this.ll; },
    setContent(c) { this.content = c; return this; },
    openOn() { return this; },
    remove() { return this; },
  };
}

function fakeMarker(lat, lng, stop) {
  return {
    ll: { lat, lng },
    _naviguideWaypoint: stop,
    getLatLng() { return this.ll; },
  };
}

describe("EscalePopup — contrat (lot R7)", () => {
  it("contenu = EscaleSheet, croix, pas de ListenButton, ≤ 340 × 260", () => {
    assert.match(src, /data-testid="escale-popup"/);
    assert.match(src, /<EscaleSheet/);
    assert.match(src, /onClose/);
    assert.match(sheet, /data-testid="escale-close"/);
    assert.match(sheet, /×|<X /);
    assert.doesNotMatch(src, /ListenButton/);
    assert.doesNotMatch(sheet, /ListenButton/);
    assert.equal(ESCALE_POPUP_MAX_WIDTH, 340);
    assert.equal(ESCALE_POPUP_MAX_HEIGHT, 260);
    assert.match(src, /ESCALE_POPUP_MAX_WIDTH/);
    assert.match(src, /ESCALE_POPUP_MAX_HEIGHT/);
    assert.match(src, /overflowY:\s*"auto"/);
  });

  it("L.popup ancré au drapeau : pas de croix Leaflet, 340 px, Échap", () => {
    const opts = createEscalePopupOptions();
    assert.equal(opts.autoPan, true);
    assert.equal(opts.closeButton, false);
    assert.equal(opts.className, "escale-popup");
    assert.equal(opts.maxWidth, 340);
    assert.equal(opts.closeOnClick, false);
    const created = [];
    const L = {
      popup(o) {
        const p = { ...fakePopup(), opts: o };
        created.push(p);
        return p;
      },
    };
    const first = ensureEscalePopup(null, L);
    assert.equal(ensureEscalePopup(first, L), first);
    assert.equal(created.length, 1);
    assert.match(src, /attachEscalePopup/);
    assert.match(src, /keydown/);
    assert.match(src, /Escape/);
    assert.match(sceneSrc, /this\.escalePopup = attachEscalePopup\(this, L\)/);
    assert.match(sceneSrc, /this\.escalePopup\?\.sync\(\)/);
  });

  it("trouve le drapeau de l'escale ouverte (copie la plus proche)", () => {
    const ajaccio = { name: "Ajaccio (Corse)", lat: 41.9192, lon: 8.7386 };
    const scene = {
      map: { getCenter: () => ({ lng: 8.7 }) },
      waypointMarkers: new Map([
        ["route:2:0", fakeMarker(41.9192, 8.7386, ajaccio)],
        ["route:2:1", fakeMarker(41.9192, 8.7386 + 360, ajaccio)],
        ["route:0:0", fakeMarker(46.15, -1.15, { name: "La Rochelle", lat: 46.15, lon: -1.15 })],
      ]),
    };
    const found = findWaypointMarker(scene, ajaccio);
    assert.equal(found.getLatLng().lng, 8.7386);
    assert.equal(findWaypointMarker(scene, { name: "Nouméa", lat: -22, lon: 166 }), null);
  });

  it("App relie le clic drapeau et la légende au même état ; plus dans le panneau", () => {
    assert.match(app, /onWaypointClick=\{openEscaleSheet\}/);
    assert.match(app, /onEscaleSheet=\{openEscaleSheet\}/);
    assert.match(app, /<EscalePopupHost/);
    assert.doesNotMatch(sidebar, /EscaleSheet/);
    assert.doesNotMatch(app, /escaleStop=\{escaleStop\}/);
    const point = { name: "Ajaccio (Corse)", lat: 41.9, lon: 8.7 };
    const calls = { sheet: 0, draw: 0 };
    handleWaypointMarkerClick(false, point, 0, {
      onWaypointClick: () => { calls.sheet += 1; },
      onDrawingWaypointClick: () => { calls.draw += 1; },
    });
    assert.equal(calls.sheet, 1);
    assert.equal(calls.draw, 0);
  });
});
