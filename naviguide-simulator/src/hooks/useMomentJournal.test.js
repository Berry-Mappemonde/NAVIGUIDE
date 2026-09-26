import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import fixture from "../fixtures/moment.json" with { type: "json" };
import { ETA_RETRY_MS, nextEtaRetryMs } from "./usePlanReview.js";
import {
  MOMENT_JOURNAL_CAP,
  appendLocalMoment,
  localChanges,
  momentAtOrBefore,
  momentJournalStorageKey,
  parseOfficialMoments,
  pollOfficialMoments,
  readLocalJournal,
  sortJournalEntries,
  writeLocalJournal,
} from "./useMomentJournal.js";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "useMomentJournal.js"), "utf8");

function fakeStorage() {
  const m = new Map();
  return {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
    removeItem: (k) => m.delete(k),
  };
}

function momentAt(i) {
  return {
    t: new Date(Date.parse("2026-05-15T08:00:00Z") + i * 3600000).toISOString(),
    pos: { lat: 48 + i / 100, lon: -1 - i / 100 },
    signature: `sig-${i}`,
    here: { zee: { name: i % 3 === 0 ? `ZEE ${i}` : "ZEE A" } },
    leg: { to: i % 7 === 0 ? `Port ${i}` : "La Rochelle", regime: "climatology" },
    alerts: [],
    around: [],
  };
}

describe("useMomentJournal — lot R9b : repli localStorage, plafond 2 000", () => {
  it("écrit et relit le journal local sous la clé de la route", () => {
    const st = fakeStorage();
    const routeId = "simulation:official";
    const rows = appendLocalMoment([], fixture);
    const written = writeLocalJournal(routeId, rows, st);
    assert.equal(written.length, 1);
    assert.equal(written[0].signature, fixture.signature);
    assert.equal(st.getItem(momentJournalStorageKey(routeId)).includes(fixture.signature), true);
    const read = readLocalJournal(routeId, st);
    assert.equal(read.length, 1);
    assert.equal(read[0].t, fixture.t);
    assert.equal(readLocalJournal("simulation:other", st).length, 0);
  });

  it("plafonne à 2 000 et refuse un doublon de signature", () => {
    let rows = [];
    for (let i = 0; i < MOMENT_JOURNAL_CAP + 5; i += 1) {
      rows = appendLocalMoment(rows, momentAt(i));
    }
    assert.equal(rows.length, MOMENT_JOURNAL_CAP);
    assert.equal(rows[0].signature, "sig-5");
    assert.equal(rows[rows.length - 1].signature, `sig-${MOMENT_JOURNAL_CAP + 4}`);
    const same = appendLocalMoment(rows, momentAt(MOMENT_JOURNAL_CAP + 4));
    assert.equal(same, rows);
    const st = fakeStorage();
    const written = writeLocalJournal("simulation:official", rows, st);
    assert.equal(written.length, MOMENT_JOURNAL_CAP);
    assert.equal(readLocalJournal("simulation:official", st).length, MOMENT_JOURNAL_CAP);
  });

  it("trie chronologiquement et prend le moment ≤ t", () => {
    const late = { t: "2026-06-23T08:00:00Z", signature: "c", seq: 2, moment: { t: "2026-06-23T08:00:00Z", signature: "c" } };
    const early = { t: "2026-05-15T08:00:00Z", signature: "a", seq: 0, moment: { t: "2026-05-15T08:00:00Z", signature: "a" } };
    const mid = { t: "2026-06-02T08:00:00Z", signature: "b", seq: 1, moment: { t: "2026-06-02T08:00:00Z", signature: "b" } };
    const ordered = sortJournalEntries([late, early, mid]);
    assert.deepEqual(ordered.map((e) => e.t), [early.t, mid.t, late.t]);
    assert.equal(momentAtOrBefore(ordered, "2026-06-10T00:00:00Z").signature, "b");
    assert.equal(momentAtOrBefore(ordered, "2026-05-15T08:00:00Z").signature, "a");
    assert.equal(momentAtOrBefore(ordered, "2026-05-01T00:00:00Z"), null);
  });

  it("lit le payload officiel { moments } et ignore un corps invalide", () => {
    const body = parseOfficialMoments({
      voyageId: "official",
      count: 2,
      moments: [
        { t: "2026-06-02T08:00:00Z", signature: "b", pos: { lat: 32.1, lon: -16.9 } },
        { t: "2026-05-15T08:00:00Z", signature: "a", pos: { lat: 48.8, lon: 2.3 } },
        { t: "x", signature: "" },
      ],
    });
    assert.equal(body.length, 2);
    assert.equal(body[0].signature, "a");
    assert.equal(parseOfficialMoments({}).length, 0);
  });
});

