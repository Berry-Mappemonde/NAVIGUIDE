import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { flattenRoute } from "./routePlayhead.js";
import {
  ALONG_AMP_NM,
  MAX_PEARLS_SIM,
  MAX_PEARLS_SUIVRE,
  SUIVRE_LOOKAHEAD_MAX_NM,
  attachBags,
  buildAlongIndex,
  filmEventMarks,
  lookaheadNmFor,
  maxPearlsFor,
  nearestPearlBag,
  pearlKey,
  promoteLaterAtPlayhead,
  sampleLeg,
  upsertLedger,
} from "./iciAlong.js";
import { detectEvents, emptyEventMemory } from "./eventRules.js";
import { resolveOrders } from "./skipperOrders.js";

function lineFlat() {
  return flattenRoute([{
    coords: [
      [-1.16, 46.15],
      [-2.16, 46.15],
      [-3.16, 46.15],
      [-5.16, 46.15],
    ],
  }]);
}

describe("iciAlong sample", () => {
  it("behindNm keeps the pearl just passed; nearestPearlBag re-centres its thin bag on the boat", () => {
    const flat = lineFlat();
    const ahead = sampleLeg(flat, { fromNm: 0, toNm: flat.totalNm, boatNm: 50, maxPearls: 20 });
    assert.ok(ahead[0].whenNm >= 0, "sans behindNm : rien derrière");
    const around = sampleLeg(flat, { fromNm: 0, toNm: flat.totalNm, boatNm: 50, maxPearls: 20, behindNm: 24 });
    assert.ok(around[0].whenNm <= -20 && around[0].whenNm >= -24, `première perle derrière : ${around[0].whenNm}`);
    const key = pearlKey(around[1].lat, around[1].lon, null);
    const bags = new Map([[key, { at: { lat: around[1].lat, lon: around[1].lon }, zee: { name: "French EEZ", mrgid: 5677 }, poe: [], amp: [] }]]);
    const boat = { lat: around[1].lat, lon: around[1].lon + 0.05 };
    const near = nearestPearlBag(around, bags, boat, { maxNm: 15 });
    assert.equal(near.thin, true);
    assert.equal(near.zee.mrgid, 5677);
    assert.deepEqual(near.at, boat, "le sac est recentré sur le bateau");
    assert.ok(near.pearlNm < 3);
    assert.equal(nearestPearlBag(around, bags, { lat: 0, lon: 0 }, { maxNm: 15 }), null, "trop loin : rien");
    assert.equal(nearestPearlBag(around, new Map(), boat), null, "perle pas encore chargée : rien");
  });

  it("Simulation: dense pearls near the boat, coarser far ahead, the whole leg bounded", () => {
    const flat = lineFlat();
    const pearls = sampleLeg(flat, { fromNm: 0, toNm: flat.totalNm, boatNm: 0, maxPearls: 200, nearNm: 36, farStepNm: 48 });
    const steps = pearls.slice(1).map((p, i) => Math.round(p.cumNm - pearls[i].cumNm));
    assert.deepEqual(steps.slice(0, 3), [12, 12, 12], "12 nm jusqu’à nearNm");
    assert.ok(steps.slice(3).every((d) => d === 48), `puis 48 nm : ${steps}`);
    assert.ok(pearls.at(-1).cumNm <= flat.totalNm);
  });

  it("samples this leg every ~12 nm and skips nothing on a sea line", () => {
    const flat = lineFlat();
    const pearls = sampleLeg(flat, { fromNm: 0, toNm: flat.totalNm, boatNm: 0, maxPearls: 20 });
    assert.ok(pearls.length >= 3);
    assert.ok(pearls.every((p) => Number.isFinite(p.lat) && Number.isFinite(p.filmCum)));
    const steps = pearls.slice(1).map((p, i) => p.cumNm - pearls[i].cumNm);
    assert.ok(steps.every((d) => d >= 11 && d <= 13));
  });

  it("caps Suivre lookahead well under 39 000 nm", () => {
    assert.equal(lookaheadNmFor("suivre"), SUIVRE_LOOKAHEAD_MAX_NM);
    assert.equal(lookaheadNmFor("simulation"), Infinity);
    const flat = lineFlat();
    const pearls = sampleLeg(flat, {
      boatNm: 0,
      toNm: 20000,
      lookaheadNm: lookaheadNmFor("suivre"),
      maxPearls: MAX_PEARLS_SUIVRE,
    });
    assert.ok(pearls.length <= MAX_PEARLS_SUIVRE);
    assert.ok((pearls.at(-1)?.cumNm ?? 0) < 400);
  });

  it("Suivre horizon follows the skipper orders: nm = H × kn, pearls = ceil(nm / 12)", () => {
    const cruise = resolveOrders({ profile: "cruise" }, { mode: "suivre" });
    assert.equal(lookaheadNmFor("suivre", cruise), 252);
    assert.equal(maxPearlsFor("suivre", cruise), 21);
    assert.equal(SUIVRE_LOOKAHEAD_MAX_NM, 252);
    assert.equal(MAX_PEARLS_SUIVRE, 21);

    const coastal = resolveOrders({ profile: "coastal" }, { mode: "suivre" });
    assert.equal(lookaheadNmFor("suivre", coastal), 120);
    assert.equal(maxPearlsFor("suivre", coastal), 10);

    const ocean = resolveOrders({ profile: "ocean" }, { mode: "suivre" });
    assert.equal(lookaheadNmFor("suivre", ocean), 336);
    assert.equal(maxPearlsFor("suivre", ocean), 28);
    assert.equal(maxPearlsFor("simulation", ocean), MAX_PEARLS_SIM);
  });

  it("48 h on Ocean really samples past the old 24 pearls / 350 nm cap", () => {
    const ocean = resolveOrders({ profile: "ocean" }, { mode: "suivre" });
    const flat = flattenRoute([{
      coords: [[-1.16, 46.15], [-6.16, 46.15], [-12.16, 46.15], [-18.16, 46.15]],
    }]);
    assert.ok(flat.totalNm > 600, `long sea line, got ${flat.totalNm} nm`);
    const pearls = sampleLeg(flat, {
      boatNm: 0,
      toNm: 20000,
      lookaheadNm: lookaheadNmFor("suivre", ocean),
      maxPearls: maxPearlsFor("suivre", ocean),
    });
    assert.ok(pearls.length > 24, `expected > 24 pearls, got ${pearls.length}`);
    assert.ok(pearls.length <= 28);
    assert.ok((pearls.at(-1)?.cumNm ?? 0) <= 336 + 1e-6);
    assert.ok((pearls.at(-1)?.cumNm ?? 0) < 1000, "never the whole route");
  });

  it("along-track marina / AMP radius follow the orders", () => {
    const pearls = [{ lat: 46.15, lon: -1.5, month: 6, whenNm: 12 }];
    const bagMap = new Map([[pearlKey(46.15, -1.5, 6), {
      zee: null,
      poe: [],
      amp: [],
      nearby: { marinas: [{ name: "Far marina", nm: 30 }], capitaineries: [], wpi: [] },
    }]]);
    const cruise = attachBags(pearls, bagMap, 6, resolveOrders({ profile: "cruise" }, { mode: "suivre" }));
    assert.equal(cruise[0].harbours.length, 0);
    const ocean = attachBags(pearls, bagMap, 6, resolveOrders({ profile: "ocean" }, { mode: "suivre" }));
    assert.equal(ocean[0].harbours.length, 1);
  });

  it("skips an air hop on the current stretch", () => {
    const flat = flattenRoute([
      { coords: [[-1, 46], [-1.2, 46]] },
      { coords: [[-40, 30], [-41, 30]] },
    ]);
    const pearls = sampleLeg(flat, { fromNm: 0, toNm: 6, boatNm: 0 });
    assert.ok(pearls.length >= 1);
    assert.ok(pearls.every((p) => p.lat > 40 && p.lon > -5));
    assert.ok(pearls.every((p) => !p.jump));
  });

  it("attaches bags on the track, not a side AMP beyond 15 nm", () => {
    const pearls = [{ lat: 46, lon: -2, cumNm: 12, filmCum: 12, whenNm: 12, month: 6 }];
    const map = new Map([[pearlKey(46, -2, 6), {
      zee: { name: "Spain", mrgid: 8462 },
      amp: [
        { name: "Sur le trait", site_id: "a1", nm: 8, visit_url: "https://x.fr/v", manager_url: "https://x.fr" },
        { name: "Trop loin", site_id: "a2", nm: ALONG_AMP_NM + 4 },
      ],
      nearby: { marinas: [{ name: "Port", nm: 6 }], capitaineries: [], wpi: [] },
    }]]);
    const along = buildAlongIndex(pearls, map, 6);
    assert.equal(along.pearls[0].zee.mrgid, 8462);
    assert.equal(along.pearls[0].amp.length, 1);
    assert.equal(along.pearls[0].amp[0].name, "Sur le trait");
    assert.equal(along.harbours[0].name, "Port");
  });
});

