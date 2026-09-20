/**
 * Le récit de la traversée — de Saint-Maur à la position d’aujourd’hui,
 * raconté dans l’ordre (revue du porteur, 19 sept. 2026) :
 *
 *   « L’expédition a quitté Saint-Maur le 15 mai… Le 15 mai, le bateau a pris
 *   la mer à La Rochelle vers Ajaccio : 1 820 nm en 9 jours ; vent moyen
 *   12 kn au bateau. Arrivée le 24 mai, 3 jours à quai. Puis départ le 27 mai
 *   vers Fort-de-France … Aujourd’hui … »
 *
 * Écrit à partir de ce qui est su : l’horloge officielle (dates d’escale,
 * jours à quai, milles), la position live, la jambe en cours, et le journal
 * de bord serveur (vent du GRIB au bateau, escales franchies, mots du
 * skipper) quand il est là. Zéro LLM, aucun chiffre inventé : quand une
 * donnée manque, la phrase manque.
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

function daysBetween(isoA, isoB) {
  const a = ms(isoA);
  const b = ms(isoB);
  if (a == null || b == null) return null;
  return Math.max(0, Math.round((b - a) / 86_400_000));
}

function joinList(parts, lang) {
  if (!parts.length) return "";
  if (parts.length === 1) return parts[0];
  return `${parts.slice(0, -1).join(", ")}${isEn(lang) ? " and " : " et "}${parts[parts.length - 1]}`;
}

function dayWord(n, lang) {
  if (isEn(lang)) return `${n} day${n > 1 ? "s" : ""}`;
  return `${n} jour${n > 1 ? "s" : ""}`;
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
    out.push({
      name: m.name,
      iso: m.iso,
      filmNm: film,
      nm: Number.isFinite(Number(m.nm)) ? Number(m.nm) : film,
      holdHours: Number(m.holdHours) || 0,
    });
  }
  return out.sort((a, b) => a.filmNm - b.filmNm);
}

/** Departure from a stopover = arrival + days in port. */
function departureIso(stop) {
  const t = ms(stop?.iso);
  if (t == null) return null;
  return new Date(t + (Number(stop.holdHours) || 0) * 3_600_000).toISOString();
}

/** `events` = the whole voyage minus positions (server summary); `latest` = the recent tail. Deduped by id. */
function journalEntries(journal) {
  const all = [...(journal?.events || []), ...(journal?.latest || journal?.entries || [])];
  const seen = new Set();
  return all.filter((e) => {
    const id = e?.id || `${e?.kind}:${e?.t}`;
    if (seen.has(id)) return false;
    seen.add(id);
    return true;
  });
}

/** GRIB entries of the journal between two instants: mean / max wind at the boat. */
function windBetween(journal, fromIso, toIso) {
  const a = ms(fromIso);
  const b = ms(toIso);
  if (a == null || b == null) return null;
  const winds = [];
  for (const e of journalEntries(journal)) {
    if (e?.kind !== "grib") continue;
    const t = ms(e.t);
    if (t == null || t < a || t > b) continue;
    const kn = Number(e.windKnots ?? e.wind?.windKnots);
    if (Number.isFinite(kn)) winds.push(kn);
  }
  if (!winds.length) return null;
  return {
    mean: Math.round(winds.reduce((s, x) => s + x, 0) / winds.length),
    max: Math.round(Math.max(...winds)),
    n: winds.length,
  };
}

/** Route events of the journal (v2: ZEE crossings, MPA within reach) between two instants, in order. */
function routeEventsBetween(journal, fromIso, toIso) {
  const a = ms(fromIso);
  const b = ms(toIso);
  if (a == null || b == null) return [];
  return journalEntries(journal)
    .filter((e) => ((e?.kind === "zee" || e?.kind === "amp" || e?.kind === "poe") && e.name) || e?.kind === "wx")
    .filter((e) => { const t = ms(e.t); return t != null && t >= a && t <= b; })
    .sort((x, y) => ms(x.t) - ms(y.t));
}

