import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import fixture from "../fixtures/moment.json" with { type: "json" };
import { momentSearchParams } from "../hooks/useMoment.js";
import { wrapLon } from "../utils/geo.js";
import { sortJournalEntries } from "../hooks/useMomentJournal.js";
import {
  dismissAlert,
  formatJournalLine,
  formatLegLine,
  seekJournalEntry,
  visibleAlerts,
} from "./iciMaintenant.js";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "IciMaintenant.jsx"), "utf8");
const helpers = readFileSync(join(here, "iciMaintenant.js"), "utf8");
const hook = readFileSync(join(here, "..", "hooks", "useMoment.js"), "utf8");

const tFr = (key, vars = {}) => {
  const table = {
    iciLegDay: "J{n}",
    iciLegKn: "{kn} kn",
    iciLegRemaining: "reste {nm} nm",
    etaRange: "arrivée entre le {p10} et le {p90}",
  };
  return Object.entries(vars).reduce((s, [k, v]) => s.replace(`{${k}}`, v), table[key] || key);
};

describe("IciMaintenant — lot R8b : cinq sections, pas de titre", () => {
  it("rend les cinq sections et le sélecteur à trois onglets, sans bandeau", () => {
    assert.match(src, /data-testid="ici-maintenant"/);
    assert.match(src, /data-testid="ici-tabs"/);
    assert.match(src, /data-testid=\{testId\}/);
    assert.match(src, /data-testid=\{tab\.testId\}/);
    for (const id of [
      "ici-section-leg",
      "ici-section-alerts",
      "ici-section-here",
      "ici-section-around",
      "ici-section-sources",
    ]) {
      assert.match(src, new RegExp(`testId="${id}"`));
    }
    assert.match(helpers, /ici-tab-now/);
    assert.match(helpers, /ici-tab-story/);
    assert.match(helpers, /ici-tab-journal/);
    assert.match(helpers, /iciNowTab/);
    assert.match(helpers, /iciStoryTab/);
    assert.match(helpers, /iciJournalTab/);
    assert.match(src, /iciSectionLeg/);
    assert.match(src, /iciSectionAlerts/);
    assert.match(src, /iciSectionHere/);
    assert.match(src, /iciSectionAround/);
    assert.match(src, /iciSectionSources/);
    assert.doesNotMatch(src, /Ici et maintenant|Here and now|iciNowTitle|ici-title|ici-banner/);
    assert.doesNotMatch(src, /<h[1-6]\b/);
    assert.doesNotMatch(src, /momentNowTitle|storyHint|journalHint/);
  });

  it("ferme une pastille sans en ouvrir une autre", () => {
    const alerts = fixture.alerts;
    assert.ok(alerts.length >= 2, "la fixture porte au moins deux alertes");
    const first = alerts[0].id;
    const second = alerts[1].id;
    const afterOne = dismissAlert(new Set(), first);
    const shown = visibleAlerts(alerts, afterOne);
    assert.equal(shown.some((a) => a.id === first), false);
    assert.equal(shown.some((a) => a.id === second), true);
    assert.equal(shown.length, alerts.length - 1);
    const afterTwo = dismissAlert(afterOne, second);
    const left = visibleAlerts(alerts, afterTwo);
    assert.equal(left.some((a) => a.id === second), false);
    assert.equal(left.length, alerts.length - 2);
  });

  it("conserve les liens de sources et les emplacements vides Récit / Journal", () => {
    assert.match(src, /data-testid="ici-source-link"/);
    assert.match(src, /here\?\.links/);
    assert.match(src, /target="_blank"/);
    assert.match(src, /rel="noopener noreferrer"/);
    assert.match(src, /data-testid="ici-story-slot"/);
    assert.match(src, /data-testid="ici-journal-slot"/);
    assert.match(src, /flex-1 min-h-0 overflow-auto/);
    assert.doesNotMatch(src, /Bientôt|placeholder|aide|hint|TODO/i);
  });

  it("formate la ligne d'étape avec les chiffres du Moment, sans en inventer", () => {
    const line = formatLegLine(fixture.leg, tFr, "fr");
    assert.match(line, /Fort-de-France/);
    assert.match(line, /Pointe-à-Pitre/);
    assert.match(line, /J21/);
    assert.match(line, /8,0 kn/);
    assert.match(line, /reste 80 nm/);
    assert.match(line, /arrivée entre le/);
  });
});