describe("iciAlong events + ledger", () => {
  it("emits zee-ahead and amp-ahead from along pearls", () => {
    const at = { zee: { name: "France", mrgid: 5677 }, amp: [], poe: [] };
    const along = {
      pearls: [{
        whenNm: 40,
        filmCum: 40,
        zee: { name: "Spanish Exclusive Economic Zone", mrgid: 8462 },
        amp: [{ name: "Cabrera", site_id: "cab", visit_url: "https://cabrera.es/v", manager_url: "https://cabrera.es" }],
        poe: [{ name: "Palma", nm: 12, url: "https://aduana.es" }],
        harbours: [],
      }],
      harbours: [],
    };
    const r = detectEvents({
      at,
      prev: at,
      along,
      ctx: { mode: "simulation", legId: "LR→Ajaccio", cumNm: 10, filmCum: 10 },
      memory: emptyEventMemory("LR→Ajaccio"),
    });
    const types = r.events.map((e) => e.type);
    assert.ok(types.includes("zee-ahead"));
    assert.ok(types.includes("amp-ahead"));
    assert.ok(types.includes("poe-ahead"));
    assert.equal(r.events.find((e) => e.type === "zee-ahead").whenNm, 40);
    assert.equal(r.events.find((e) => e.type === "amp-ahead").payload.tavily, null);
    assert.equal(r.events.find((e) => e.type === "poe-ahead").name, "Palma");
  });

  it("does not announce the boat PoE as ahead at the current pearl", () => {
    const at = { zee: { mrgid: 5677 }, amp: [], poe: [{ name: "La Rochelle", nm: 2 }] };
    const r = detectEvents({
      at,
      prev: at,
      along: {
        pearls: [{
          whenNm: 0,
          filmCum: 10,
          zee: { mrgid: 5677 },
          amp: [],
          poe: [{ name: "La Rochelle", nm: 2 }],
          harbours: [],
        }],
        harbours: [],
      },
      ctx: { mode: "simulation", legId: "x" },
      memory: emptyEventMemory("x"),
    });
    assert.ok(!r.events.some((e) => e.type === "poe-ahead"));
  });

  it("does not announce an AMP beside the track if it is not on a pearl", () => {
    const at = {
      zee: { mrgid: 5677 },
      amp: [{ name: "À côté", site_id: "side", nm: 8 }],
    };
    const r = detectEvents({
      at,
      prev: at,
      along: { pearls: [{ whenNm: 20, filmCum: 20, zee: { mrgid: 5677 }, amp: [], poe: [], harbours: [] }], harbours: [] },
      ctx: { mode: "simulation", legId: "x" },
      memory: emptyEventMemory("x"),
    });
    assert.ok(!r.events.some((e) => e.type === "amp-ahead"));
  });

  it("keeps a ledger and promotes later once at the playhead", () => {
    const later = {
      id: "wind-shift:1",
      stableKey: "wind-shift:forecast",
      type: "wind-shift",
      judge: "later",
      filmCum: 80,
      story: { status: "template" },
    };
    const led = upsertLedger([], [later]);
    const still = promoteLaterAtPlayhead(led, 20);
    assert.equal(still[0].judge, "later");
    const now = promoteLaterAtPlayhead(led, 80);
    assert.equal(now[0].judge, "now");
    assert.equal(now[0].promoted, true);
    assert.equal(now[0].seenNow, true);
    const again = promoteLaterAtPlayhead(now, 10);
    assert.equal(again[0].judge, "now");
    assert.equal(again[0].seenNow, true);
  });

  it("keeps a pending story when the detector re-emits a template", () => {
    const pending = {
      id: "zee-enter:1",
      stableKey: "zee-enter:8462",
      type: "zee-enter",
      judge: "now",
      story: { status: "pending", cascade: "nim-or-claude", tavily: null, nvidia: null },
      phrase: "On vient d’entrer dans Spain.",
    };
    const led = upsertLedger([], [pending]);
    const again = upsertLedger(led, [{
      ...pending,
      story: { status: "template" },
      phrase: "On vient d’entrer dans Spain.",
    }]);
    assert.equal(again[0].story.status, "pending");
  });

  it("a pill already told under the old orders keeps its story and its orders after a profile change", () => {
    const told = {
      id: "hs-shift:forecast:2",
      stableKey: "hs-shift:forecast",
      type: "hs-shift",
      judge: "now",
      payload: { hs: 3.6, alert: true, alertM: 3.5, tavily: null, nvidia: null },
      skipper: { profile: "cruise", used: [{ id: "hsAlertM", value: 3.5, unit: "m", source: "usage" }] },
      story: { status: "ready", text: "Houle 3,6 m, au-dessus des 3,5 m de croisière.", tavily: null, nvidia: null },
      phrase: "Houle 3,6 m, au-dessus des 3,5 m de croisière.",
    };
    const led = upsertLedger([], [told]);
    const afterSwitch = upsertLedger(led, [{
      ...told,
      payload: { hs: 3.6, alert: true, alertM: 2.5, tavily: null, nvidia: null },
      skipper: { profile: "coastal", used: [{ id: "hsAlertM", value: 2.5, unit: "m", source: "usage" }] },
      story: { status: "template" },
      phrase: "Houle 3.6 m (kind: forecast, alerte).",
    }]);
    assert.equal(afterSwitch.length, 1, "no second pill, no rewind");
    assert.equal(afterSwitch[0].story.status, "ready");
    assert.equal(afterSwitch[0].phrase, told.story.text, "the ready text stays");
    assert.equal(afterSwitch[0].skipper.profile, "cruise", "the story keeps the orders it was written under");
    assert.equal(afterSwitch[0].skipper.used[0].value, 3.5);

    const fresh = upsertLedger([], [{ ...told, story: { status: "template" }, skipper: { profile: "coastal", used: [] } }]);
    assert.equal(fresh[0].skipper.profile, "coastal", "a pill without a story follows the new orders");
  });

  it("Simulation keeps every visible pill", () => {
    const marks = filmEventMarks([
      { id: "a", type: "zee-enter", judge: "now", filmCum: 10 },
      { id: "b", type: "amp-ahead", judge: "later", filmCum: 40, whenNm: 30 },
      { id: "c", type: "zee-ahead", judge: "later", filmCum: 90, whenNm: 80 },
      { id: "d", type: "group", judge: "now", filmCum: 40 },
    ], { mode: "simulation" });
    assert.equal(marks.length, 3);
    assert.deepEqual(marks.map((e) => e.type), ["zee-enter", "amp-ahead", "zee-ahead"]);
  });

  it("Suivre keeps live + one upcoming pill only", () => {
    const marks = filmEventMarks([
      { id: "a", type: "zee-enter", judge: "now", filmCum: 10 },
      { id: "b", type: "amp-ahead", judge: "later", filmCum: 40, whenNm: 30 },
      { id: "c", type: "zee-ahead", judge: "later", filmCum: 90, whenNm: 80 },
    ], { mode: "suivre" });
    assert.equal(marks.length, 2);
    assert.equal(marks[0].type, "zee-enter");
    assert.equal(marks[1].type, "amp-ahead");
  });
});