/** « Entre-temps : entrée dans la ZEE espagnole le 17 mai, haute mer le 20 mai ; AMP à portée : Pertuis Charentais. » */
function routeEventsSentence(events, lang) {
  if (!events.length) return "";
  const en = isEn(lang);
  // Entries only, each EEZ once (a re-entry after a short high-seas gap is not a new fact).
  const seenZee = new Set();
  const zee = events.filter((e) => {
    if (e.kind !== "zee" || e.event !== "enter") return false;
    const key = e.mrgid ?? e.name;
    if (seenZee.has(key)) return false;
    seenZee.add(key);
    return true;
  });
  const amp = events.filter((e) => e.kind === "amp");
  const bits = [];
  if (zee.length) {
    const parts = zee.slice(0, 6).map((e) => (en ? `${e.name} on ${dayMonth(e.t, lang)}` : `${e.name} le ${dayMonth(e.t, lang)}`));
    const more = zee.length > 6 ? (en ? ` and ${zee.length - 6} more` : ` et ${zee.length - 6} autres`) : "";
    bits.push(en ? `entered: ${parts.join(", ")}${more}` : `entré dans : ${parts.join(", ")}${more}`);
  }
  if (amp.length) {
    const names = amp.slice(0, 3).map((e) => e.name);
    const more = amp.length > 3 ? (en ? ` and ${amp.length - 3} more` : ` et ${amp.length - 3} autres`) : "";
    bits.push(en
      ? `marine protected area${amp.length > 1 ? "s" : ""} within reach: ${joinList(names, lang)}${more}`
      : `aire${amp.length > 1 ? "s" : ""} marine${amp.length > 1 ? "s" : ""} protégée${amp.length > 1 ? "s" : ""} à portée : ${joinList(names, lang)}${more}`);
  }
  // Ports of entry passed (lot A), each once.
  const seenPoe = new Set();
  const poe = events.filter((e) => {
    if (e.kind !== "poe") return false;
    const key = e.poeId ?? e.name;
    if (seenPoe.has(key)) return false;
    seenPoe.add(key);
    return true;
  });
  if (poe.length) {
    const names = poe.slice(0, 4).map((e) => e.name);
    const more = poe.length > 4 ? (en ? ` and ${poe.length - 4} more` : ` et ${poe.length - 4} autres`) : "";
    bits.push(en
      ? `port${poe.length > 1 ? "s" : ""} of entry passed: ${joinList(names, lang)}${more}`
      : `port${poe.length > 1 ? "s" : ""} d’entrée passé${poe.length > 1 ? "s" : ""} : ${joinList(names, lang)}${more}`);
  }
  const head = bits.length ? `${en ? "Meanwhile" : "Entre-temps"} — ${bits.join(" ; ")}.` : "";
  // Remarkable weather at the boat (lot A): derived from journaled GRIBs, cited with its numbers.
  const wx = events.filter((e) => e.kind === "wx" && Number.isFinite(Number(e.windKnots ?? e.hs)));
  let wxSentence = "";
  if (wx.length) {
    const parts = wx.slice(0, 3).map((e) => {
      const kn = Number.isFinite(e.windKnots) ? `${Math.round(e.windKnots)} kn` : "";
      const hs = Number.isFinite(e.hs) ? `Hs ${Number(e.hs).toLocaleString(en ? "en-GB" : "fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} m` : "";
      const what = e.event === "sea" ? (en ? "heavy sea" : "mer forte") : (en ? "gale" : "coup de vent");
      const nums = [kn, hs].filter(Boolean).join(", ");
      return `${what} ${en ? "on" : "le"} ${dayMonth(e.t, lang)}${nums ? ` (${nums})` : ""}`;
    });
    const more = wx.length > 3 ? (en ? ` and ${wx.length - 3} more` : ` et ${wx.length - 3} autres`) : "";
    wxSentence = en ? `Weather at the boat: ${joinList(parts, lang)}${more} (GFS).` : `Météo au bateau : ${joinList(parts, lang)}${more} (GFS).`;
  }
  return [head, wxSentence].filter(Boolean).join(" ");
}

