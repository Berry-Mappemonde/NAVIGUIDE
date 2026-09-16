import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  DEFAULT_ORDERS,
  DEFAULT_PROFILE,
  PROFILES,
  PROFILE_TABLE,
  STORAGE_KEY,
  clearSavedOrders,
  depthPhrase,
  exampleLine,
  lookaheadBudget,
  ordersLine,
  readBoat,
  readSavedOrders,
  resolveOrders,
  skipperSnapshot,
  suggestProfileForBoat,
  thresholdValues,
  thresholdsForEvent,
  writeSavedOrders,
} from "./skipperOrders.js";
import {
  CURRENT_SHIFT_KN,
  DEPTH_ALERT_M,
  GALE_HOLD_KT,
  GALE_KT,
  GROUP_NM,
  HS_ALERT_M,
  HS_SHIFT_M,
  MARINA_REFUGE_NM,
  RAIN_3H_MM,
  RAIN_MM_H,
  ROUTE_SAMPLE_NM,
  WIND_SHIFT_DEG,
  WIND_SHIFT_KT,
} from "./eventRules.js";
import { SUIVRE_LOOKAHEAD_H } from "./iciAlong.js";

const src = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "skipperOrders.js"), "utf8");
const LLM_SOURCES = new Set(["beaufort", "wmo", "metoffice", "usage", "derive", "ui"]);

function memStorage(initial = {}) {
  const map = new Map(Object.entries(initial));
  return {
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => map.set(k, String(v)),
    removeItem: (k) => map.delete(k),
    dump: () => Object.fromEntries(map),
  };
}

const berryPolar = {
  expedition_id: "berry-mappemonde-2026",
  boat_name: "Leopard 46",
  vmg_summary: {
    8: { downwind: { speed: 6.0 } },
    10: { downwind: { speed: 8.0 } },
    12: { downwind: { speed: 10.0 } },
    16: { downwind: { speed: 12.0 } },
  },
};

