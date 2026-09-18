import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const hook = readFileSync(join(here, "useSkipperOrders.js"), "utf8");
const panel = readFileSync(join(here, "..", "components", "SkipperOrdersPanel.jsx"), "utf8");
const tools = readFileSync(join(here, "..", "components", "ToolsSidebar.jsx"), "utf8");
const app = readFileSync(join(here, "..", "App.jsx"), "utf8");

describe("useSkipperOrders contract", () => {
  it("persists the orders in this tab (same v1 key), sanitized, and never awaits a model", () => {
    assert.match(hook, /readSavedOrders\(storage\(\)\)/);
    assert.match(hook, /writeSavedOrders\(storage\(\), next\)/);
    assert.match(hook, /sanitizeSaved\(\{ \.\.\.prev, \.\.\.patch \}\)/);
    assert.match(hook, /clearSavedOrders\(storage\(\)\)/);
    assert.match(hook, /resolveOrders\(saved, \{ polar, mode \}\)/);
    assert.match(hook, /NOTICE_MS = 6000/);
    assert.match(hook, /Never awaits a model/);
    assert.match(hook, /Never rewinds the film/);
    assert.doesNotMatch(hook, /fetch\(|await |Nemotron|Tavily|mongo/i);
  });

  it("exposes S6 / S7 setters and shows the cyan line on profile / comfort / horizon, not per Expert keystroke", () => {
    assert.match(hook, /setComfort/);
    assert.match(hook, /setHorizon/);
    assert.match(hook, /setExpert = useCallback\(\(id, value\)/);
    assert.match(hook, /clampExpert\(id, value\)/);
    assert.match(hook, /function noticeKey\(saved\)/);
    assert.match(hook, /\$\{saved\.profile\}\|\$\{saved\.comfort \|\| "normal"\}\|\$\{saved\.horizonH \|\| ""\}/);
  });

  it("proposes coastal for a small polar and lets the skipper refuse", () => {
    assert.match(hook, /acceptSuggest/);
    assert.match(hook, /dismissSuggest/);
    assert.match(hook, /never switches silently/);
  });
});

describe("SkipperOrdersPanel contract (v1 + S6 + S7)", () => {
  it("shows three pills and a boat read from the polar — no L / draft fields", () => {
    assert.match(panel, /items=\{PROFILES\}/);
    assert.match(panel, /aria-pressed=\{value === it\}/);
    assert.match(panel, /skipperProfileAria/);
    assert.match(panel, /skipperSuivreWindow/);
    assert.match(panel, /skipperResetBerry/);
    assert.doesNotMatch(panel, /skipperSharedClock|exampleLine|skipperRainSimulation/);
    const boatBlock = panel.slice(panel.indexOf('t("skipperBoat")'), panel.indexOf('data-testid="skipper-comfort"'));
    assert.ok(boatBlock.length > 0);
    assert.doesNotMatch(boatBlock, /<input/); // the boat block has no input
    assert.doesNotMatch(panel, /wind-gale|hs-shift|depth-alert/);
  });

  it("S6: comfort pills with the live effect, horizon pills greyed in Simulation", () => {
    assert.match(panel, /items=\{COMFORTS\}/);
    assert.match(panel, /data-testid="skipper-comfort-effect"/);
    assert.match(panel, /skipperComfortAria/);
    assert.match(panel, /items=\{HORIZONS_H\}/);
    assert.match(panel, /disabled=\{!isSuivre\}/);
    assert.match(panel, /skipperHorizonLeg/);
  });

  it("S7: a folded Expert drawer, inputs only there, gale read-only", () => {
    const drawer = panel.slice(panel.indexOf("<details"), panel.indexOf("</details>"));
    assert.ok(drawer.length > 0, "details drawer exists");
    assert.match(drawer, /skipperExpertTitle/);
    assert.match(drawer, /EXPERT_IDS\.map/);
    assert.match(drawer, /type="number"/);
    assert.match(drawer, /min=\{f\.min\}[^]*max=\{f\.max\}[^]*step=\{f\.step\}/);
    assert.match(drawer, /onExpert\?\.\(id, null\)/);
    assert.match(drawer, /skipperExpertLocked/);
    const outside = panel.replace(drawer, "");
    assert.doesNotMatch(outside, /<input/);
    assert.doesNotMatch(panel, /<details open/);
  });

  it("is mounted in the tools sidebar under the polar, not on the film bar", () => {
    assert.match(tools, /<SkipperOrdersPanel/);
    const polarTable = tools.indexOf("POLAR_VMG_TWS_KEYS.map");
    const panelAt = tools.indexOf("<SkipperOrdersPanel");
    assert.ok(polarTable > 0 && panelAt > polarTable, "panel sits after the polar block");
    const filmBar = readFileSync(join(here, "..", "components", "SimulationFilmBar.jsx"), "utf8");
    assert.doesNotMatch(filmBar, /SkipperOrders|skipperProfile/);
  });

  it("App passes the same orders to detectors, judge and lookahead, and the cyan notice to the briefing", () => {
    assert.match(app, /useSkipperOrders\(\{/);
    assert.equal((app.match(/orders: skipper\.orders/g) || []).length, 2);
    assert.match(app, /skipperNotice=\{skipper\.notice\}/);
    assert.match(app, /skipperOrders=\{skipper\.orders\}/);
    assert.match(app, /onSkipperComfort=\{skipper\.setComfort\}/);
    assert.match(app, /onSkipperHorizon=\{skipper\.setHorizon\}/);
    assert.match(app, /onSkipperExpert=\{skipper\.setExpert\}/);
    assert.match(tools, /onComfort=\{onSkipperComfort\}/);
    assert.match(tools, /onExpert=\{onSkipperExpert\}/);
    const dossier = readFileSync(join(here, "useIciDossier.js"), "utf8");
    assert.match(dossier, /q\.set\("radius_nm", String\(radiusRef\.current\)\)/);
    assert.match(dossier, /radiusRef\.current = /);
    assert.doesNotMatch(app, /knots: expeditionSpeed\.knots,\n\s*\}\);\n\n\s*const iciPack/);
  });
});
