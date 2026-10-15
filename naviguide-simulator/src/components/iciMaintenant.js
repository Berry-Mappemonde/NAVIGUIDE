import { reviewLeg } from "../engine/planReview.js";
import { momentAtOrBefore } from "../hooks/useMomentJournal.js";

const MONTHS_SHORT = {
  fr: ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."],
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
};

export const ICI_TABS = [
  { id: "now", testId: "ici-tab-now", labelKey: "iciNowTab" },
  { id: "story", testId: "ici-tab-story", labelKey: "iciStoryTab" },
  { id: "journal", testId: "ici-tab-journal", labelKey: "iciJournalTab" },
  { id: "review", testId: "ici-tab-review", labelKey: "planReviewTitle" },
];

const TRACER_TAB_IDS = ["review", "story"];
const FOLLOW_CUSTOM_TAB_IDS = ["review", "journal", "story"];

/** Tracer = simulation (Berry) ou drawn (brouillon / ma route). */
export function isTracerIciMode(mode) {
  return mode === "simulation" || mode === "drawn";
}

export function isFollowCustomIci(mode, { routeSource } = {}) {
  return mode === "follow" && routeSource === "custom";
}

/**
 * Suivre × Berry : Maintenant · Récit · Journal · Revue du plan.
 * Suivre × ma route (DM8C, option A) : Revue du plan · Journal · Récit ;
 * Maintenant masqué (pas de « maintenant » sur une horloge que je choisis).
 * Tracer : Revue du plan · Récit seulement (lot DM9).
 * Les onglets masqués restent dans ICI_TABS : hidden, pas supprimés.
 */
export function visibleIciTabs(mode, { routeSource } = {}) {
  if (isTracerIciMode(mode)) {
    return TRACER_TAB_IDS.map((id) => ICI_TABS.find((tab) => tab.id === id)).filter(Boolean);
  }
  if (isFollowCustomIci(mode, { routeSource })) {
    return FOLLOW_CUSTOM_TAB_IDS.map((id) => ICI_TABS.find((tab) => tab.id === id)).filter(Boolean);
  }
  return ICI_TABS;
}

/**
 * Onglets masqués mais encore dans le DOM (hidden), pour les specs qui
 * cliquent par testid sans les montrer à l'écran.
 */
export function hiddenIciTabs(mode, { routeSource } = {}) {
  if (isTracerIciMode(mode)) {
    return ICI_TABS.filter((tab) => tab.id === "now" || tab.id === "journal");
  }
  if (isFollowCustomIci(mode, { routeSource })) {
    return ICI_TABS.filter((tab) => tab.id === "now");
  }
  return [];
}

/** Onglet ouvert à l'entrée du mode : Revue en Tracer et Suivre × ma route. */
export function defaultIciTab(mode, { routeSource } = {}) {
  if (isTracerIciMode(mode) || isFollowCustomIci(mode, { routeSource })) return "review";
  return "now";
}

/**
 * En Tracer, la Revue du plan sert aussi le contenu de Maintenant
 * (briefing, jambe, escale, Demander conseil) : les onglets sont masqués,
 * pas les surfaces (anti-régression visuelle).
 * En Suivre × ma route : Maintenant n'est pas servi (option A).
 */
export function servesNowContent(view, mode, { routeSource } = {}) {
  if (isFollowCustomIci(mode, { routeSource })) return false;
  if (view === "now") return true;
  return isTracerIciMode(mode) && view === "review";
}

const EVENT_TYPE_LABEL = {
  fr: {
    amp: "Aire marine protégée",
    mpa: "Aire marine protégée",
    cyclone: "Cyclone",
    marina: "Marina",
    port: "Port",
    station: "Station croisée",
    science: "Station croisée",
    sci: "Station croisée",
    stop: "Escale",
    escale: "Escale",
    entry: "Formalités d’entrée",
    poe: "Ports d’entrée",
    zee: "ZEE",
  },
  en: {
    amp: "Marine protected area",
    mpa: "Marine protected area",
    cyclone: "Cyclone",
    marina: "Marina",
    port: "Port",
    station: "Station passed",
    science: "Station passed",
    sci: "Station passed",
    stop: "Stopover",
    escale: "Stopover",
    entry: "Entry formalities",
    poe: "Ports of entry",
    zee: "EEZ",
  },
};

