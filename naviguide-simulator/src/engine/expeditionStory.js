/**
 * Le récit de la traversée — de Saint-Maur à la position d’aujourd’hui.
 *
 * Écrit à partir de ce qui est su : l’horloge officielle (dates d’escale,
 * jours à quai), la position live, la jambe en cours, et le journal de bord
 * serveur (vent du GRIB au bateau) quand il est là. Zéro LLM, aucun chiffre
 * inventé : quand une donnée manque, la phrase manque.
 *
 * Retourne des paragraphes (FR / EN) ; le bouton « Écouter » les lit dans
 * l’ordre, la sidebar les affiche en Suivre.
 */

import { getCardinalDirection } from "../utils/getCardinalDirection.js";

const MONTHS = {
  fr: ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
  en: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
};

function isEn(lang) {
  return String(lang || "").toLowerCase().startsWith("en");
}

function ms(iso) {
  const t = Date.parse(iso ?? "");
  return Number.isFinite(t) ? t : null;
}

/** "24 mai" / "24 May" ; with year when asked. */
export function dayMonth(iso, lang = "fr", { year = false } = {}) {
  const t = ms(iso);
  if (t == null) return "";
  const d = new Date(t);
  const m = MONTHS[isEn(lang) ? "en" : "fr"][d.getUTCMonth()];
  const day = d.getUTCDate();
  const y = year ? ` ${d.getUTCFullYear()}` : "";
  if (isEn(lang)) return `${day} ${m}${y}`;
  return `${day === 1 ? "1er" : day} ${m}${y}`;
}

function nmLabel(nm, lang) {
  const v = Math.round(Number(nm) || 0);
  return isEn(lang) ? `${v.toLocaleString("en-GB")} nm` : `${v.toLocaleString("fr-FR")} nm`;
}

function days(hours) {
  return Math.max(0, Math.round((Number(hours) || 0) / 24));
}

function joinList(parts, lang) {
  if (!parts.length) return "";
  if (parts.length === 1) return parts[0];
  return `${parts.slice(0, -1).join(", ")}${isEn(lang) ? " and " : " et "}${parts[parts.length - 1]}`;
}

function shortName(name) {
  // "Fort-de-France (Martinique)" stays; "Saint-Maur (Berry, Indre)" → "Saint-Maur".
  return String(name || "").replace(/\s*\(Berry, Indre\)\s*/, "").trim();
}

function compass(deg, lang) {
  const d = Number(deg);
  if (!Number.isFinite(d)) return "";
  const card = getCardinalDirection(d);
  return isEn(lang) ? card.replace(/O/g, "W") : card;
}

/** Stopovers with a date, in route order, deduplicated by (name, filmNm). */
export function datedMarks(marks) {
  const out = [];
  for (const m of marks || []) {
    if (!m?.name || ms(m.iso) == null) continue;
    const film = Number(m.filmNm ?? m.nm) || 0;
    if (out.some((x) => x.name === m.name && Math.abs(x.filmNm - film) < 0.6)) continue;
    out.push({ name: m.name, iso: m.iso, filmNm: film, holdHours: Number(m.holdHours) || 0 });
  }
  return out.sort((a, b) => a.filmNm - b.filmNm);
}

/** Latest GRIB entry of the journal (wind at the boat), if any. */
function latestGrib(journal) {
  const entries = journal?.latest || journal?.entries || [];
  let best = null;
  for (const e of entries) {
    if (e?.kind !== "grib") continue;
    if (!best || ms(e.t) > ms(best.t)) best = e;
  }
  return best;
}

/**
 * @param {object} p
 * @param {object} p.clock      official clock (t0, marks[], vertices[])
 * @param {Array}  p.marks      legend marks (name, filmNm, iso, holdHours)
 * @param {object} p.live       official live sample (filmNm, sailNm, iso, seaHours, atQuay, status, windKnots, dirFromDeg, kind, model)
 * @param {object} p.leg        hud leg (fromStop, toStop, remainingNm, etaHours, vehicle)
 * @param {object} p.journal    GET /voyage/official/journal payload (optional)
 * @param {Date|number|string} p.now
 * @param {string} p.lang
 * @returns {string[]} paragraphs
 */
