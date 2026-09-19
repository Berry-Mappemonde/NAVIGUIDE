/**
 * Carte du moment — ce que le visiteur voit pendant que le bateau avance.
 *
 * Deux surfaces, une file chacune :
 *  - NOW (« à bord, maintenant ») : sécurité et décisions — coup de vent,
 *    repli, haut-fond, câble, cyclone, formalités (ZEE, port d’entrée, AMP),
 *    météo qui change le plan. Affichée dès que le juge dit « now » ; une
 *    carte à la fois ; les alertes passent devant.
 *  - FREE (« pendant ce temps, autour du bateau ») : information — fiches
 *    science, projets, marinas, balisage, image satellite, climatologie,
 *    digests groupés, événements « later » atteints par la tête de lecture.
 *    Visible seulement quand aucune carte NOW n’est posée ; tourne.
 *
 * Fonctions pures. Pas de HTTP, pas de timer : le hook passe `nowMs`.
 * Le texte vient de `phraseForEvent` (récit LLM quand il est prêt, phrase
 * locale sinon) ou des mêmes phrases que le briefing — jamais un chiffre
 * inventé ici.
 */

import { phraseForEvent, satelliteSentence, climatologySentence } from "./iciBriefing.js";
import { placeLabel } from "./briefingLinks.js";

export const LANE_NOW = "now";
export const LANE_FREE = "free";

/** Information kinds: never a NOW card, whatever the judge said. */
const INFO_TYPES = new Set([
  "science-hit",
  "project-nearby",
  "aton-nearby",
  "satellite-scene",
  "anchorage-ahead",
  "group",
]);

/** Durées d’affichage (ms). Simulation en pause / Suivre sans lecture : pas d’expiration NOW. */
export const TTL = Object.freeze({
  nowSuivreMs: 90_000,
  nowPlayingMs: 14_000,
  freeMs: 9_000,
  freeSuivreMs: 14_000,
  freePausedMs: Infinity,
});

export const QUEUE_MAX = Object.freeze({ now: 6, free: 12 });

/** Cap the per-kind information items taken from one bag (same caps as the briefing). */
const BAG_CAPS = Object.freeze({
  marina: 3,
  capitainerie: 2,
  wpi: 2,
  anchorage: 3,
  science: 3,
  project: 3,
  aton: 3,
});

function isEn(lang) {
  return String(lang || "").toLowerCase().startsWith("en");
}

function num(n, lang) {
  if (!Number.isFinite(Number(n))) return "";
  const v = Math.round(Number(n) * 10) / 10;
  return isEn(lang) ? String(v) : String(v).replace(".", ",");
}

/**
 * Which lane an event belongs to. `null` = not shown (hidden by the judge,
 * or a « later » event the playhead has not reached yet).
 */
export function classifyMoment(ev, { filmCum = null, mode = "simulation" } = {}) {
  if (!ev || ev.judge === "hide") return null;
  if (INFO_TYPES.has(ev.type)) return reached(ev, filmCum, mode) ? LANE_FREE : null;
  if (ev.promoted) return LANE_FREE;
  if (ev.judge === "now") return LANE_NOW;
  if (ev.judge === "later") return reached(ev, filmCum, mode) ? LANE_FREE : null;
  return null;
}

function reached(ev, filmCum, mode) {
  if (mode === "suivre") return true;
  if (!Number.isFinite(ev.filmCum) || !Number.isFinite(filmCum)) return true;
  return filmCum + 0.5 >= ev.filmCum;
}

/** Place the card can point at on the map (same shape as a briefing entity). */
export function entityForEvent(ev) {
  const p = ev?.payload || {};
  const pick = (kind, item) => {
    if (!item || !Number.isFinite(Number(item.lat)) || !Number.isFinite(Number(item.lon))) return null;
    return {
      id: `${kind}:${item.site_id ?? item.id ?? item.name ?? ev.id}`,
      kind,
      name: placeLabel(kind, item),
      rawName: String(item.name || ""),
      lat: Number(item.lat),
      lon: Number(item.lon),
      nm: Number.isFinite(Number(item.nm)) ? Number(item.nm) : null,
      url: item.url || item.visit_url || item.manager_url || null,
      source: item.source || null,
    };
  };
  return pick("marina", p.harbour)
    || pick("poe", p.poe)
    || pick("amp", p.amp)
    || pick("zee", p.zee)
    || null;
}

