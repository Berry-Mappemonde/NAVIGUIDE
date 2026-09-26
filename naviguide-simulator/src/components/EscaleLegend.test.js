import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "EscaleLegend.jsx"), "utf8");

describe("EscaleLegend — plus de carré vert (lot RD1)", () => {
  it("ne rend plus escale-sheet-open", () => {
    assert.doesNotMatch(src, /escale-sheet-open/);
    assert.doesNotMatch(src, /▤/);
    assert.doesNotMatch(src, /onSheet/);
    assert.match(src, /onSeek/);
    assert.match(src, /data-testid="escale-legend"/);
  });
});

describe("EscaleLegend — informatif en Suivre (lot RE2)", () => {
  it("sans onSeek, la ligne n'est pas un bouton et n'a pas de clic", () => {
    assert.match(src, /data-testid="escale-legend-row"/);
    assert.match(src, /data-interactive=\{interactive \? "true" : "false"\}/);
    assert.match(src, /typeof onSeek === "function"/);
    assert.match(src, /cursor-default/);
    assert.match(src, /cursor-pointer/);
    const branch = src.slice(src.indexOf("{interactive ? ("), src.indexOf("</li>"));
    assert.match(branch, /<button[\s\S]*onClick=\{\(\) => onSeek\(at/);
    const idle = branch.slice(branch.indexOf(") : ("));
    assert.match(idle, /<div className="flex-1 min-w-0 text-left px-2 py-1 text-\[11px\] cursor-default"/);
    assert.doesNotMatch(idle, /onClick/);
    assert.doesNotMatch(idle, /<button/);
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
