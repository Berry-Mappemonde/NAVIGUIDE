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
  it("persists the character only, in this tab, and never awaits a model", () => {
    assert.match(hook, /readSavedOrders\(storage\(\)\)/);
    assert.match(hook, /writeSavedOrders\(storage\(\), \{ profile: next \}\)/);
    assert.match(hook, /clearSavedOrders\(storage\(\)\)/);
    assert.match(hook, /resolveOrders\(\{ profile \}, \{ polar, mode \}\)/);
    assert.match(hook, /NOTICE_MS = 6000/);
    assert.match(hook, /Never awaits a model/);
    assert.match(hook, /Never rewinds the film/);
    assert.doesNotMatch(hook, /fetch\(|await |Nemotron|Tavily|mongo/i);
  });

  it("proposes coastal for a small polar and lets the skipper refuse", () => {
    assert.match(hook, /acceptSuggest/);
    assert.match(hook, /dismissSuggest/);
    assert.match(hook, /never switches silently/);
  });
});

describe("SkipperOrdersPanel contract (v1)", () => {
  it("shows three pills and a boat read from the polar — no fields, no Comfort, no Expert", () => {
    assert.match(panel, /PROFILES\.map/);
    assert.match(panel, /aria-pressed=\{profile === p\}/);
    assert.match(panel, /skipperProfileAria/);
    assert.match(panel, /skipperSuivreWindow/);
    assert.match(panel, /skipperResetBerry/);
    assert.doesNotMatch(panel, /skipperSharedClock|exampleLine|skipperRainSimulation/);
    assert.doesNotMatch(panel, /<input/);
    assert.doesNotMatch(panel, /comfort|Souple|Expert|Chiffres/i);
    assert.doesNotMatch(panel, /wind-gale|hs-shift|depth-alert/);
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
    assert.doesNotMatch(app, /knots: expeditionSpeed\.knots,\n\s*\}\);\n\n\s*const iciPack/);
  });
});
