import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "EscaleLegend.jsx"), "utf8");
const tools = readFileSync(join(here, "ToolsSidebar.jsx"), "utf8");

describe("EscaleLegend — plus de carré vert (lot RD1)", () => {
  it("ne rend plus escale-sheet-open", () => {
    assert.doesNotMatch(src, /escale-sheet-open/);
    assert.doesNotMatch(src, /▤/);
    assert.doesNotMatch(src, /onSheet/);
    assert.match(src, /data-testid="escale-legend"/);
  });
});

describe("EscaleLegend — informative dans tous les modes (lot RF8, étend RE2)", () => {
  it("n'a plus de gestionnaire de clic, aucun mode", () => {
    assert.match(src, /data-testid="escale-legend-row"/);
    assert.match(src, /data-interactive="false"/);
    assert.doesNotMatch(src, /typeof onSeek === "function"/);
    assert.doesNotMatch(src, /onSeek=/);
    assert.doesNotMatch(src, /onClick/);
    assert.doesNotMatch(src, /<button/);
    assert.doesNotMatch(src, /cursor-pointer/);
    assert.match(src, /<div className="flex-1 min-w-0 text-left px-2 py-1 text-\[11px\] cursor-default"/);
    assert.match(src, /nmLabel/);
    assert.match(src, /dateLabel/);
    assert.match(src, /quayLabel/);
    assert.match(src, /etaLabel/);
    assert.doesNotMatch(tools, /onSeek=\{onSeekEscale\}/);
  });
});

describe("EscaleLegend — fourchette sous la date (lot C6)", () => {
  it("ajoute eta-range sans retirer la date", () => {
    assert.match(src, /data-testid="escale-legend"/);
    assert.match(src, /data-testid="eta-range"/);
    assert.match(src, /formatCivilDate/);
    assert.match(src, /dateLabel/);
    assert.match(src, /formatEtaRange/);
    assert.match(src, /formatEtaRangeTitle/);
    assert.match(src, /useOfficialEta/);
    assert.match(src, /nextStopFromMarks/);
    assert.match(src, /stopMatch/);
    assert.match(src, /nextIndex/);
    assert.match(src, /title=\{etaTitle/);
  });
});

describe("EscaleLegend — ETA gelée pendant le film (lot RF4)", () => {
  it("passe frozen à useOfficialEta", () => {
    assert.match(src, /frozen = false/);
    assert.match(src, /useOfficialEta\(nextName, \{ enabled: Boolean\(nextName\), frozen \}\)/);
  });
});
