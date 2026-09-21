import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { formatEtaRange, nextStopFromMarks } from "./usePlanReview.js";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "usePlanReview.js"), "utf8");

describe("usePlanReview — fourchette ETA (lot C6)", () => {
  it("ne fabrique pas de fourchette sans membres ou sans dates", () => {
    const t = (_k, v) => `entre le ${v.p10} et le ${v.p90} (p10–p90, ${v.n} membres)`;
    assert.equal(formatEtaRange(null, t, "fr"), "");
    assert.equal(formatEtaRange({ members: 0, p10: "2026-10-11T00:00:00Z", p90: "2026-10-14T00:00:00Z" }, t, "fr"), "");
    assert.equal(formatEtaRange({ members: 80, p10: null, p90: null }, t, "fr"), "");
  });

  it("écrit le libellé p10–p90 à partir des ISO (même mois : jour seul)", () => {
    const t = (_k, v) => `entre le ${v.p10} et le ${v.p90} (p10–p90, ${v.n} membres)`;
    const eta = { members: 80, p10: "2026-10-11T08:00:00Z", p90: "2026-10-14T18:00:00Z" };
    assert.equal(formatEtaRange(eta, t, "fr"), "entre le 11 et le 14 (p10–p90, 80 membres)");
    assert.match(formatEtaRange(eta, t, "fr"), /p10/);
  });

  it("prend la prochaine escale dont l'iso est dans le futur", () => {
    const now = Date.parse("2026-09-20T12:00:00Z");
    const name = nextStopFromMarks([
      { name: "Nouméa", iso: "2026-09-01T00:00:00Z" },
      { name: "Dzaoudzi", iso: "2026-10-12T00:00:00Z" },
    ], now);
    assert.equal(name, "Dzaoudzi");
    assert.equal(nextStopFromMarks([], now), "");
  });

  it("appelle GET /voyage/official/eta et n'invente rien si members=0", () => {
    assert.match(src, /\/voyage\/official\/eta\?stop=/);
    assert.match(src, /Number\(body\.members\) > 0/);
    assert.match(src, /etaRange: eta/);
  });
});
