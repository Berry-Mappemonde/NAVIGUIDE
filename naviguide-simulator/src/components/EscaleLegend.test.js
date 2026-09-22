import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "EscaleLegend.jsx"), "utf8");

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