const KIND_WORDS = Object.freeze({
  marina: ["Marina", "Marina"],
  capitainerie: ["Capitainerie", "Harbour office"],
  wpi: ["Port de commerce (WPI)", "Commercial port (WPI)"],
  anchorage: ["Mouillage", "Anchorage"],
  science: ["Fiche science", "Science sheet"],
  project: ["Projet", "Project"],
  aton: ["Balisage", "Aid to navigation"],
  satellite: ["Image satellite", "Satellite image"],
  climatology: ["Climatologie", "Climatology"],
});

export function kindWord(kind, lang) {
  const row = KIND_WORDS[kind];
  return row ? row[isEn(lang) ? 1 : 0] : String(kind || "");
}

function placeItem(kind, item, lang) {
  if (!item || !item.name) return null;
  const name = placeLabel(kind, item, lang);
  const nm = Number.isFinite(Number(item.nm)) ? Number(item.nm) : null;
  const en = isEn(lang);
  const where = nm != null ? (en ? ` at ${num(nm, lang)} nm` : ` à ${num(nm, lang)} nm`) : "";
  const source = item.source ? ` (${item.source})` : "";
  const key = `bag:${kind}:${item.site_id ?? item.id ?? item.osm_id ?? `${item.name}:${Number(item.lat).toFixed(2)}:${Number(item.lon).toFixed(2)}`}`;
  return {
    key,
    lane: LANE_FREE,
    origin: "bag",
    kind,
    type: kind,
    severity: "info",
    title: kindWord(kind, lang),
    text: `${name}${where}${kind === "science" ? source : ""}.`,
    entity: {
      id: key,
      kind,
      name,
      rawName: String(item.name),
      lat: Number.isFinite(Number(item.lat)) ? Number(item.lat) : null,
      lon: Number.isFinite(Number(item.lon)) ? Number(item.lon) : null,
      nm,
      url: item.url || item.website || (kind === "amp" ? item.visit_url || item.manager_url : null) || null,
      source: item.source || null,
    },
  };
}

/**
 * Information items in one `ici()` bag: what is around the boat, told one
 * card at a time when nothing urgent is up. Keys are stable per place so a
 * marina met again 3 nm later is not repeated.
 */
export function infoItemsFromBag(bag, lang = "fr") {
  if (!bag) return [];
  const out = [];
  const push = (kind, items) => {
    (items || []).slice(0, BAG_CAPS[kind] ?? 3).forEach((it) => {
      const card = placeItem(kind, it, lang);
      if (card) out.push(card);
    });
  };
  push("marina", bag.nearby?.marinas);
  push("capitainerie", bag.nearby?.capitaineries);
  push("wpi", bag.nearby?.wpi);
  push("anchorage", bag.nearby?.anchorages);
  push("science", bag.science?.nearby);
  push("project", bag.projects);
  push("aton", bag.aton?.nearby);

  const scene = bag.satellites?.scene || bag.satellites?.scenes?.[0];
  if (scene?.id) {
    out.push({
      key: `bag:satellite:${scene.id}`,
      lane: LANE_FREE,
      origin: "bag",
      kind: "satellite",
      type: "satellite-scene",
      severity: "info",
      title: kindWord("satellite", lang),
      text: satelliteSentence(bag, lang),
      entity: null,
    });
  }

  const c = bag.climatology;
  if (c && (c.point || c.wind) && c.month != null) {
    const zone = c.zone || c.point?.zone || c.point?.cell || `${Math.round(Number(bag.at?.lat) / 5) * 5}:${Math.round(Number(bag.at?.lon) / 5) * 5}`;
    out.push({
      key: `bag:climatology:${c.month}:${zone}`,
      lane: LANE_FREE,
      origin: "bag",
      kind: "climatology",
      type: "climatology",
      severity: "info",
      title: kindWord("climatology", lang),
      text: climatologySentence(bag, lang),
      entity: null,
    });
  }
  return out.filter((card) => card.text);
}