export function expeditionStory({ clock, marks, live, leg, journal = null, now = Date.now(), lang = "fr" } = {}) {
  const en = isEn(lang);
  const nowMs = now instanceof Date ? now.getTime() : (typeof now === "number" ? now : ms(now));
  const t0 = ms(clock?.t0);
  const stops = datedMarks(marks?.length ? marks : clock?.marks);
  if (t0 == null && !stops.length) return [];
  const out = [];

  const start = stops[0];
  const sea = stops.find((s, i) => i > 0 && /rochelle/i.test(s.name)) || stops[1] || null;
  const departIso = start?.iso || clock?.t0;

  // 1. Le départ.
  if (nowMs != null && t0 != null && nowMs < t0) {
    out.push(en
      ? `The Berry-Mappemonde expedition leaves ${shortName(start?.name || "Saint-Maur")} on ${dayMonth(departIso, lang, { year: true })}${sea ? ` and puts to sea at ${shortName(sea.name)}` : ""}.`
      : `L’expédition Berry-Mappemonde quitte ${shortName(start?.name || "Saint-Maur")} le ${dayMonth(departIso, lang, { year: true })}${sea ? ` et prend la mer à ${shortName(sea.name)}` : ""}.`);
    return out;
  }
  // The sea date is written only when it falls on another day than the departure.
  const seaDay = sea && dayMonth(sea.iso, lang) !== dayMonth(departIso, lang) ? dayMonth(sea.iso, lang) : "";
  out.push(en
    ? `The Berry-Mappemonde expedition left ${shortName(start?.name || "Saint-Maur")} on ${dayMonth(departIso, lang, { year: true })}${sea ? `, and the boat put to sea at ${shortName(sea.name)}${seaDay ? ` on ${seaDay}` : ""}` : ""}.`
    : `L’expédition Berry-Mappemonde a quitté ${shortName(start?.name || "Saint-Maur")} le ${dayMonth(departIso, lang, { year: true })}${sea ? `, et le bateau a pris la mer à ${shortName(sea.name)}${seaDay ? ` le ${seaDay}` : ""}` : ""}.`);

  // 2. Les escales franchies (arrivée avant maintenant), hors départ / mise à l’eau.
  const boatFilm = Number(live?.filmNm);
  const passed = stops.filter((s, i) => {
    if (i === 0 || s === sea) return false;
    if (nowMs != null && ms(s.iso) > nowMs) return false;
    if (Number.isFinite(boatFilm) && s.filmNm > boatFilm + 0.6) return false;
    return true;
  });
  if (passed.length) {
    const list = joinList(passed.map((s) => `${shortName(s.name)} (${dayMonth(s.iso, lang)})`), lang);
    const quay = passed.reduce((acc, s) => acc + days(s.holdHours), 0);
    out.push(en
      ? `Since then, ${passed.length} stopover${passed.length > 1 ? "s" : ""}: ${list}${quay ? ` — ${quay} day${quay > 1 ? "s" : ""} in port in all` : ""}.`
      : `Depuis, ${passed.length} escale${passed.length > 1 ? "s" : ""} : ${list}${quay ? ` — ${quay} jour${quay > 1 ? "s" : ""} à quai en tout` : ""}.`);
  }

  // 3. Aujourd’hui.
  if (live && Number.isFinite(boatFilm)) {
    const dayAtSea = days(live.seaHours);
    const elapsed = t0 != null && nowMs != null ? Math.max(0, Math.floor((nowMs - t0) / 86_400_000)) : null;
    const when = elapsed != null
      ? (en ? `Today, day ${elapsed}${dayAtSea ? ` (${dayAtSea} at sea)` : ""}` : `Aujourd’hui, jour ${elapsed}${dayAtSea ? ` (${dayAtSea} de mer)` : ""}`)
      : (en ? "Today" : "Aujourd’hui");
    const dist = nmLabel(live.sailNm ?? live.filmNm, lang);
    const to = leg?.toStop ? shortName(leg.toStop) : null;
    const nextMark = to ? stops.find((s) => s.name === leg.toStop) : null;
    const eta = nextMark ? dayMonth(nextMark.iso, lang) : null;
    const left = Number(leg?.remainingNm);
    if (live.status === "arrived") {
      out.push(en
        ? `${when}: the boat has arrived — ${dist} logged since the start.`
        : `${when} : le bateau est arrivé — ${dist} parcourus depuis le départ.`);
    } else if (live.atQuay && leg?.fromStop) {
      const here = shortName(leg.fromStop);
      out.push(en
        ? `${when}: the boat is in port at ${here}, ${dist} from the start${to ? `; next leg to ${to}${eta ? `, expected on ${eta}` : ""}` : ""}.`
        : `${when} : le bateau est à quai à ${here}, à ${dist} du départ${to ? ` ; prochaine jambe vers ${to}${eta ? `, arrivée prévue le ${eta}` : ""}` : ""}.`);
    } else if (live.vehicle === "plane") {
      out.push(en
        ? `${when}: the crew is in the air${to ? `, heading for ${to}` : ""} — the boat stays where it is.`
        : `${when} : l’équipage est dans les airs${to ? `, vers ${to}` : ""} — le bateau ne bouge pas.`);
    } else {
      const tail = to
        ? (en
          ? `, heading for ${to}${Number.isFinite(left) && left > 0.5 ? ` (${nmLabel(left, lang)} to go)` : ""}${eta ? `, expected on ${eta}` : ""}`
          : `, cap sur ${to}${Number.isFinite(left) && left > 0.5 ? ` (encore ${nmLabel(left, lang)})` : ""}${eta ? `, arrivée prévue le ${eta}` : ""}`)
        : "";
      out.push(en
        ? `${when}: the boat is ${dist} from the start${tail}.`
        : `${when} : le bateau est à ${dist} du départ${tail}.`);
    }
  }

  // 4. Le vent au bateau (GRIB live, sinon dernière entrée du journal).
  const wind = live?.kind === "forecast" && Number.isFinite(live.windKnots)
    ? { kn: live.windKnots, from: live.dirFromDeg, model: live.model, when: null }
    : null;
  const g = !wind ? latestGrib(journal) : null;
  const gw = g && Number.isFinite(g.windKnots ?? g.wind?.windKnots)
    ? { kn: g.windKnots ?? g.wind.windKnots, from: g.dirFromDeg ?? g.wind?.dirFromDeg, model: g.model || g.wind?.model, when: g.t }
    : null;
  const w = wind || gw;
  if (w) {
    const from = compass(w.from, lang);
    const kn = Math.round(Number(w.kn));
    out.push(en
      ? `${w.when ? `On ${dayMonth(w.when, lang)}, at the boat` : "At the boat"}: wind ${kn} kn${from ? ` from the ${from}` : ""}${w.model ? ` (${w.model} forecast)` : ""}.`
      : `${w.when ? `Le ${dayMonth(w.when, lang)}, au bateau` : "Au bateau"} : vent ${kn} kn${from ? ` de ${from}` : ""}${w.model ? ` (prévision ${w.model})` : ""}.`);
  }

  return out;
}

export function expeditionStoryText(params) {
  return expeditionStory(params).join("\n\n");
}
