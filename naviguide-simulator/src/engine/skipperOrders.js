/**
 * Skipper orders — one character, one number per threshold.
 * Pure functions. No HTTP. No chat. No world search. No extra LLM provider.
 *
 * Cruise = today's E1 constants (eventRules.js). Coastal / Ocean = fixed
 * numbers written here once. No formula at runtime, no second default.
 * The boat (name, L, draft, planning speed) is READ from the polar, never typed.
 */

import { expeditionBoatKnots } from "./playSpeeds.js";

export const PROFILES = Object.freeze(["coastal", "cruise", "ocean"]);
export const DEFAULT_PROFILE = "cruise";
export const COMFORT_DEFAULT = "normal";
export const STORAGE_KEY = "ng.sim.skipperOrders.v1";
export const DEFAULT_BOAT = Object.freeze({ name: null, loaM: 14, draftM: 1.4 });
export const SMALL_BOAT_LOA_M = 11;
export const SMALL_BOAT_DRAFT_M = 1.1;

/** Beaufort 8 / 7. Same in the three profiles. Read-only. */
const LOCKED = Object.freeze({ galeKt: 34, galeHoldKt: 28 });

/** Engine / expert numbers (hide or S7+). Same in the three profiles in v1. */
const SHARED = Object.freeze({
  galePct: 15,
  windShiftResetKt: 4,
  windShiftResetDeg: 20,
  cooldownNm: 15,
  cooldownMin: 30,
  currentIgnoreKn: 0.3,
  currentInvertDeg: 120,
  ampHysteresisNm: 5,
  ampAheadMinNm: 5,
  marinaRefugeCooldownMin: 360,
  depthCooldownNm: 2,
  routeSampleNm: 12,
  groupNmFast: 80,
  iciRadiusNm: 30,
  alongAmpNm: 15,
});

/** The three characters. Each Hs / depth cell IS the number. */
export const PROFILE_TABLE = Object.freeze({
  coastal: Object.freeze({
    id: "coastal",
    phrase: Object.freeze({ fr: "Je parle tôt.", en: "I speak early." }),
    windShiftKt: 6,
    windShiftDeg: 30,
    hsAlertM: 2.5,
    hsShiftM: 0.6,
    currentShiftKn: 0.6,
    depthAlertM: 8,
    depthLabel: "plateau",
    rainMmH: 3,
    rain3hMm: 8,
    marinaRefugeNm: 15,
    suivreLookaheadH: 24,
    groupNm: 8,
    planningKnDefault: 5,
  }),
  cruise: Object.freeze({
    id: "cruise",
    phrase: Object.freeze({ fr: "Ordres Berry — croisière.", en: "Berry orders — cruise." }),
    windShiftKt: 8,
    windShiftDeg: 40,
    hsAlertM: 3.5,
    hsShiftM: 1.0,
    currentShiftKn: 1.0,
    depthAlertM: 15,
    depthLabel: "plateau",
    rainMmH: 4,
    rain3hMm: 10,
    marinaRefugeNm: 25,
    suivreLookaheadH: 36,
    groupNm: 15,
    planningKnDefault: 7,
  }),
  ocean: Object.freeze({
    id: "ocean",
    phrase: Object.freeze({ fr: "Je ne parle que si ça compte.", en: "I only speak when it matters." }),
    windShiftKt: 16,
    windShiftDeg: 60,
    hsAlertM: 5.0,
    hsShiftM: 1.5,
    currentShiftKn: 1.5,
    depthAlertM: 5,
    depthLabel: "talonnage",
    rainMmH: 6,
    rain3hMm: 15,
    marinaRefugeNm: 40,
    suivreLookaheadH: 48,
    groupNm: 25,
    planningKnDefault: 7,
  }),
});

const RAIN_IDS = new Set(["rainMmH", "rain3hMm", "marinaRefugeNm", "marinaRefugeCooldownMin"]);

const PROFILE_LABEL = Object.freeze({
  coastal: Object.freeze({ fr: "côtier", en: "coastal" }),
  cruise: Object.freeze({ fr: "croisière", en: "cruise" }),
  ocean: Object.freeze({ fr: "large", en: "offshore" }),
});

