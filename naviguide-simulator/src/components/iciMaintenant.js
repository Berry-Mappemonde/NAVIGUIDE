const MONTHS_SHORT = {
  fr: ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."],
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
};

export const ICI_TABS = [
  { id: "now", testId: "ici-tab-now", labelKey: "iciNowTab" },
  { id: "story", testId: "ici-tab-story", labelKey: "iciStoryTab" },
  { id: "journal", testId: "ici-tab-journal", labelKey: "iciJournalTab" },
];

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

export function journalChangeLabel(entry) {
  const changes = (Array.isArray(entry?.changes) ? entry.changes : [])
    .filter((c) => c && c.title)
    .sort((a, b) => (Number(b.score) || 0) - (Number(a.score) || 0));
  return changes[0] ? String(changes[0].title) : "";
}

export function formatJournalLine(entry, lang = "fr") {
  return [formatJournalDate(entry?.t, lang), formatJournalPos(entry?.pos, lang), journalChangeLabel(entry)]
    .filter(Boolean)
    .join(" · ");
}

export function seekJournalEntry(onSeek, entry) {
  const t = entry?.t;
  if (typeof onSeek === "function" && t) onSeek(t);
}