const TYPE_ONLY_TITLES = new Set([
  "Aire marine protégée",
  "Marine protected area",
  "Cyclone",
  "Marina",
  "Port",
  "Station croisée",
  "Station passed",
  "Fiche science",
  "Science sheet",
  "Formalités d'entrée",
  "Formalités d’entrée",
  "Entry formalities",
  "Escale",
  "Stopover",
]);

const NAMED_EVENT_KINDS = new Set([
  "amp", "mpa", "cyclone", "marina", "port", "station", "science", "sci", "stop", "escale", "entry", "poe", "zee",
]);

const TITLE_EN = {
  "Formalités d'entrée": "Entry formalities",
  "Formalités d’entrée": "Entry formalities",
  "Aire marine protégée": "Marine protected area",
  "Station croisée": "Station passed",
  "Escale": "Stopover",
};

const NAMELESS_FACT = /traces de cyclone|cyclone tracks|saison cyclonique|cyclone season|ce mois-ci|this month/i;

function inferKindFromTitle(title) {
  const raw = String(title || "").trim().toLowerCase();
  if (/aire marine|marine protected/.test(raw)) return "amp";
  if (/formalit|entry formalit|ports? d['’]entr|ports? of entry/.test(raw)) return "entry";
  if (/^escale\b|^stopover\b/.test(raw)) return "stop";
  if (raw === "cyclone") return "cyclone";
  if (raw === "marina") return "marina";
  if (/station/.test(raw)) return "station";
  return "";
}

export function localizeStoredTitle(title, lang) {
  const raw = String(title || "").trim();
  if (!raw || lang !== "en") return raw;
  if (TITLE_EN[raw]) return TITLE_EN[raw];
  const escale = /^(?:Escale|Stopover)\s+(.+)$/i.exec(raw);
  if (escale) return `Stopover ${escale[1]}`;
  return raw;
}

function stripTypePrefix(name, type) {
  const n = String(name || "").trim();
  if (!n) return "";
  const exact = [type, "Escale", "Stopover", "Station croisée", "Station passed",
    "Formalités d'entrée", "Formalités d’entrée", "Entry formalities",
    "Aire marine protégée", "Marine protected area"];
  if (exact.some((p) => p && n.toLowerCase() === String(p).toLowerCase())) return "";
  const escale = /^(?:Escale|Stopover)\s+(.+)$/i.exec(n);
  return escale ? escale[1].trim() : n;
}

/**
 * The official journal is built in French. Live GET /ici/moment follows `lang`.
 * Prefer the live moment for alerts / here / around so EN is not a FR leftover.
 */
export function displayIciFrame(moment, journalEntries, mode) {
  const journalHit = mode === "follow" && moment
    ? momentAtOrBefore(journalEntries, moment?.t)
    : null;
  const timeline = journalHit || moment;
  return {
    shown: timeline,
    alerts: (moment?.alerts?.length ? moment.alerts : timeline?.alerts) || [],
    here: moment?.here?.sentences?.length ? moment.here : (timeline?.here || moment?.here),
    around: moment?.around?.length ? moment.around : (timeline?.around || []),
    sources: moment?.sources?.length ? moment.sources : (timeline?.sources || []),
  };
}

function yearIn(text) {
  const m = String(text || "").match(/\b((?:19|20)\d{2})\b/);
  return m ? m[1] : "";
}

/** Nom porté par le fait serveur — jamais inventé, jamais une phrase générique. */
export function nameFromJournalFact(fact) {
  const s = String(fact || "").trim();
  if (!s || NAMELESS_FACT.test(s)) return "";
  const beforeNm = s.match(/^(.+?)\s+\([\d.,]+\s*nm\)/i);
  if (beforeNm) return beforeNm[1].trim();
  const namedYear = s.match(/^(?:Cyclone\s+)?([^.(]{2,60}?)\s+\((?:19|20)\d{2}\)\s*$/i);
  if (namedYear) return s.replace(/^Cyclone\s+/i, "").trim();
  const beforeColon = s.match(/^([^:]{2,60})\s*:/);
  if (beforeColon && !/^(vent|wind|hs|reste|left|remaining)/i.test(beforeColon[1].trim())) {
    return beforeColon[1].trim();
  }
  if (!/[.!?]$/.test(s) && s.length <= 60 && !/^\d/.test(s) && !/\bkn\b|\bHs\b/i.test(s)) {
    return s;
  }
  return "";
}

export function visibleAlerts(alerts, dismissed) {
  const hide = dismissed instanceof Set ? dismissed : new Set(dismissed || []);
  return (Array.isArray(alerts) ? alerts : []).filter((a) => a && a.id && !hide.has(a.id));
}

export function dismissAlert(dismissed, id) {
  const next = new Set(dismissed instanceof Set ? dismissed : dismissed || []);
  if (id) next.add(id);
  return next;
}

export function etaDayLabel(iso, lang = "fr") {
  const stamp = Date.parse(iso || "");
  if (!Number.isFinite(stamp)) return "";
  const d = new Date(stamp);
  const months = MONTHS_SHORT[lang] || MONTHS_SHORT.fr;
  return `${d.getUTCDate()} ${months[d.getUTCMonth()]}`;
}

export function formatNumber(value, lang, digits) {
  if (!Number.isFinite(Number(value))) return "";
  const loc = lang === "en" ? "en-US" : "fr-FR";
  if (digits == null) {
    return Math.round(Number(value)).toLocaleString(loc);
  }
  return Number(value).toLocaleString(loc, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/**
 * Revue du plan de MA route : une jambe entre chaque couple de points
 * (milles, jours). Pas de fourchette inventée — seulement si l'horloge
 * porte déjà des dates. Jamais le fixture Berry.
 */
export function legsFromClockMarks(clock, lang = "fr") {
  const marks = (clock?.marks || []).filter((m) => m && String(m.name || "").trim());
  if (marks.length < 2) return [];
  const legs = [];
  for (let i = 0; i < marks.length - 1; i += 1) {
    const a = marks[i];
    const b = marks[i + 1];
    const fromNm = Number(a.filmNm ?? a.nm) || 0;
    const toNm = Number(b.filmNm ?? b.nm) || 0;
    const nm = Math.max(0, toNm - fromNm);
    const hours = Number(b.tHours) - Number(a.tHours);
    const days = Number.isFinite(hours) && hours > 0 ? hours / 24 : 0;
    const depart = Date.parse(a.iso || "");
    const month = Number.isFinite(depart) ? new Date(depart).getUTCMonth() + 1 : null;
    legs.push(reviewLeg({
      from: a.name,
      to: b.name,
      legNm: Math.round(nm) || 0,
      daysAtSea: days > 0 ? Math.max(1, Math.round(days)) : 0,
      departIso: a.iso || "",
      arriveIso: b.iso || "",
      month,
      fromNm,
      toNm,
    }, null, lang));
  }
  return legs;
}

export function formatLegLine(leg, t, lang = "fr") {
  if (!leg || typeof leg !== "object") return "";
  const bits = [];
  if (leg.from && leg.to) bits.push(`${leg.from} → ${leg.to}`);
  if (Number.isFinite(Number(leg.day))) bits.push(t("iciLegDay", { n: String(Math.trunc(Number(leg.day))) }));
  if (Number.isFinite(Number(leg.kn))) bits.push(t("iciLegKn", { kn: formatNumber(leg.kn, lang, 1) }));
  if (Number.isFinite(Number(leg.remainingNm))) {
    bits.push(t("iciLegRemaining", { nm: formatNumber(leg.remainingNm, lang) }));
  }
  const p10 = etaDayLabel(leg.eta?.p10, lang);
  const p90 = etaDayLabel(leg.eta?.p90, lang);
  if (p10 && p90) bits.push(t("etaRange", { p10, p90 }));
  return bits.join(" · ");
}

export function regimeColor(regime) {
  if (regime === "hindcast") return "#2dd4bf";
  if (regime === "forecast") return "#38bdf8";
  if (regime === "climatology") return "#c084fc";
  return null;
}

export function formatJournalDate(iso, lang = "fr") {
  const day = etaDayLabel(iso, lang);
  if (!day) return "";
  const stamp = Date.parse(iso || "");
  if (!Number.isFinite(stamp)) return day;
  const d = new Date(stamp);
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${day} ${hh}:${mm}`;
}

export function formatJournalPos(pos, lang = "fr") {
  const lat = Number(pos?.lat);
  const lon = Number(pos?.lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return "";
  return `${formatNumber(lat, lang, 1)} · ${formatNumber(lon, lang, 1)}`;
}

export function journalChangeLabel(entry, lang = "fr") {
  const changes = (Array.isArray(entry?.changes) ? entry.changes : [])
    .filter((c) => c && c.title)
    .sort((a, b) => (Number(b.score) || 0) - (Number(a.score) || 0));
  const change = changes[0];
  if (!change) return "";
  const stored = String(change.title || "").trim();
  if (!stored) return "";
  const title = localizeStoredTitle(stored, lang);
  if (stored.includes(" — ")) {
    const [left, ...rest] = stored.split(" — ");
    const right = rest.join(" — ");
    const loc = localizeStoredTitle(left, lang);
    return right ? `${loc} — ${right}` : loc;
  }
  if (/^Ports d['’]entrée\s*:/i.test(stored)) {
    return lang === "en"
      ? stored.replace(/^Ports d['’]entrée\s*:/i, "Ports of entry:")
      : stored;
  }
  if (/^Ports? of entry\s*:/i.test(stored)) return stored;

  const rawKind = String(change.kind || "");
  const inferred = inferKindFromTitle(stored) || inferKindFromTitle(title);
  const kind = NAMED_EVENT_KINDS.has(rawKind)
    ? rawKind
    : (rawKind === "alert-on" || rawKind === "alert-off" || !rawKind ? inferred : rawKind);
  const labels = EVENT_TYPE_LABEL[lang] || EVENT_TYPE_LABEL.fr;
  const type = labels[kind] || (TYPE_ONLY_TITLES.has(stored) || TYPE_ONLY_TITLES.has(title) ? title : "");
  if (!type) return title;

  let name = (TYPE_ONLY_TITLES.has(stored) || TYPE_ONLY_TITLES.has(title)) ? "" : title;
  name = stripTypePrefix(name, type);
  if (name && name.toLowerCase() === type.toLowerCase()) name = "";
  if (!name) name = nameFromJournalFact(change.fact);
  name = stripTypePrefix(name, type);
  if (name && name.toLowerCase() === type.toLowerCase()) name = "";

  if (kind === "cyclone") {
    if (NAMELESS_FACT.test(String(change.fact || ""))) name = nameFromJournalFact(change.fact);
    const year = yearIn(change.fact) || yearIn(name);
    if (name && year && !name.includes(year)) name = `${name} (${year})`;
  }

  if (type && name) return `${type} — ${name}`;
  return type || title;
}

export function formatJournalLine(entry, lang = "fr") {
  return [formatJournalDate(entry?.t, lang), formatJournalPos(entry?.pos, lang), journalChangeLabel(entry, lang)]
    .filter(Boolean)
    .join(" · ");
}

export function seekJournalEntry(onSeek, entry) {
  const t = entry?.t;
  if (typeof onSeek === "function" && t) onSeek(t);
}
