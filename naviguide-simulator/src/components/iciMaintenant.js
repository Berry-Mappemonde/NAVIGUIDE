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

/**
 * Récit seulement en Suivre (lot RD6). Revue du plan en Suivre et Simulation
 * (horloge officielle, lot RD9), jamais en Tracer — un onglet marche ou n'existe pas.
 */
export function visibleIciTabs(mode) {
  return ICI_TABS.filter((tab) => {
    if (tab.id === "story") return mode === "follow";
    if (tab.id === "review") return mode === "follow" || mode === "simulation";
    return true;
  });
}

const EVENT_TYPE_LABEL = {
  fr: {
    amp: "Aire marine protégée",
    mpa: "Aire marine protégée",
    cyclone: "Cyclone",
    marina: "Marina",
    station: "Station croisée",
    science: "Station croisée",
  },
  en: {
    amp: "Marine protected area",
    mpa: "Marine protected area",
    cyclone: "Cyclone",
    marina: "Marina",
    station: "Station passed",
    science: "Station passed",
  },
};

const TYPE_ONLY_TITLES = new Set([
  "Aire marine protégée",
  "Marine protected area",
  "Cyclone",
  "Marina",
  "Station croisée",
  "Station passed",
  "Fiche science",
  "Science sheet",
]);

const NAMED_EVENT_KINDS = new Set(["amp", "mpa", "cyclone", "marina", "station", "science"]);

const NAMELESS_FACT = /traces de cyclone|cyclone tracks|saison cyclonique|cyclone season|ce mois-ci|this month/i;

function inferKindFromTitle(title) {
  const raw = String(title || "").trim().toLowerCase();
  if (/aire marine|marine protected/.test(raw)) return "amp";
  if (raw === "cyclone") return "cyclone";
  if (raw === "marina") return "marina";
  if (/station/.test(raw)) return "station";
  return "";
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
  const title = String(change.title || "").trim();
  if (!title) return "";
  if (title.includes(" — ")) return title;
  if (/^Ports d['’]entrée\s*:/i.test(title) || /^Ports? of entry\s*:/i.test(title)) return title;

  const rawKind = String(change.kind || "");
  const kind = NAMED_EVENT_KINDS.has(rawKind)
    ? rawKind
    : (rawKind === "alert-on" || rawKind === "alert-off" ? inferKindFromTitle(title) : rawKind);
  const labels = EVENT_TYPE_LABEL[lang] || EVENT_TYPE_LABEL.fr;
  const type = labels[kind] || (TYPE_ONLY_TITLES.has(title) ? title : "");
  if (!type) return title;

  let name = TYPE_ONLY_TITLES.has(title) ? "" : title;
  if (name && name.toLowerCase() === type.toLowerCase()) name = "";
  if (!name) name = nameFromJournalFact(change.fact);
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
