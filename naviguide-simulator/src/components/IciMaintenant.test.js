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
  journalChangeLabel,
  seekJournalEntry,
  visibleAlerts,
  visibleIciTabs,
  formatLegLine,
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
    assert.match(src, /visibleIciTabs\(mode\)/);
    assert.match(src, /tabs\.map\(\(tab\) =>/);
    assert.doesNotMatch(src, /ICI_TABS\.map/);
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

describe("useMoment — lot R8b / RC2", () => {
  it("interroge /ici/moment ; sans lat/lon ou API KO → moment null, pas la fixture", () => {
    assert.match(hook, /\/ici\/moment\?/);
    assert.match(hook, /moment: null/);
    assert.match(hook, /source: "none"/);
    assert.match(hook, /export const MOMENT_FIXTURE/);
    assert.doesNotMatch(hook, /moment: MOMENT_FIXTURE/);
    assert.doesNotMatch(hook, /source: "fixture"/);
    assert.match(hook, /controller\.abort\(\)/);
    const q = momentSearchParams({ lat: 37.7, lon: 236.84, t: "2026-05-15T08:00:00Z", mode: "follow", lang: "fr" });
    assert.equal(Number(Number(q.get("lon")).toFixed(2)), Number(wrapLon(236.84).toFixed(2)));
    assert.equal(q.get("t"), "2026-05-15T08:00:00Z");
  });
});

describe("IciMaintenant — lot RC2 : encadré honnête", () => {
  it("moment null : sections présentes, aucune ligne Antilles", () => {
    for (const id of [
      "ici-section-leg",
      "ici-section-alerts",
      "ici-section-here",
      "ici-section-around",
      "ici-section-sources",
    ]) {
      assert.match(src, new RegExp(`testId="${id}"`));
    }
    assert.equal(formatLegLine(null, tFr, "fr"), "");
    assert.equal(formatLegLine(undefined, tFr, "fr"), "");
    assert.equal(formatLegLine({}, tFr, "fr"), "");
    assert.deepEqual(visibleAlerts(null, new Set()), []);
    assert.doesNotMatch(src, /Fort-de-France|Pointe-à-Pitre|CORIOLIS-Guadeloupe/);
  });

  it("rend here.sentences et here.links même si hereBody est passé", () => {
    assert.match(src, /hereBody/);
    assert.match(src, /here\?\.sentences/);
    assert.match(src, /here\?\.links/);
    assert.match(src, /data-testid="ici-here-sentence"/);
    assert.match(src, /data-testid="ici-source-link"/);
    assert.doesNotMatch(src, /!hereBody \? \(shown\?\.here\?\.sentences/);
    const idxBody = src.indexOf("{hereBody}");
    const idxSent = src.indexOf("(here?.sentences || []).map");
    assert.ok(idxBody >= 0 && idxSent > idxBody, "sentences après hereBody, sans le masquer");
  });

  it("fermeture d'une pastille inchangée", () => {
    const alerts = fixture.alerts;
    const first = alerts[0].id;
    const second = alerts[1].id;
    const afterOne = dismissAlert(new Set(), first);
    const shown = visibleAlerts(alerts, afterOne);
    assert.equal(shown.some((a) => a.id === first), false);
    assert.equal(shown.some((a) => a.id === second), true);
    assert.equal(shown.length, alerts.length - 1);
  });
});

describe("IciMaintenant — lot RD6 : onglet Récit et journal nommé", () => {
  it("n'expose Récit qu'en Suivre", () => {
    assert.deepEqual(visibleIciTabs("follow").map((t) => t.id), ["now", "story", "journal"]);
    assert.deepEqual(visibleIciTabs("simulation").map((t) => t.id), ["now", "journal"]);
    assert.deepEqual(visibleIciTabs("drawn").map((t) => t.id), ["now", "journal"]);
    assert.match(src, /visibleIciTabs\(mode\)/);
    assert.doesNotMatch(src, /className="mt-1\.5 min-h-0 flex-1"/);
    assert.doesNotMatch(src, /placeholder|journalHint|récit vide|onglet vide/i);
  });

  it("nomme l'AMP, le cyclone et la marina d'après le fait, sans inventer", () => {
    const ampNamed = journalChangeLabel({
      changes: [{ kind: "amp", score: 1, title: "Iroise", fact: "Iroise (4 nm)" }],
    }, "fr");
    assert.equal(ampNamed, "Aire marine protégée — Iroise");
    const ampFromFact = journalChangeLabel({
      changes: [{ kind: "alert-on", score: 3, title: "Aire marine protégée", fact: "Iroise (4 nm): IUCN II." }],
    }, "fr");
    assert.equal(ampFromFact, "Aire marine protégée — Iroise");
    const ampTypeOnly = journalChangeLabel({
      changes: [{ kind: "amp", score: 1, title: "Aire marine protégée", fact: "" }],
    }, "fr");
    assert.equal(ampTypeOnly, "Aire marine protégée");
    const cyclone = journalChangeLabel({
      changes: [{ kind: "cyclone", score: 3, title: "Cyclone", fact: "Irma (2017)" }],
    }, "fr");
    assert.equal(cyclone, "Cyclone — Irma (2017)");
    const cycloneAnon = journalChangeLabel({
      changes: [{ kind: "cyclone", score: 3, title: "Cyclone", fact: "3 traces de cyclone ce mois-ci." }],
    }, "fr");
    assert.equal(cycloneAnon, "Cyclone");
    const marina = journalChangeLabel({
      changes: [{ kind: "marina", score: 1, title: "Marina Bas-du-Fort", fact: "Marina Bas-du-Fort (16 nm)" }],
    }, "fr");
    assert.equal(marina, "Marina — Marina Bas-du-Fort");
    const ports = journalChangeLabel({
      changes: [{ kind: "zee-enter", score: 2, title: "Ports d'entrée : Pointe-à-Pitre", fact: "Pointe-à-Pitre" }],
    }, "fr");
    assert.equal(ports, "Ports d'entrée : Pointe-à-Pitre");
    const line = formatJournalLine({
      t: "2026-05-16T10:00:00Z",
      pos: { lat: 48.2, lon: -4.8 },
      changes: [{ kind: "amp", score: 1, title: "Iroise", fact: "Iroise (4 nm)" }],
    }, "fr");
    assert.match(line, /Aire marine protégée — Iroise/);
    assert.doesNotMatch(line, /Iroise Iroise/);
  });
});
