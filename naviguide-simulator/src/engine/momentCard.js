/**
 * Carte du moment — ce que le visiteur voit pendant que le bateau avance.
 *
 * Deux voies, une file chacune (arbitrage du porteur, 19 sept. 2026) :
 *  - NOW (« à bord, maintenant ») : sécurité et décisions — coup de vent,
 *    repli, haut-fond, cyclone, entrée / sortie de ZEE, port d’entrée, météo
 *    qui change le plan, escale (arrivée / départ), **climatologie** et
 *    **balisage**. Une carte à la fois ; les alertes passent devant ;
 *    fermable ; en lecture une nouvelle carte remplace l’ancienne après
 *    quelques secondes, et une carte laissée loin derrière la tête de
 *    lecture n’est plus montrée.
 *  - FREE (« pendant ce temps, autour du bateau ») : information — fiches
 *    science, projets, image satellite, **câbles**, **aires marines
 *    protégées**, digests groupés, événements « later » atteints par la tête
 *    de lecture. Visible seulement quand aucune carte NOW n’est posée ; tourne,
 *    boucle sur les fiches du sac.
 *
 * Fonctions pures (jamais de mutation de l’état précédent : StrictMode peut
 * rejouer un updater). Pas de HTTP, pas de timer : le hook passe `nowMs`.
 * Le texte vient de `phraseForEvent` (récit LLM quand il est prêt, phrase
 * locale sinon) ou des mêmes phrases que le briefing — jamais un chiffre
 * inventé ici.
 */

import { phraseForEvent, satelliteSentence, climatologySentence } from "./iciBriefing.js";
import { placeLabel } from "./briefingLinks.js";
import { formatJournalEntry } from "./journalFormat.js";

export const LANE_NOW = "now";
export const LANE_FREE = "free";

/** Information kinds: never a NOW card, whatever the judge said. */
const INFO_TYPES = new Set([
  "science-hit",
  "project-nearby",
  "satellite-scene",
  "anchorage-ahead",
  "group",
  "amp-enter",
  "amp-ahead",
  "cable-alert",
]);

/** Bag kinds that are decisions for the skipper (NOW lane). */
const NOW_BAG_KINDS = new Set(["aton", "climatology"]);

/** Durées d’affichage (ms). Simulation en pause / Suivre sans lecture : pas d’expiration NOW. */
export const TTL = Object.freeze({
  nowSuivreMs: 90_000,
  nowPlayingMs: 14_000,
  /** In playback a newer NOW card may replace the shown one after this. */
  nowReplaceMs: 5_000,
  freeMs: 9_000,
  freeSuivreMs: 14_000,
  freePausedMs: Infinity,
});

export const QUEUE_MAX = Object.freeze({ now: 6, free: 12 });

/** Simulation: an event left this far behind the playhead is history, not a card. */
export const STALE_CARD_NM = 80;

