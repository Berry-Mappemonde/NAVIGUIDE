import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const sidebar = readFileSync(join(here, "Sidebar.jsx"), "utf8");
const ici = readFileSync(join(here, "IciMaintenant.jsx"), "utf8");
const chat = readFileSync(join(here, "LogbookChat.jsx"), "utf8");
const cards = readFileSync(join(here, "MomentCards.jsx"), "utf8");
const app = readFileSync(join(here, "..", "App.jsx"), "utf8");
const scene = readFileSync(join(here, "..", "map", "MapSceneController.js"), "utf8");
const css = readFileSync(join(here, "..", "index.css"), "utf8");

function firstIndex(src, pattern) {
  const m = src.match(pattern);
  assert.ok(m, `motif introuvable : ${pattern}`);
  return m.index;
}

describe("Sidebar layout (lot R8c)", () => {
  it("place carte Berry → chat → IciMaintenant, sans les anciens blocs", () => {
    const berryAt = firstIndex(sidebar, /<BerryCard/);
    const chatAt = firstIndex(sidebar, /<LogbookChat messages=\{chat\.messages\}/);
    const iciAt = firstIndex(sidebar, /<IciMaintenant/);
    const storyAt = firstIndex(sidebar, /data-testid="expedition-story"/);
    const journalAt = firstIndex(sidebar, /<JournalPanel /);
    assert.ok(berryAt < chatAt, "BerryCard avant LogbookChat");
    assert.ok(chatAt < iciAt, "LogbookChat avant IciMaintenant");
    assert.ok(iciAt < storyAt, "IciMaintenant reçoit le récit");
    assert.ok(storyAt < journalAt, "récit avant journal");
    assert.doesNotMatch(sidebar, /<MomentNowCard /);
    assert.doesNotMatch(sidebar, /<FreeMomentBlock /);
    assert.doesNotMatch(sidebar, /EscaleSheet/);
  });

  it("garde les surfaces par alias : étape, sac, récit, journal — fiche d'escale hors du sac", () => {
    assert.match(sidebar, /<SimulationPanel/);
    assert.match(sidebar, /<IciMaintenant/);
    assert.match(sidebar, /data-testid="here-product"/);
    assert.match(sidebar, /data-testid="briefing"/);
    assert.match(sidebar, /data-testid="ici-briefing"/);
    assert.match(sidebar, /data-testid="expedition-story"/);
    assert.match(sidebar, /<JournalPanel /);
    assert.doesNotMatch(sidebar, /EscaleSheet/);
    assert.match(ici, /<EscaleSheet/);
    assert.match(ici, /testId="ici-section-here"/);
  });

  it("fixe les hauteurs via --sim-box-h-* et les classes sim-box-*", () => {
    assert.match(css, /--sim-box-h-chat:\s*168px/);
    assert.match(css, /--sim-box-h-now:/);
    assert.match(css, /--sim-box-h-ici:/);
    assert.match(css, /--sim-box-h-story:/);
    assert.match(css, /\.light-mode \.sim-box-chat/);
    assert.match(css, /\.light-mode \.sim-box-ici/);
    assert.match(css, /\.light-mode \.sim-box-story/);
    assert.match(css, /\.light-mode \.ici-maintenant/);
    assert.match(chat, /sim-box-chat/);
    assert.match(cards, /sim-box-now/);
    assert.match(sidebar, /sim-box-ici/);
    assert.match(sidebar, /sim-box-story/);
  });

  it("réserve le sac ici à hauteur fixe avec le placeholder de remplissage", () => {
    assert.match(sidebar, /iciBriefingLoading/);
    assert.match(sidebar, /Le sac se remplit|iciBriefingLoading/);
    assert.match(sidebar, /\{!isDrawing \? \(/);
  });

  it("lot N1 — Importer à côté de Terminer, sans texte d'aide", () => {
    assert.match(sidebar, /data-testid="route-import"/);
    assert.match(sidebar, /data-testid="route-import-file"/);
    assert.match(sidebar, /accept="\.geojson,\.json,\.kml"/);
    assert.match(sidebar, /t\("importRoute"\)/);
    assert.doesNotMatch(sidebar, /t\("clickToImport"\)|t\("importOrDraw"\)|t\("clickNewImport"\)/);
  });

  it("lot RD2 — toggle gauche fermé à top-4, pas d'aplat blanc crédits/zoom", () => {
    assert.match(sidebar, /naviguide-sidebar-toggle--left[\s\S]{0,280}absolute top-4/);
    assert.doesNotMatch(sidebar, /top-\[92px\]/);
    assert.match(css, /\.leaflet-bottom\.leaflet-right \.leaflet-control-attribution \{[\s\S]{0,80}background:\s*rgba\(15,\s*23,\s*42,\s*0\.72\)/);
    assert.match(css, /\.leaflet-bottom\.leaflet-right \.leaflet-control-zoom\.leaflet-bar \{[\s\S]{0,180}background:\s*rgba\(15,\s*23,\s*42,\s*0\.72\)/);
    assert.doesNotMatch(css, /\.light-mode \.leaflet-container \.leaflet-control-attribution/);
    assert.doesNotMatch(css, /\.light-mode \.leaflet-container \.leaflet-control-zoom/);
    assert.doesNotMatch(css, /leaflet-control-attribution[\s\S]{0,220}rgba\(255,\s*255,\s*255/);
    assert.doesNotMatch(css, /leaflet-control-zoom\.leaflet-bar[\s\S]{0,220}rgba\(255,\s*255,\s*255/);
  });
});

describe("contrat pop-up hors film (lot R8c)", () => {
  it("ne rend plus les cartes flottantes ni la popup d'escale sur la carte", () => {
    assert.doesNotMatch(app, /<MomentNowCard/);
    assert.doesNotMatch(app, /<FreeMomentBlock/);
    assert.match(app, /<EscalePopupHost/);
    assert.match(app, /stop=\{replay\.active \? null : escaleStop\}/);
    assert.match(app, /useMoment\(/);
    assert.match(app, /mode: drawingMode \? "drawn"/);
    assert.match(scene, /escalePopup\.setSheet = \(\) => \{\}/);
    assert.match(scene, /escalePopup\.sync = \(\) => \{\}/);
    assert.doesNotMatch(ici, /ListenButton/);
    assert.doesNotMatch(ici, /moment-free-listen/);
    assert.match(ici, /testId="moment-now"/);
    assert.match(ici, /testId="moment-free"/);
  });
});