/** unit / source / rule per id. `source` ∈ beaufort | wmo | metoffice | usage | derive | ui | engine. */
const META = Object.freeze({
  galeKt: { unit: "kn", source: "beaufort", locked: true, rule: "Beaufort 8" },
  galeHoldKt: { unit: "kn", source: "beaufort", locked: true, rule: "Beaufort 7, fin du coup de vent" },
  galePct: { unit: "%", source: "ui", rule: "part de la rose climatologique" },
  windShiftKt: {
    unit: "kn",
    source: (p) => (p === "ocean" ? "wmo" : "usage"),
    rule: (p) => (p === "ocean" ? "grain OMM +16 kn" : `ça change la toile (${PROFILE_LABEL[p].fr})`),
  },
  windShiftDeg: { unit: "°", source: "usage", rule: (p) => `bascule de vent (${PROFILE_LABEL[p].fr})` },
  windShiftResetKt: { unit: "kn", source: "ui", rule: "retour au calme" },
  windShiftResetDeg: { unit: "°", source: "ui", rule: "retour au calme" },
  cooldownNm: { unit: "nm", source: "engine", rule: "anti-spam" },
  cooldownMin: { unit: "min", source: "engine", rule: "anti-spam" },
  currentShiftKn: { unit: "kn", source: "usage", rule: (p) => `usage routage (${PROFILE_LABEL[p].fr})` },
  currentIgnoreKn: { unit: "kn", source: "usage", rule: "bruit de courant" },
  currentInvertDeg: { unit: "°", source: "usage", rule: "inversion de courant" },
  hsShiftM: { unit: "m", source: "usage", rule: (p) => `variation de houle (${PROFILE_LABEL[p].fr})` },
  hsAlertM: {
    unit: "m",
    source: "usage",
    rule: (p) => ({
      coastal: "constante Côtier 2,5 m — je parle tôt",
      cruise: "constante Croisière E1 3,5 m",
      ocean: "constante Large 5,0 m — je ne parle que si ça compte",
    })[p],
  },
  ampHysteresisNm: { unit: "nm", source: "engine", rule: "hystérésis AMP" },
  ampAheadMinNm: { unit: "nm", source: "ui", rule: "distance minimale devant" },
  rainMmH: { unit: "mm/h", source: "metoffice", rule: "pluie forte Met Office" },
  rain3hMm: { unit: "mm/3h", source: "wmo", rule: "pluie forte OMM sur 3 h" },
  marinaRefugeNm: { unit: "nm", source: "ui", rule: (p) => `repli Plan B (${PROFILE_LABEL[p].fr})` },
  marinaRefugeCooldownMin: { unit: "min", source: "ui", rule: "anti-spam repli" },
  depthAlertM: {
    unit: "m",
    source: "ui",
    rule: (p) => ({
      coastal: "constante Côtier 8 m — plateau",
      cruise: "constante Croisière E1 15 m — plateau",
      ocean: "constante Large 5 m — talonnage",
    })[p],
  },
  depthCooldownNm: { unit: "nm", source: "engine", rule: "anti-spam fond" },
  routeSampleNm: { unit: "nm", source: "engine", rule: "pas des perles" },
  groupNm: { unit: "nm", source: "ui", rule: (p) => `groupement (${PROFILE_LABEL[p].fr})` },
  groupNmFast: { unit: "nm", source: "ui", rule: "groupement film rapide" },
  iciRadiusNm: { unit: "nm", source: "ui", rule: "rayon du sac (Met Éireann côtier)" },
  alongAmpNm: { unit: "nm", source: "ui", rule: "AMP sur le trait" },
  suivreLookaheadH: { unit: "h", source: "usage", rule: (p) => `fenêtre GRIB (${PROFILE_LABEL[p].fr})` },
  suivreLookaheadMaxNm: { unit: "nm", source: "derive", rule: "heures × nœuds" },
  maxPearlsSuivre: { unit: "perles", source: "derive", rule: "ceil(nm / 12)" },
  planningKn: { unit: "kn", source: "usage", rule: null },
});

function isFinitePositive(n) {
  return Number.isFinite(n) && n > 0;
}

/** null / undefined / "" stay unknown (NaN) — Number(null) would lie with 0. */
function measure(v) {
  if (v == null || v === "") return NaN;
  return Number(v);
}

function isEn(lang) {
  return typeof lang === "string" && lang.toLowerCase().startsWith("en");
}

function fmt(n, lang, digits = null) {
  if (!Number.isFinite(n)) return "—";
  const s = digits == null ? String(n) : n.toFixed(digits);
  return isEn(lang) ? s : s.replace(".", ",");
}

export function profileLabel(profile, lang = "fr") {
  const row = PROFILE_LABEL[profile] || PROFILE_LABEL[DEFAULT_PROFILE];
  return isEn(lang) ? row.en : row.fr;
}