/** Cap the per-kind information items taken from one bag (same caps as the briefing). */
const BAG_CAPS = Object.freeze({
  marina: 3,
  capitainerie: 2,
  wpi: 2,
  anchorage: 3,
  science: 3,
  project: 3,
  amp: 2,
  aton: 1,
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

/** Simulation only: the card's place on the film is far behind the boat. */
export function isStaleCard(card, { filmCum = null, mode = "simulation" } = {}) {
  if (mode === "suivre") return false;
  if (!card || !Number.isFinite(card.filmCum) || !Number.isFinite(filmCum)) return false;
  return filmCum - card.filmCum > STALE_CARD_NM;
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
  amp: ["Aire marine protégée", "Marine protected area"],
  aton: ["Balisage", "Aid to navigation"],
  satellite: ["Image satellite", "Satellite image"],
  climatology: ["Climatologie", "Climatology"],
  cable: ["Câble sous-marin", "Submarine cable"],
  escale: ["Escale", "Stopover"],
  climo: ["Changement de régime", "Regime change"],
  sci: ["Station croisée", "Station passed"],
});

/** Journal kinds that become a moment card (lot E + F2). */
export const JOURNAL_CARD_KINDS = new Set(["stop", "zee", "amp", "poe", "wx", "note", "climo", "sci"]);

const JOURNAL_TITLE = {
  fr: { stop: "Escale", zee: "ZEE", amp: "Aire marine protégée", poe: "Port d’entrée", wx: "Météo au bateau", note: "Mot du skipper", climo: "Changement de régime", sci: "Station croisée" },
  en: { stop: "Stopover", zee: "EEZ", amp: "Marine protected area", poe: "Port of entry", wx: "Weather at the boat", note: "Skipper's note", climo: "Regime change", sci: "Station passed" },
};

function journalDayLabel(iso, lang) {
  const t = Date.parse(iso || "");
  if (!Number.isFinite(t)) return "";
  return new Date(t).toLocaleDateString(lang === "en" ? "en-GB" : "fr-FR", { day: "numeric", month: "long", timeZone: "UTC" });
}

function journalTitleOf(entry, lang) {
  const words = JOURNAL_TITLE[isEn(lang) ? "en" : "fr"];
  if (entry?.title && typeof entry.title === "object") {
    const picked = isEn(lang) ? (entry.title.en || entry.title.fr) : (entry.title.fr || entry.title.en);
    if (picked) return picked;
  }
  if (typeof entry?.title === "string" && entry.title) return entry.title;
  return words[entry?.kind] || entry?.kind || "";
}

function journalEntityKind(entry) {
  if (entry?.entity?.kind) return entry.entity.kind;
  if (entry?.kind === "poe") return "poe";
  if (entry?.kind === "amp") return "amp";
  if (entry?.kind === "sci") return "science";
  if (entry?.kind === "stop") return "escale";
  return "place";
}

/** A moment card (NOW lane) from a journal line — the text the journal already formats. */
export function cardFromJournalEntry(entry, lang = "fr") {
  if (!entry || !JOURNAL_CARD_KINDS.has(entry.kind)) return null;
  const f = formatJournalEntry(entry, lang);
  const when = journalDayLabel(entry.t, lang);
  const title = journalTitleOf(entry, lang);
  const hasPos = Number.isFinite(entry.lat) && Number.isFinite(entry.lon);
  const given = entry.entity && typeof entry.entity === "object" ? entry.entity : null;
  const lat = Number.isFinite(given?.lat) ? given.lat : entry.lat;
  const lon = Number.isFinite(given?.lon) ? given.lon : entry.lon;
  return {
    key: `replay:${entry.id || `${entry.kind}:${entry.t}`}`,
    lane: LANE_NOW,
    origin: "journal",
    kind: entry.kind,
    type: `replay-${entry.kind}`,
    severity: entry.kind === "wx" ? "alert" : "info",
    title: `${title}${when ? ` · ${when}` : ""}`,
    text: f.text,
    facts: entry.facts || null,
    entity: hasPos || (Number.isFinite(lat) && Number.isFinite(lon))
      ? {
        id: `replay:${entry.kind}:${entry.name || given?.name || entry.t}`,
        kind: journalEntityKind(entry),
        name: given?.name || entry.name || title,
        rawName: given?.name || entry.name || "",
        lat: Number.isFinite(lat) ? lat : entry.lat,
        lon: Number.isFinite(lon) ? lon : entry.lon,
        nm: Number.isFinite(given?.nm) ? given.nm : (Number.isFinite(entry.nm) ? entry.nm : 0),
        url: given?.url || entry.url || entry.visitUrl || null,
        source: given?.source || entry.basis || null,
      }
      : null,
    whenNm: 0,
    at: entry.t,
  };
}

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
    lane: NOW_BAG_KINDS.has(kind) ? LANE_NOW : LANE_FREE,
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
 * Cards in one `ici()` bag: what is around the boat, told one card at a time.
 * Keys are stable per place so a marina met again 3 nm later is not repeated.
 * Balisage and climatologie go to the NOW lane (decisions), the rest to FREE.
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
  push("amp", bag.amp);
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

  const cables = bag.emodnet?.cables;
  if (cables?.nearby === true) {
    const at = bag.at || {};
    out.push({
      key: `bag:cable:${Number(at.lat).toFixed(1)}:${Number(at.lon).toFixed(1)}`,
      lane: LANE_FREE,
      origin: "bag",
      kind: "cable",
      type: "cable-alert",
      severity: "info",
      title: kindWord("cable", lang),
      text: isEn(lang)
        ? "A submarine cable passes here (EMODnet, observation)."
        : "Un câble sous-marin passe ici (EMODnet, observation).",
      entity: null,
    });
  }

  const c = bag.climatology;
  if (c && (c.point || c.wind) && c.month != null) {
    const zone = c.zone || c.point?.zone || c.point?.cell || `${Math.round(Number(bag.at?.lat) / 5) * 5}:${Math.round(Number(bag.at?.lon) / 5) * 5}`;
    out.push({
      key: `bag:climatology:${c.month}:${zone}`,
      lane: LANE_NOW,
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

/**
 * Escale card: written when the leg changes (the boat left a stopover).
 * `leg` = { fromStop, toStop, holdDays, legNm, etaIso } from the film clock.
 */
export function escaleCard(leg, lang = "fr", { filmCum = null } = {}) {
  if (!leg?.fromStop) return null;
  const en = isEn(lang);
  const from = String(leg.fromStop);
  const to = leg.toStop ? String(leg.toStop) : null;
  const quay = Number.isFinite(leg.holdDays) && leg.holdDays > 0
    ? (en ? ` — ${leg.holdDays} day${leg.holdDays > 1 ? "s" : ""} in port` : ` — ${leg.holdDays} jour${leg.holdDays > 1 ? "s" : ""} à quai`)
    : "";
  const nm = Number.isFinite(leg.legNm) && leg.legNm > 0.5
    ? ` (${Math.round(leg.legNm).toLocaleString(en ? "en-GB" : "fr-FR")} nm)`
    : "";
  const eta = leg.etaLabel ? (en ? `, expected on ${leg.etaLabel}` : `, arrivée prévue le ${leg.etaLabel}`) : "";
  const text = to
    ? (en
      ? `Stopover ${from}${quay}. Departure: heading for ${to}${nm}${eta}.`
      : `Escale ${from}${quay}. Départ : cap sur ${to}${nm}${eta}.`)
    : (en ? `Stopover ${from}${quay}.` : `Escale ${from}${quay}.`);
  return {
    key: `ev:escale:${from}→${to || ""}`,
    lane: LANE_NOW,
    origin: "event",
    kind: "escale",
    type: "escale-out",
    severity: "watch",
    title: kindWord("escale", lang),
    text,
    entity: Number.isFinite(leg.lat) && Number.isFinite(leg.lon)
      ? { id: `escale:${from}`, kind: "wpi", name: from, rawName: from, lat: leg.lat, lon: leg.lon, nm: 0, url: null, source: null }
      : null,
    filmCum,
    whenNm: 0,
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
 * One step. Ingests the judged ledger + the current bag (+ an escale card
 * when the leg changed), expires cards, and promotes the next one. Returns
 * the same object when nothing changed so React can skip the render.
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
  leg = null,
} = {}) {
  let state = prev || emptyMoments();
  let changed = false;
  // Pure: never mutate `prev.seen` — React (StrictMode) may run an updater
  // twice with the same previous state and keep the second result.
  const seen = new Set(state.seen);
  let nowQueue = state.nowQueue;
  let freeQueue = state.freeQueue;
  let freeLoop = state.freeLoop || [];
  let now = state.now;
  let free = state.free;

  if (legId !== state.legId) {
    // New leg: the ledger restarted; queued cards of the old leg are stale.
    const previousLeg = state.legId;
    state = { ...state, legId };
    nowQueue = [];
    freeQueue = [];
    freeLoop = [];
    free = null;
    changed = true;
    // The boat just left a stopover: one NOW card says so (not on the first leg).
    if (previousLeg != null && leg?.fromStop) {
      const card = escaleCard(leg, lang, { filmCum });
      if (card && !seen.has(card.key) && !state.dismissed.has(card.key)) {
        seen.add(card.key);
        nowQueue = pushCapped(nowQueue, card, QUEUE_MAX.now);
      }
    }
  }

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
    if (isStaleCard(card, { filmCum, mode })) continue; // history, not a card
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

  // 2. Bag → cards (balisage / climatologie → NOW, the rest → FREE).
  for (const card of infoItemsFromBag(bag, lang)) {
    if (seen.has(card.key)) continue;
    seen.add(card.key);
    if (card.lane === LANE_NOW) nowQueue = pushCapped(nowQueue, { ...card, filmCum }, QUEUE_MAX.now);
    else freeQueue = pushCapped(freeQueue, card, QUEUE_MAX.free);
    changed = true;
  }

  // 3. Drop queued cards left behind by the playhead (Simulation).
  const beforeNow = nowQueue.length;
  nowQueue = nowQueue.filter((c) => !isStaleCard(c, { filmCum, mode }));
  const beforeFree = freeQueue.length;
  freeQueue = freeQueue.filter((c) => !isStaleCard(c, { filmCum, mode }));
  if (nowQueue.length !== beforeNow || freeQueue.length !== beforeFree) changed = true;

  // 4. Expire / replace the NOW card, then pop the next one.
  const nowTtl = nowTtlMs({ mode, playing });
  if (now && Number.isFinite(nowTtl) && nowMs - now.shownAt >= nowTtl) {
    now = null;
    changed = true;
  }
  if (now && playing && mode !== "suivre" && nowQueue.length && nowMs - now.shownAt >= TTL.nowReplaceMs) {
    // In playback the boat moves fast: a newer decision replaces the shown one.
    now = null;
    changed = true;
  }
  if (now && isStaleCard(now, { filmCum, mode })) {
    now = null;
    changed = true;
  }
  if (!now && nowQueue.length) {
    const sorted = sortNowQueue(nowQueue);
    now = { ...sorted[0], shownAt: nowMs };
    nowQueue = sorted.slice(1);
    changed = true;
  }

  // 5. FREE only breathes when nothing urgent is posted.
  if (!now) {
    const freeTtl = freeTtlMs({ mode, playing });
    if (free && Number.isFinite(freeTtl) && nowMs - free.shownAt >= freeTtl) {
      if (free.origin === "bag" && !freeLoop.some((c) => c.key === free.key)) freeLoop = [...freeLoop, free];
      free = null;
      changed = true;
    }
    if (!free && !freeQueue.length && freeLoop.length >= 2) {
      // Nothing new: loop on what is around the boat (bag cards only).
      freeQueue = freeLoop.map((c) => ({ ...c, loop: true }));
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
    freeQueue = freeLoop.map((c) => ({ ...c, loop: true }));
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