/** Skipper notes of the journal between two instants (the human voice, verbatim). */
function notesBetween(journal, fromIso, toIso, max = 2) {
  const a = ms(fromIso);
  const b = ms(toIso);
  if (a == null || b == null) return [];
  return journalEntries(journal)
    .filter((e) => e?.kind === "note" && typeof e.text === "string" && e.text.trim())
    .filter((e) => { const t = ms(e.t); return t != null && t >= a && t <= b; })
    .slice(0, max)
    .map((e) => e.text.trim());
}

/** Latest GRIB entry of the journal (wind at the boat), if any. */
function latestGrib(journal) {
  let best = null;
  for (const e of journalEntries(journal)) {
    if (e?.kind !== "grib") continue;
    if (!best || ms(e.t) > ms(best.t)) best = e;
  }
  return best;
}

/** One passed leg, told in one paragraph: departure, crossing, arrival, port. */
function legParagraph(from, to, { journal, lang, sea }) {
  const en = isEn(lang);
  const dep = from === sea ? from.iso : departureIso(from);
  const legNm = Math.max(0, (Number(to.nm) || 0) - (Number(from.nm) || 0));
  const dur = daysBetween(dep, to.iso);
  const wind = windBetween(journal, dep, to.iso);
  const notes = notesBetween(journal, dep, to.iso);
  const crossings = routeEventsSentence(routeEventsBetween(journal, dep, to.iso), lang);
  const bits = [];
  const head = from === sea
    ? (en
      ? `On ${dayMonth(dep, lang)}, the boat put to sea at ${shortName(from.name)}, bound for ${shortName(to.name)}`
      : `Le ${dayMonth(dep, lang)}, le bateau a pris la mer à ${shortName(from.name)}, vers ${shortName(to.name)}`)
    : (en
      ? `Then on ${dayMonth(dep, lang)}, departure for ${shortName(to.name)}`
      : `Puis, le ${dayMonth(dep, lang)}, départ vers ${shortName(to.name)}`);
  const facts = [];
  if (legNm > 0.5) facts.push(nmLabel(legNm, lang));
  if (dur != null && dur > 0) facts.push(en ? `in ${dayWord(dur, lang)}` : `en ${dayWord(dur, lang)}`);
  bits.push(`${head}${facts.length ? ` : ${facts.join(en ? " " : " ")}` : ""}.`);
  if (crossings) bits.push(crossings);
  if (wind) {
    bits.push(en
      ? `Wind at the boat: ${wind.mean} kn on average, ${wind.max} kn at most (GFS, ${wind.n} readings).`
      : `Vent au bateau : ${wind.mean} kn en moyenne, ${wind.max} kn au plus fort (GFS, ${wind.n} relevés).`);
  }
  for (const n of notes) bits.push(en ? `The skipper wrote: « ${n} »` : `Le skipper a noté : « ${n} »`);
  const quay = days(to.holdHours);
  bits.push(en
    ? `Arrival at ${shortName(to.name)} on ${dayMonth(to.iso, lang)}${quay ? `, ${dayWord(quay, lang)} in port` : ""}.`
    : `Arrivée à ${shortName(to.name)} le ${dayMonth(to.iso, lang)}${quay ? `, ${dayWord(quay, lang)} à quai` : ""}.`);
  return bits.join(" ");
}