/** Budget rule §2.6 — the horizon never lies: nm = H × kn, pearls follow. */
function budgetFrom(hours, planningKn, sampleNm) {
  const h = isFinitePositive(hours) ? hours : PROFILE_TABLE.cruise.suivreLookaheadH;
  const kn = isFinitePositive(planningKn) ? planningKn : PROFILE_TABLE.cruise.planningKnDefault;
  const step = isFinitePositive(sampleNm) ? sampleNm : SHARED.routeSampleNm;
  const maxNm = Math.round(h * kn * 10) / 10;
  return {
    hours: h,
    planningKn: kn,
    sampleNm: step,
    maxNm,
    maxPearls: Math.max(1, Math.ceil(maxNm / step)),
  };
}

/** Read the boat from the polar. Berry defaults when the polar does not say. */
export function readBoat(polar) {
  const loaRaw = Number(polar?.loa_m ?? polar?.loaM);
  const draftRaw = Number(polar?.draft_m ?? polar?.draftM);
  const hasPolarSpeed = Boolean(polar?.vmg_summary && typeof polar.vmg_summary === "object");
  const kn = hasPolarSpeed ? expeditionBoatKnots(polar) : null;
  return {
    name: polar?.boat_name ?? polar?.name ?? DEFAULT_BOAT.name,
    expeditionId: polar?.expedition_id ?? null,
    loaM: isFinitePositive(loaRaw) ? loaRaw : DEFAULT_BOAT.loaM,
    draftM: isFinitePositive(draftRaw) ? draftRaw : DEFAULT_BOAT.draftM,
    planningKn: isFinitePositive(kn) ? Math.round(kn * 10) / 10 : null,
    source: {
      name: polar?.boat_name || polar?.name ? "polar" : null,
      loa: isFinitePositive(loaRaw) ? "polar" : "default",
      draft: isFinitePositive(draftRaw) ? "polar" : "default",
      planningKn: isFinitePositive(kn) ? "polar" : "profile",
    },
  };
}

/**
 * A small polar PROPOSES Coastal. Never a silent switch.
 * Only when L / draft were really read from the polar.
 */
export function suggestProfileForBoat(boat) {
  if (!boat) return null;
  const smallLoa = boat.source?.loa === "polar" && boat.loaM < SMALL_BOAT_LOA_M;
  const smallDraft = boat.source?.draft === "polar" && boat.draftM < SMALL_BOAT_DRAFT_M;
  if (!smallLoa && !smallDraft) return null;
  return { profile: "coastal", reason: smallLoa ? "small_loa" : "small_draft" };
}

function metaFor(id, profile) {
  const m = META[id] || {};
  const source = typeof m.source === "function" ? m.source(profile) : (m.source || "ui");
  const rule = typeof m.rule === "function" ? m.rule(profile) : (m.rule ?? null);
  return { unit: m.unit || "", source, rule, locked: Boolean(m.locked) };
}

/**
 * resolveOrders(saved, { polar, mode }) →
 *   { profile, mode, phrase, comfort, boat, knobs, values, thresholds, rainEnabled, rainReason, budget, suggest }
 * One `value` per id. Never two candidates.
 */
export function resolveOrders(saved, { polar = null, mode = "simulation" } = {}) {
  const profile = PROFILES.includes(saved?.profile) ? saved.profile : DEFAULT_PROFILE;
  const row = PROFILE_TABLE[profile];
  const boat = readBoat(polar);
  const planningKn = boat.planningKn ?? row.planningKnDefault;
  const budget = budgetFrom(row.suivreLookaheadH, planningKn, SHARED.routeSampleNm);
  const rainEnabled = mode === "suivre";
  const rainReason = rainEnabled ? null : "simulation_no_rain";

  const values = Object.freeze({
    ...LOCKED,
    ...SHARED,
    windShiftKt: row.windShiftKt,
    windShiftDeg: row.windShiftDeg,
    hsAlertM: row.hsAlertM,
    hsShiftM: row.hsShiftM,
    currentShiftKn: row.currentShiftKn,
    depthAlertM: row.depthAlertM,
    depthLabel: row.depthLabel,
    rainMmH: row.rainMmH,
    rain3hMm: row.rain3hMm,
    marinaRefugeNm: row.marinaRefugeNm,
    suivreLookaheadH: row.suivreLookaheadH,
    suivreLookaheadMaxNm: budget.maxNm,
    maxPearlsSuivre: budget.maxPearls,
    planningKn,
    groupNm: row.groupNm,
  });

  const thresholds = Object.keys(values)
    .filter((id) => id !== "depthLabel")
    .map((id) => {
      const m = metaFor(id, profile);
      const rain = RAIN_IDS.has(id);
      return {
        id,
        value: values[id],
        unit: m.unit,
        source: id === "planningKn" && boat.planningKn != null ? "usage" : m.source,
        rule: id === "planningKn"
          ? (boat.planningKn != null ? "polaire (VMG portant)" : `défaut ${PROFILE_LABEL[profile].fr} sans polaire`)
          : m.rule,
        locked: m.locked,
        enabled: rain ? rainEnabled : true,
        reason: rain && !rainEnabled ? rainReason : null,
      };
    });

  const suggest = profile === "coastal" ? null : suggestProfileForBoat(boat);

  return {
    profile,
    mode,
    phrase: row.phrase,
    comfort: COMFORT_DEFAULT,
    boat,
    knobs: { horizonH: row.suivreLookaheadH, comfort: COMFORT_DEFAULT },
    values,
    thresholds,
    rainEnabled,
    rainReason,
    budget,
    suggest,
  };
}