describe("IciMaintenant — lot R8c : récit / journal / escale, pas d'Écouter", () => {
  it("reçoit les vues Récit et Journal et ouvre l'escale dans Ici", () => {
    assert.match(src, /data-testid="ici-story-slot"/);
    assert.match(src, /data-testid="ici-journal-slot"/);
    assert.match(src, /<EscaleSheet/);
    assert.match(src, /escale\?\.stop/);
    assert.match(src, /testId="moment-now"/);
    assert.match(src, /testId="moment-free"/);
    assert.doesNotMatch(src, /ListenButton/);
    assert.doesNotMatch(src, /moment-free-listen/);
    assert.doesNotMatch(src, /momentNowTitle|momentFreeTitle/);
  });
});

describe("IciMaintenant — lot R9b : journal chronologique, clic → onSeek(t)", () => {
  const entries = [
    { t: "2026-06-23T08:00:00Z", pos: { lat: 14.6, lon: -61.0 }, signature: "c", seq: 2, changes: [{ title: "Fort-de-France" }] },
    { t: "2026-05-15T08:00:00Z", pos: { lat: 48.86, lon: 2.35 }, signature: "a", seq: 0, changes: [] },
    { t: "2026-06-02T08:00:00Z", pos: { lat: 32.1, lon: -16.9 }, signature: "b", seq: 1, changes: [{ title: "ZEE du Maroc" }] },
  ];

  it("rend N entrées dans l'ordre chronologique", () => {
    const lines = sortJournalEntries(entries).map((entry) => formatJournalLine(entry, "fr"));
    assert.equal(lines.length, 3);
    assert.match(lines[0], /15 mai/);
    assert.match(lines[1], /2 juin/);
    assert.match(lines[2], /23 juin/);
    assert.match(lines[0], /48,9/);
    assert.match(lines[1], /ZEE du Maroc/);
    assert.match(src, /data-testid="ici-journal-entry"/);
    assert.match(src, /data-testid="ici-journal-list"/);
    assert.match(src, /sortJournalEntries\(entries\)/);
    assert.match(src, /formatJournalLine\(entry, lang\)/);
    assert.doesNotMatch(src, /journalHint|Le journal commence|cliquez|aide/i);
  });

  it("clic appelle onSeek(t)", () => {
    const seen = [];
    seekJournalEntry((t) => seen.push(t), entries[2]);
    assert.deepEqual(seen, ["2026-06-02T08:00:00Z"]);
    seekJournalEntry((t) => seen.push(t), { t: "2026-05-15T08:00:00Z" });
    assert.deepEqual(seen, ["2026-06-02T08:00:00Z", "2026-05-15T08:00:00Z"]);
    assert.match(src, /seekJournalEntry\(onSeek, entry\)/);
    assert.match(src, /momentAtOrBefore\(journalEntries, moment\?\.t\)/);
  });
});

describe("useMoment — lot R8b", () => {
  it("interroge /ici/moment et se replie sur la fixture", () => {
    assert.match(hook, /\/ici\/moment\?/);
    assert.match(hook, /source: "fixture"/);
    assert.match(hook, /MOMENT_FIXTURE/);
    assert.match(hook, /controller\.abort\(\)/);
    const q = momentSearchParams({ lat: 37.7, lon: 236.84, t: "2026-05-15T08:00:00Z", mode: "follow", lang: "fr" });
    assert.equal(Number(Number(q.get("lon")).toFixed(2)), Number(wrapLon(236.84).toFixed(2)));
    assert.equal(q.get("t"), "2026-05-15T08:00:00Z");
  });
});