/**
 * @param {object} p
 * @param {object} p.clock      official clock (t0, marks[], vertices[])
 * @param {Array}  p.marks      legend marks (name, nm, filmNm, iso, holdHours)
 * @param {object} p.live       official live sample (filmNm, sailNm, iso, seaHours, atQuay, status, windKnots, dirFromDeg, kind, model)
 * @param {object} p.leg        hud leg (fromStop, toStop, remainingNm, etaHours, vehicle)
 * @param {object} p.journal    GET /voyage/official/journal payload (optional)
 * @param {Date|number|string} p.now
 * @param {string} p.lang
 * @returns {string[]} paragraphs, chronological
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
  out.push(en
    ? `The Berry-Mappemonde expedition left ${shortName(start?.name || "Saint-Maur")} on ${dayMonth(departIso, lang, { year: true })}.`
    : `L’expédition Berry-Mappemonde a quitté ${shortName(start?.name || "Saint-Maur")} le ${dayMonth(departIso, lang, { year: true })}.`);

  // 2. Chaque jambe franchie, dans l’ordre : départ, traversée, arrivée, quai.
  const boatFilm = Number(live?.filmNm);
  const seaIdx = sea ? stops.indexOf(sea) : 0;
  const passed = [];
  for (let i = Math.max(seaIdx, 0); i < stops.length - 1; i++) {
    const from = stops[i];
    const to = stops[i + 1];
    if (nowMs != null && ms(to.iso) > nowMs) break;
    if (Number.isFinite(boatFilm) && to.filmNm > boatFilm + 0.6) break;
    passed.push([from, to]);
  }
  for (const [from, to] of passed) out.push(legParagraph(from, to, { journal, lang, sea }));

  // 3. La jambe en cours, puis aujourd’hui.
  if (live && Number.isFinite(boatFilm)) {
    const current = passed.length ? passed[passed.length - 1][1] : sea;
    const to = leg?.toStop ? shortName(leg.toStop) : null;
    const nextMark = to ? stops.find((s) => s.name === leg.toStop) : null;
    const eta = nextMark ? dayMonth(nextMark.iso, lang) : null;
    const left = Number(leg?.remainingNm);
    const dayAtSea = days(live.seaHours);
    const elapsed = t0 != null && nowMs != null ? Math.max(0, Math.floor((nowMs - t0) / 86_400_000)) : null;
    const when = elapsed != null
      ? (en ? `Today, day ${elapsed}${dayAtSea ? ` (${dayAtSea} at sea)` : ""}` : `Aujourd’hui, jour ${elapsed}${dayAtSea ? ` (${dayAtSea} de mer)` : ""}`)
      : (en ? "Today" : "Aujourd’hui");
    const dist = nmLabel(live.sailNm ?? live.filmNm, lang);

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
      const dep = current && current !== sea ? departureIso(current) : current?.iso;
      const since = current && dep
        ? (en
          ? `Since ${dayMonth(dep, lang)}, under way from ${shortName(current.name)}${to ? ` to ${to}` : ""}`
          : `Depuis le ${dayMonth(dep, lang)}, en route de ${shortName(current.name)}${to ? ` vers ${to}` : ""}`)
        : (en ? `Under way${to ? ` to ${to}` : ""}` : `En route${to ? ` vers ${to}` : ""}`);
      const untilIso = live.iso || new Date(nowMs).toISOString();
      const wind = current && dep ? windBetween(journal, dep, untilIso) : null;
      const crossings = current && dep ? routeEventsSentence(routeEventsBetween(journal, dep, untilIso), lang) : "";
      const tail = [
        Number.isFinite(left) && left > 0.5 ? (en ? `${nmLabel(left, lang)} to go` : `encore ${nmLabel(left, lang)}`) : null,
        eta ? (en ? `expected on ${eta}` : `arrivée prévue le ${eta}`) : null,
      ].filter(Boolean).join(", ");
      out.push(`${since}${tail ? ` : ${tail}` : ""}.${crossings ? ` ${crossings}` : ""}${wind ? (en
        ? ` Wind at the boat so far: ${wind.mean} kn on average, ${wind.max} kn at most (GFS).`
        : ` Vent au bateau depuis : ${wind.mean} kn en moyenne, ${wind.max} kn au plus fort (GFS).`) : ""}`);
      out.push(en
        ? `${when}: the boat is ${dist} from the start.`
        : `${when} : le bateau est à ${dist} du départ.`);
    }
  }

  // 4. Le vent au bateau maintenant (GRIB live, sinon dernière entrée du journal).
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
      ? `${w.when ? `On ${dayMonth(w.when, lang)}, at the boat` : "At the boat now"}: wind ${kn} kn${from ? ` from the ${from}` : ""}${w.model ? ` (${w.model} forecast)` : ""}.`
      : `${w.when ? `Le ${dayMonth(w.when, lang)}, au bateau` : "Au bateau maintenant"} : vent ${kn} kn${from ? ` de ${from}` : ""}${w.model ? ` (prévision ${w.model})` : ""}.`);
  }

  return out;
}

export function expeditionStoryText(params) {
  return expeditionStory(params).join("\n\n");
}