/** Flat values with Cruise defaults when no orders were passed. */
export function thresholdValues(orders) {
  const v = orders?.values;
  if (v && Number.isFinite(v.galeKt) && Number.isFinite(v.hsAlertM) && Number.isFinite(v.depthAlertM)) {
    return v;
  }
  return DEFAULT_ORDERS.values;
}

/** Budget §2.6 from resolved orders (Cruise if none). */
export function lookaheadBudget(orders) {
  if (orders?.budget && isFinitePositive(orders.budget.maxNm)) return orders.budget;
  return DEFAULT_ORDERS.budget;
}

function idsForEvent(type, orders, payload) {
  const p = payload || {};
  const simulation = orders.mode !== "suivre";
  switch (type) {
    case "wind-gale":
      return ["galeKt", "galeHoldKt", ...(simulation && p.galePct != null ? ["galePct"] : [])];
    case "wind-shift":
      return ["windShiftKt", "windShiftDeg"];
    case "current-shift":
      return ["currentShiftKn", ...(p.invert ? ["currentInvertDeg"] : [])];
    case "hs-shift":
      return p.alert === false ? ["hsShiftM"] : ["hsShiftM", "hsAlertM"];
    case "wx-alert": {
      const ids = [];
      const noDetail = p.gale == null && p.hs == null && p.rain == null;
      if (noDetail || p.gale) ids.push("galeKt");
      if (noDetail || p.hs != null) ids.push("hsAlertM");
      if (!simulation && (noDetail || p.rain)) ids.push("rainMmH", "rain3hMm");
      return ids;
    }
    case "marina-refuge":
      return simulation ? [] : ["rainMmH", "rain3hMm", "marinaRefugeNm"];
    case "depth-alert":
      return ["depthAlertM"];
    case "amp-ahead":
      return ["ampAheadMinNm", "alongAmpNm"];
    case "amp-enter":
      return ["iciRadiusNm"];
    default:
      return [];
  }
}

/**
 * thresholdsForEvent(type, orders, payload?) → `used`
 * Only the ids that made THIS event switch. One `value` per id.
 */
export function thresholdsForEvent(type, orders, payload = null) {
  const o = orders?.thresholds ? orders : DEFAULT_ORDERS;
  const byId = new Map(o.thresholds.map((t) => [t.id, t]));
  const seen = new Set();
  const used = [];
  for (const id of idsForEvent(type, o, payload)) {
    if (seen.has(id) || !byId.has(id)) continue;
    seen.add(id);
    const t = byId.get(id);
    used.push({ id, value: t.value, unit: t.unit, source: t.source, rule: t.rule });
  }
  return used;
}

/** Frozen snapshot attached to an event at detection time (§6.2). */
export function skipperSnapshot(type, orders, payload = null, lang = "fr") {
  const o = orders?.thresholds ? orders : DEFAULT_ORDERS;
  return {
    profile: o.profile,
    profile_phrase: isEn(lang) ? o.phrase.en : o.phrase.fr,
    comfort: o.comfort,
    boat: { name: o.boat.name, loaM: o.boat.loaM, draftM: o.boat.draftM },
    used: thresholdsForEvent(type, o, payload),
  };
}

/**
 * Living example from the current bag. Under two lines. FR / EN.
 * "Vent ici 18 kn — je me tais. À 34 kn je parle. Mer 1,4 m — sous 3,5 m."
 */