describe("useMomentJournal — lot RC9 : re-demande /moments tant que vide", () => {
  it("relance après un premier [] puis remplit les lignes", async () => {
    assert.match(src, /pollOfficialMoments/);
    assert.match(src, /nextEtaRetryMs/);
    const rows = [
      { t: "2026-05-15T08:00:00Z", signature: "a", pos: { lat: 48.8, lon: 2.3 } },
      { t: "2026-09-24T08:00:00Z", signature: "b", pos: { lat: 32.1, lon: -16.9 } },
    ];
    let n = 0;
    const seen = [];
    const entries = await pollOfficialMoments({
      fetchFn: async () => {
        n += 1;
        return n === 1 ? { moments: [] } : { moments: rows };
      },
      sleep: async () => {},
      onUpdate: (next) => seen.push(next.entries.length),
    });
    assert.equal(n, 2);
    assert.equal(entries.length, 2);
    assert.equal(entries[0].signature, "a");
    assert.equal(entries[1].signature, "b");
    assert.deepEqual(seen, [0, 2]);
    assert.equal(nextEtaRetryMs(0), ETA_RETRY_MS[0]);
  });

  it("relance après un fetch en erreur puis s'arrête dès qu'il y a des lignes", async () => {
    let n = 0;
    const entries = await pollOfficialMoments({
      fetchFn: async () => {
        n += 1;
        if (n === 1) throw new Error("HTTP 500");
        return { moments: [{ t: "2026-05-15T08:00:00Z", signature: "a" }] };
      },
      sleep: async () => {},
    });
    assert.equal(n, 2);
    assert.equal(entries.length, 1);
    assert.equal(entries[0].signature, "a");
  });
});

describe("useMomentJournal — lot RD6 : nom d'AMP depuis le fait", () => {
  it("porte le nom de l'AMP (here.mpa) et de la marina (around), jamais inventé", () => {
    const prev = {
      here: { zee: { name: "ZEE A" }, mpa: [] },
      leg: { to: "La Rochelle", regime: "climatology" },
      alerts: [],
      around: [],
    };
    const cur = {
      here: {
        zee: { name: "ZEE A" },
        mpa: [{ name: "Iroise", nm: 4, site_id: "fr-amp-iroise" }],
      },
      leg: { to: "La Rochelle", regime: "climatology" },
      alerts: [{
        id: "mpa-fr-amp-iroise",
        kind: "mpa",
        title: "Aire marine protégée",
        fact: "Iroise (4 nm): IUCN II.",
      }],
      around: [{
        kind: "marina",
        title: "Marina du Château",
        fact: "Marina du Château (2 nm)",
      }],
    };
    const changes = localChanges(prev, cur);
    const amp = changes.find((c) => c.kind === "amp");
    assert.ok(amp, "entrée AMP");
    assert.equal(amp.title, "Iroise");
    assert.match(amp.fact, /Iroise/);
    assert.equal(changes.filter((c) => c.kind === "amp").length, 1, "pas de doublon alerte / mpa");
    const marina = changes.find((c) => c.kind === "marina");
    assert.ok(marina);
    assert.equal(marina.title, "Marina du Château");
    assert.match(marina.fact, /Marina du Château/);
    assert.equal(changes.some((c) => /invent|exemple|placeholder/i.test(`${c.title} ${c.fact}`)), false);
  });
});