function eventKey(ev) {
  return `ev:${ev.stableKey || ev.id}`;
}

export function cardFromEvent(ev, lang = "fr") {
  const lane = ev.promoted || INFO_TYPES.has(ev.type) || ev.judge !== "now" ? LANE_FREE : LANE_NOW;
  return {
    key: eventKey(ev),
    lane,
    origin: "event",
    kind: ev.type,
    type: ev.type,
    severity: ev.severity || "info",
    title: null,
    text: phraseForEvent(ev, lang),
    entity: entityForEvent(ev),
    whenNm: ev.whenNm ?? null,
    filmCum: ev.filmCum ?? null,
    storyStatus: ev.story?.status || null,
    judgeReason: ev.judgeReason || null,
  };
}

export function emptyMoments() {
  return {
    now: null,
    nowQueue: [],
    free: null,
    freeQueue: [],
    // Bag cards already shown on this leg: when the queue runs dry, the block
    // loops on them (what is around the boat stays readable), events never repeat.
    freeLoop: [],
    seen: new Set(),
    dismissed: new Set(),
    legId: null,
  };
}

function sortNowQueue(queue) {
  // Alerts first, then in arrival order (stable).
  return queue
    .map((c, i) => [c, i])
    .sort((a, b) => {
      const sa = a[0].severity === "alert" ? 0 : 1;
      const sb = b[0].severity === "alert" ? 0 : 1;
      return sa - sb || a[1] - b[1];
    })
    .map(([c]) => c);
}

function pushCapped(queue, card, max) {
  const next = [...queue, card];
  while (next.length > max) {
    const idx = next.findIndex((c) => c.severity !== "alert");
    next.splice(idx >= 0 ? idx : 0, 1);
  }
  return next;
}

export function nowTtlMs({ mode, playing }) {
  if (mode === "suivre") return TTL.nowSuivreMs;
  return playing ? TTL.nowPlayingMs : Infinity;
}

export function freeTtlMs({ mode, playing }) {
  if (mode === "suivre") return TTL.freeSuivreMs;
  return playing ? TTL.freeMs : TTL.freePausedMs;
}

function sameText(a, b) {
  return a?.text === b?.text && a?.storyStatus === b?.storyStatus;
}

/**
 * One step. Ingests the judged ledger + the current bag, expires cards, and
 * promotes the next one. Returns the same object when nothing changed so
 * React can skip the render.
 */