export function exampleLine(orders, sample = {}, lang = "fr") {
  const T = thresholdValues(orders);
  const en = isEn(lang);
  const parts = [];
  const tws = measure(sample?.tws);
  const hs = measure(sample?.hs);
  const depth = measure(sample?.depthM);
  if (Number.isFinite(tws)) {
    if (tws >= T.galeKt) {
      parts.push(en
        ? `Wind here ${fmt(tws, lang)} kn — gale, I speak.`
        : `Vent ici ${fmt(tws, lang)} kn — coup de vent, je parle.`);
    } else {
      parts.push(en
        ? `Wind here ${fmt(tws, lang)} kn — I stay quiet. At ${T.galeKt} kn I speak.`
        : `Vent ici ${fmt(tws, lang)} kn — je me tais. À ${T.galeKt} kn je parle.`);
    }
  }
  if (Number.isFinite(hs)) {
    if (hs >= T.hsAlertM) {
      parts.push(en
        ? `Sea ${fmt(hs, lang, 1)} m — above ${fmt(T.hsAlertM, lang, 1)} m, I speak.`
        : `Mer ${fmt(hs, lang, 1)} m — au-dessus de ${fmt(T.hsAlertM, lang, 1)} m, je parle.`);
    } else {
      parts.push(en
        ? `Sea ${fmt(hs, lang, 1)} m — under ${fmt(T.hsAlertM, lang, 1)} m.`
        : `Mer ${fmt(hs, lang, 1)} m — sous ${fmt(T.hsAlertM, lang, 1)} m.`);
    }
  }
  if (Number.isFinite(depth) && depth < T.depthAlertM) {
    const label = T.depthLabel === "talonnage"
      ? (en ? "grounding risk" : "risque de talonner")
      : (en ? "shelf ahead" : "on approche du plateau");
    parts.push(en
      ? `Depth ${fmt(depth, lang)} m — under ${T.depthAlertM} m, ${label}.`
      : `Fond ${fmt(depth, lang)} m — sous ${T.depthAlertM} m, ${label}.`);
  }
  if (!parts.length) {
    return en
      ? `No bag here yet. I speak at ${T.galeKt} kn, sea ${fmt(T.hsAlertM, lang, 1)} m, depth ${T.depthAlertM} m.`
      : `Pas encore de sac ici. Je parle à ${T.galeKt} kn, mer ${fmt(T.hsAlertM, lang, 1)} m, fond ${T.depthAlertM} m.`;
  }
  return parts.join(" ");
}

/** Cyan briefing line shown once after a change: "Ordres : croisière · Hs 3,5 m · fond 15 m". */
export function ordersLine(orders, lang = "fr") {
  const o = orders?.values ? orders : DEFAULT_ORDERS;
  const T = o.values;
  const en = isEn(lang);
  const label = profileLabel(o.profile, lang);
  return en
    ? `Orders: ${label} · Hs ${fmt(T.hsAlertM, lang, 1)} m · depth ${T.depthAlertM} m`
    : `Ordres : ${label} · Hs ${fmt(T.hsAlertM, lang, 1)} m · fond ${T.depthAlertM} m`;
}

/** Depth phrase per profile: shelf (Coastal / Cruise) or grounding (Ocean). */
export function depthPhrase(depthM, orders, lang = "fr") {
  const T = thresholdValues(orders);
  const en = isEn(lang);
  const d = fmt(depthM, lang);
  if (T.depthLabel === "talonnage") {
    return en
      ? `Grounding risk: ${d} m sounded, under ${T.depthAlertM} m.`
      : `Risque de talonner : ${d} m sondés, sous ${T.depthAlertM} m.`;
  }
  return en
    ? `Approaching the shelf: ${d} m sounded, under ${T.depthAlertM} m.`
    : `On approche du plateau : ${d} m sondés, sous ${T.depthAlertM} m.`;
}

/* ---- Persistence (tab + localStorage). v1 stores only the character. ---- */

export function readSavedOrders(storage) {
  try {
    const raw = storage?.getItem?.(STORAGE_KEY);
    if (!raw) return null;
    const obj = JSON.parse(raw);
    return PROFILES.includes(obj?.profile) ? { profile: obj.profile } : null;
  } catch {
    return null;
  }
}

export function writeSavedOrders(storage, saved) {
  try {
    const profile = PROFILES.includes(saved?.profile) ? saved.profile : DEFAULT_PROFILE;
    storage?.setItem?.(STORAGE_KEY, JSON.stringify({ profile }));
    return true;
  } catch {
    return false;
  }
}

export function clearSavedOrders(storage) {
  try {
    storage?.removeItem?.(STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}

/** Cruise = today's E1 constants. Simulation mode, no polar. */
export const DEFAULT_ORDERS = Object.freeze(resolveOrders(null, {}));