describe("skipperOrders — source contract", () => {
  it("is pure: no HTTP, no chat, no Nemotron / Tavily, no runtime formula", () => {
    assert.doesNotMatch(src, /fetch\(|Nemotron|Tavily|Token Factory|POST \/polar\/chat/);
    assert.doesNotMatch(src, /0\.30?\s*\*\s*(loa|L\b)/i);
    assert.doesNotMatch(src, /max\(\s*12\b/);
    assert.match(src, /Cruise = today's E1 constants/);
  });
});

describe("three profiles, one number per threshold", () => {
  it("exposes coastal | cruise | ocean and defaults to cruise", () => {
    assert.deepEqual([...PROFILES], ["coastal", "cruise", "ocean"]);
    assert.equal(DEFAULT_PROFILE, "cruise");
    assert.equal(DEFAULT_ORDERS.profile, "cruise");
    assert.equal(resolveOrders(null).profile, "cruise");
    assert.equal(resolveOrders({ profile: "tableur" }).profile, "cruise");
    assert.equal(resolveOrders({ profile: "ocean" }).profile, "ocean");
  });

  it("cruise equals today's E1 constants (tests E1 stay green)", () => {
    const v = DEFAULT_ORDERS.values;
    assert.equal(v.hsAlertM, HS_ALERT_M);
    assert.equal(v.depthAlertM, DEPTH_ALERT_M);
    assert.equal(v.windShiftKt, WIND_SHIFT_KT);
    assert.equal(v.windShiftDeg, WIND_SHIFT_DEG);
    assert.equal(v.galeKt, GALE_KT);
    assert.equal(v.galeHoldKt, GALE_HOLD_KT);
    assert.equal(v.hsShiftM, HS_SHIFT_M);
    assert.equal(v.currentShiftKn, CURRENT_SHIFT_KN);
    assert.equal(v.rainMmH, RAIN_MM_H);
    assert.equal(v.rain3hMm, RAIN_3H_MM);
    assert.equal(v.marinaRefugeNm, MARINA_REFUGE_NM);
    assert.equal(v.groupNm, GROUP_NM);
    assert.equal(v.routeSampleNm, ROUTE_SAMPLE_NM);
    assert.equal(v.suivreLookaheadH, SUIVRE_LOOKAHEAD_H);
  });

  it("writes the Hs / depth cells as single numbers per profile", () => {
    assert.equal(PROFILE_TABLE.coastal.hsAlertM, 2.5);
    assert.equal(PROFILE_TABLE.cruise.hsAlertM, 3.5);
    assert.equal(PROFILE_TABLE.ocean.hsAlertM, 5.0);
    assert.equal(PROFILE_TABLE.coastal.depthAlertM, 8);
    assert.equal(PROFILE_TABLE.cruise.depthAlertM, 15);
    assert.equal(PROFILE_TABLE.ocean.depthAlertM, 5);
    assert.equal(PROFILE_TABLE.coastal.depthLabel, "plateau");
    assert.equal(PROFILE_TABLE.cruise.depthLabel, "plateau");
    assert.equal(PROFILE_TABLE.ocean.depthLabel, "talonnage");
    assert.equal(PROFILE_TABLE.ocean.windShiftKt, 16);
    assert.equal(PROFILE_TABLE.coastal.windShiftKt, 6);
  });

  it("every threshold has exactly one numeric value and a known source", () => {
    for (const profile of PROFILES) {
      const o = resolveOrders({ profile });
      const ids = new Set();
      for (const t of o.thresholds) {
        assert.equal(typeof t.value, "number", `${profile}.${t.id}`);
        assert.ok(!ids.has(t.id), `duplicate ${t.id}`);
        ids.add(t.id);
        assert.ok(!("alt" in t) && !("formula" in t) && !("fallback" in t));
        assert.ok(LLM_SOURCES.has(t.source) || t.source === "engine", `${t.id}: ${t.source}`);
      }
    }
  });

  it("gale 34 / hold 28 kn are Beaufort, locked and identical in the three profiles", () => {
    for (const profile of PROFILES) {
      const o = resolveOrders({ profile });
      const gale = o.thresholds.find((t) => t.id === "galeKt");
      const hold = o.thresholds.find((t) => t.id === "galeHoldKt");
      assert.equal(gale.value, 34);
      assert.equal(hold.value, 28);
      assert.equal(gale.source, "beaufort");
      assert.equal(gale.locked, true);
      assert.equal(hold.locked, true);
    }
  });

  it("marks the ocean wind step as WMO squall, the others as usage", () => {
    assert.equal(resolveOrders({ profile: "ocean" }).thresholds.find((t) => t.id === "windShiftKt").source, "wmo");
    assert.equal(resolveOrders({ profile: "cruise" }).thresholds.find((t) => t.id === "windShiftKt").source, "usage");
  });

  it("carries the resolved Hs rule for the LLM, never a formula", () => {
    const hs = resolveOrders({ profile: "cruise" }).thresholds.find((t) => t.id === "hsAlertM");
    assert.equal(hs.value, 3.5);
    assert.match(hs.rule, /Croisière E1 3,5 m/);
    assert.doesNotMatch(hs.rule, /0,30|×\s*L/);
  });

  it("thresholdValues falls back to cruise when orders are missing", () => {
    assert.equal(thresholdValues(null).hsAlertM, 3.5);
    assert.equal(thresholdValues({}).depthAlertM, 15);
    assert.equal(thresholdValues(resolveOrders({ profile: "coastal" })).hsAlertM, 2.5);
  });
});

describe("rain is Suivre only", () => {
  it("disables rain / refuge in simulation with the reason, keeps them in suivre", () => {
    const sim = resolveOrders({ profile: "cruise" }, { mode: "simulation" });
    assert.equal(sim.rainEnabled, false);
    assert.equal(sim.rainReason, "simulation_no_rain");
    const rain = sim.thresholds.find((t) => t.id === "rainMmH");
    assert.equal(rain.value, 4);
    assert.equal(rain.enabled, false);
    assert.equal(rain.reason, "simulation_no_rain");

    const suivre = resolveOrders({ profile: "cruise" }, { mode: "suivre" });
    assert.equal(suivre.rainEnabled, true);
    assert.equal(suivre.thresholds.find((t) => t.id === "marinaRefugeNm").enabled, true);
  });
});

describe("lookahead budget — the horizon never lies (§2.6)", () => {
  it("derives nm = H × kn and pearls = ceil(nm / 12) for 24 / 36 / 48 h", () => {
    const coastal = lookaheadBudget(resolveOrders({ profile: "coastal" }));
    assert.deepEqual(
      [coastal.hours, coastal.planningKn, coastal.maxNm, coastal.maxPearls],
      [24, 5, 120, 10],
    );
    const cruise = lookaheadBudget(resolveOrders({ profile: "cruise" }));
    assert.deepEqual(
      [cruise.hours, cruise.planningKn, cruise.maxNm, cruise.maxPearls],
      [36, 7, 252, 21],
    );
    const ocean = lookaheadBudget(resolveOrders({ profile: "ocean" }));
    assert.deepEqual(
      [ocean.hours, ocean.planningKn, ocean.maxNm, ocean.maxPearls],
      [48, 7, 336, 28],
    );
  });

  it("follows a fast polar: 48 h × 10 kn = 480 nm / 40 pearls, never the old 350 / 24 cap", () => {
    const fast = { ...berryPolar, vmg_summary: { 12: { downwind: { speed: 10 } } } };
    const b = lookaheadBudget(resolveOrders({ profile: "ocean" }, { polar: fast }));
    assert.equal(b.planningKn, 10);
    assert.equal(b.maxNm, 480);
    assert.equal(b.maxPearls, 40);
    assert.ok(b.maxNm > 350);
    assert.ok(b.maxPearls > 24);
  });

  it("exposes the derived numbers as thresholds with source derive", () => {
    const o = resolveOrders({ profile: "ocean" });
    const nm = o.thresholds.find((t) => t.id === "suivreLookaheadMaxNm");
    const pearls = o.thresholds.find((t) => t.id === "maxPearlsSuivre");
    assert.equal(nm.value, 336);
    assert.equal(nm.source, "derive");
    assert.equal(pearls.value, 28);
    assert.equal(pearls.source, "derive");
  });

  it("falls back to the cruise budget without orders", () => {
    assert.equal(lookaheadBudget(null).maxNm, 252);
    assert.equal(lookaheadBudget(undefined).maxPearls, 21);
  });
});

describe("boat is read from the polar, never typed", () => {
  it("reads the name and planning speed from the polar, Berry defaults for L / draft", () => {
    const o = resolveOrders({ profile: "cruise" }, { polar: berryPolar });
    assert.equal(o.boat.name, "Leopard 46");
    assert.equal(o.boat.loaM, 14);
    assert.equal(o.boat.draftM, 1.4);
    assert.equal(o.boat.planningKn, 9);
    assert.equal(o.boat.source.loa, "default");
    assert.equal(o.boat.source.planningKn, "polar");
    assert.equal(o.values.planningKn, 9);
    assert.equal(o.budget.maxNm, 324);
  });

  it("uses the profile speed when the polar has no VMG table", () => {
    const o = resolveOrders({ profile: "coastal" }, { polar: { boat_name: "Dinghy" } });
    assert.equal(o.boat.planningKn, null);
    assert.equal(o.values.planningKn, 5);
    assert.equal(o.boat.source.planningKn, "profile");
  });

  it("proposes coastal for a small polar (L < 11 m or draft < 1.1 m) without forcing it", () => {
    const small = readBoat({ boat_name: "First 31.7", loa_m: 9.6, draft_m: 1.9 });
    assert.deepEqual(suggestProfileForBoat(small), { profile: "coastal", reason: "small_loa" });
    const o = resolveOrders({ profile: "cruise" }, { polar: { boat_name: "First 31.7", loa_m: 9.6 } });
    assert.equal(o.profile, "cruise");
    assert.equal(o.suggest?.profile, "coastal");
    assert.equal(resolveOrders({ profile: "coastal" }, { polar: { loa_m: 9.6 } }).suggest, null);
  });

  it("never proposes on the Berry defaults (nothing was read)", () => {
    assert.equal(suggestProfileForBoat(readBoat(null)), null);
    assert.equal(resolveOrders({ profile: "cruise" }, { polar: berryPolar }).suggest, null);
  });
});

describe("thresholdsForEvent → used", () => {
  it("cites only the ids that made the event switch, one value per id", () => {
    const o = resolveOrders({ profile: "cruise" }, { mode: "suivre" });
    assert.deepEqual(thresholdsForEvent("wind-gale", o).map((u) => u.id), ["galeKt", "galeHoldKt"]);
    assert.deepEqual(
      thresholdsForEvent("marina-refuge", o).map((u) => u.id),
      ["rainMmH", "rain3hMm", "marinaRefugeNm"],
    );
    assert.deepEqual(thresholdsForEvent("depth-alert", o).map((u) => u.id), ["depthAlertM"]);
    assert.deepEqual(thresholdsForEvent("wind-shift", o).map((u) => u.id), ["windShiftKt", "windShiftDeg"]);
    assert.deepEqual(thresholdsForEvent("zee-enter", o), []);
    for (const u of thresholdsForEvent("wx-alert", o)) {
      assert.equal(typeof u.value, "number");
      assert.ok(LLM_SOURCES.has(u.source));
    }
  });

  it("gives the LLM the resolved Hs number and its rule", () => {
    const used = thresholdsForEvent("hs-shift", resolveOrders({ profile: "cruise" }), { hs: 3.6, alert: true });
    const hs = used.find((u) => u.id === "hsAlertM");
    assert.deepEqual(
      { id: hs.id, value: hs.value, unit: hs.unit, source: hs.source },
      { id: "hsAlertM", value: 3.5, unit: "m", source: "usage" },
    );
    assert.match(hs.rule, /Croisière E1 3,5 m/);
    const quiet = thresholdsForEvent("hs-shift", resolveOrders({ profile: "cruise" }), { dHs: 1.2, alert: false });
    assert.deepEqual(quiet.map((u) => u.id), ["hsShiftM"]);
  });

  it("never cites rain in simulation", () => {
    const sim = resolveOrders({ profile: "cruise" }, { mode: "simulation" });
    assert.deepEqual(thresholdsForEvent("marina-refuge", sim), []);
    assert.ok(!thresholdsForEvent("wx-alert", sim).some((u) => u.id.startsWith("rain")));
    const suivre = resolveOrders({ profile: "cruise" }, { mode: "suivre" });
    assert.ok(thresholdsForEvent("wx-alert", suivre, { rain: true }).some((u) => u.id === "rainMmH"));
  });

  it("freezes a skipper snapshot in the plan's JSON shape", () => {
    const snap = skipperSnapshot("hs-shift", resolveOrders({ profile: "cruise" }, { polar: berryPolar }), { alert: true });
    assert.equal(snap.profile, "cruise");
    assert.equal(snap.profile_phrase, "Ordres Berry — croisière.");
    assert.equal(snap.comfort, "normal");
    assert.deepEqual(snap.boat, { name: "Leopard 46", loaM: 14, draftM: 1.4 });
    assert.ok(snap.used.some((u) => u.id === "hsAlertM" && u.value === 3.5));
    assert.ok(!("tavily" in snap) && !("nvidia" in snap));
  });
});

describe("phrases FR / EN", () => {
  it("writes the living example under two lines, with the skipper's numbers", () => {
    const o = resolveOrders({ profile: "cruise" });
    const fr = exampleLine(o, { tws: 18, hs: 1.4 }, "fr");
    assert.equal(fr, "Vent ici 18 kn — je me tais. À 34 kn je parle. Mer 1,4 m — sous 3,5 m.");
    const en = exampleLine(o, { tws: 18, hs: 1.4 }, "en");
    assert.equal(en, "Wind here 18 kn — I stay quiet. At 34 kn I speak. Sea 1.4 m — under 3.5 m.");
    assert.ok(!fr.includes("\n"));
  });

  it("changes with the profile, gale does not", () => {
    const ocean = exampleLine(resolveOrders({ profile: "ocean" }), { tws: 36, hs: 4.2 }, "fr");
    assert.match(ocean, /coup de vent, je parle/);
    assert.match(ocean, /Mer 4,2 m — sous 5,0 m/);
    const coastal = exampleLine(resolveOrders({ profile: "coastal" }), { tws: 12, hs: 2.7, depthM: 6 }, "fr");
    assert.match(coastal, /au-dessus de 2,5 m, je parle/);
    assert.match(coastal, /Fond 6 m — sous 8 m, on approche du plateau/);
  });

  it("stays honest without a bag", () => {
    assert.equal(
      exampleLine(resolveOrders({ profile: "cruise" }), {}, "fr"),
      "Pas encore de sac ici. Je parle à 34 kn, mer 3,5 m, fond 15 m.",
    );
  });

  it("writes the cyan orders line and the depth phrase per profile", () => {
    assert.equal(ordersLine(resolveOrders({ profile: "cruise" }), "fr"), "Ordres : croisière · Hs 3,5 m · fond 15 m");
    assert.equal(ordersLine(resolveOrders({ profile: "ocean" }), "en"), "Orders: offshore · Hs 5.0 m · depth 5 m");
    assert.match(depthPhrase(12, resolveOrders({ profile: "cruise" }), "fr"), /^On approche du plateau : 12 m sondés, sous 15 m\./);
    assert.match(depthPhrase(4, resolveOrders({ profile: "ocean" }), "fr"), /^Risque de talonner : 4 m sondés, sous 5 m\./);
    assert.match(depthPhrase(4, resolveOrders({ profile: "ocean" }), "en"), /^Grounding risk/);
  });
});

describe("persistence — tab + localStorage, profile only", () => {
  it("uses the v1 key and stores only the character", () => {
    assert.equal(STORAGE_KEY, "ng.sim.skipperOrders.v1");
    const mem = memStorage();
    assert.equal(writeSavedOrders(mem, { profile: "ocean", comfort: "hard", loaM: 9 }), true);
    assert.deepEqual(JSON.parse(mem.dump()[STORAGE_KEY]), { profile: "ocean" });
    assert.deepEqual(readSavedOrders(mem), { profile: "ocean" });
  });

  it("returns cruise when nothing or garbage is stored, and reset clears", () => {
    assert.equal(readSavedOrders(memStorage()), null);
    assert.equal(resolveOrders(readSavedOrders(memStorage())).profile, "cruise");
    const bad = memStorage({ [STORAGE_KEY]: "{not json" });
    assert.equal(readSavedOrders(bad), null);
    const mem = memStorage({ [STORAGE_KEY]: JSON.stringify({ profile: "coastal" }) });
    assert.equal(clearSavedOrders(mem), true);
    assert.equal(readSavedOrders(mem), null);
    assert.equal(readSavedOrders(null), null);
    assert.equal(writeSavedOrders(null, { profile: "ocean" }), true);
  });
});