export function advanceMoments(prev, {
  events = [],
  bag = null,
  filmCum = null,
  nowMs = Date.now(),
  playing = false,
  mode = "simulation",
  lang = "fr",
  legId = null,
} = {}) {
  let state = prev || emptyMoments();
  let changed = false;

  if (legId !== state.legId) {
    // New leg: the ledger restarted; queued cards of the old leg are stale.
    state = { ...state, legId, nowQueue: [], freeQueue: [], free: null, freeLoop: [] };
    changed = true;
  }

  // Pure: never mutate `prev.seen` — React (StrictMode) may run an updater
  // twice with the same previous state and keep the second result.
  const seen = new Set(state.seen);
  let nowQueue = state.nowQueue;
  let freeQueue = state.freeQueue;
  let freeLoop = state.freeLoop || [];
  let now = state.now;
  let free = state.free;

  // 1. Events → lanes.
  const eventCards = new Map();
  for (const ev of events || []) {
    const lane = classifyMoment(ev, { filmCum, mode });
    if (!lane) continue;
    const card = cardFromEvent(ev, lang);
    if (!card.text) continue;
    eventCards.set(card.key, card);
    if (seen.has(card.key)) continue;
    if (state.dismissed.has(card.key)) continue;
    seen.add(card.key);
    changed = true;
    if (lane === LANE_NOW) nowQueue = pushCapped(nowQueue, card, QUEUE_MAX.now);
    else freeQueue = pushCapped(freeQueue, card, QUEUE_MAX.free);
  }

  // Story text arrives after the card: refresh what is displayed / queued.
  const refresh = (card) => {
    if (!card || card.origin !== "event") return card;
    const fresh = eventCards.get(card.key);
    if (!fresh || sameText(fresh, card)) return card;
    changed = true;
    return { ...card, text: fresh.text, storyStatus: fresh.storyStatus };
  };
  now = refresh(now);
  free = refresh(free);
  nowQueue = nowQueue.map(refresh);
  freeQueue = freeQueue.map(refresh);

  // 2. Bag → information.
  for (const card of infoItemsFromBag(bag, lang)) {
    if (seen.has(card.key)) continue;
    seen.add(card.key);
    freeQueue = pushCapped(freeQueue, card, QUEUE_MAX.free);
    changed = true;
  }

  // 3. Expire the NOW card, then pop the next one.
  const nowTtl = nowTtlMs({ mode, playing });
  if (now && Number.isFinite(nowTtl) && nowMs - now.shownAt >= nowTtl) {
    now = null;
    changed = true;
  }
  if (!now && nowQueue.length) {
    const sorted = sortNowQueue(nowQueue);
    now = { ...sorted[0], shownAt: nowMs };
    nowQueue = sorted.slice(1);
    changed = true;
  }

  // 4. FREE only breathes when nothing urgent is posted.
  if (!now) {
    const freeTtl = freeTtlMs({ mode, playing });
    if (free && Number.isFinite(freeTtl) && nowMs - free.shownAt >= freeTtl) {
      if (free.origin === "bag" && !freeLoop.some((c) => c.key === free.key)) freeLoop = [...freeLoop, free];
      free = null;
      changed = true;
    }
    if (!free && !freeQueue.length && freeLoop.length >= 2) {
      // Nothing new: loop on what is around the boat (bag cards only).
      freeQueue = freeLoop;
      freeLoop = [];
      changed = true;
    }
    if (!free && freeQueue.length) {
      free = { ...freeQueue[0], shownAt: nowMs };
      freeQueue = freeQueue.slice(1);
      changed = true;
    }
  }

  if (!changed) return prev || state;
  return { ...state, now, nowQueue, free, freeQueue, freeLoop, seen };
}

/** The visitor closes the NOW card: it never comes back; the next one shows. */
export function dismissNow(state, nowMs = Date.now()) {
  if (!state?.now) return state;
  const dismissed = new Set(state.dismissed);
  dismissed.add(state.now.key);
  const sorted = sortNowQueue(state.nowQueue);
  const next = sorted[0] ? { ...sorted[0], shownAt: nowMs } : null;
  return { ...state, now: next, nowQueue: sorted.slice(1), dismissed };
}

/** « Suivant » on the FREE block: the shown bag card joins the loop, the next one shows. */
export function nextFree(state, nowMs = Date.now()) {
  if (!state) return state;
  let freeLoop = state.freeLoop || [];
  if (state.free?.origin === "bag" && !freeLoop.some((c) => c.key === state.free.key)) {
    freeLoop = [...freeLoop, state.free];
  }
  let freeQueue = state.freeQueue;
  if (!freeQueue.length && freeLoop.length >= 2) {
    freeQueue = freeLoop;
    freeLoop = [];
  }
  const next = freeQueue[0] ? { ...freeQueue[0], shownAt: nowMs } : null;
  if (!next && !state.free) return state;
  return { ...state, free: next, freeQueue: freeQueue.slice(1), freeLoop };
}

/** Text read aloud for a card: title (info) + body. */
export function cardSpeech(card) {
  if (!card) return "";
  return [card.title, card.text].filter(Boolean).join(". ");
}
