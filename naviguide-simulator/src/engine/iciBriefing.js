/**
 * Story of the `ici()` bag — one briefing, not four agents.
 * Tells only what is around the boat.
 */

import { briefingEntities, placeLabel, segmentBriefing } from "./briefingLinks.js";
import { getCardinalDirection } from "../utils/getCardinalDirection.js";

const TERRITORY = {
  fr: {
    france_metropolitaine: "France métropolitaine",
    guyane: "Guyane",
    martinique: "Martinique",
    guadeloupe: "Guadeloupe",
    saint_barthelemy: "Saint-Barthélemy",
    saint_martin: "Saint-Martin",
    saint_pierre_et_miquelon: "Saint-Pierre-et-Miquelon",
    polynesie_francaise: "Polynésie française",
    nouvelle_caledonie: "Nouvelle-Calédonie",
    wallis_et_futuna: "Wallis-et-Futuna",
    la_reunion: "La Réunion",
    mayotte: "Mayotte",
    taaf: "Terres australes et antarctiques françaises",
  },
  en: {
    france_metropolitaine: "metropolitan France",
    guyane: "French Guiana",
    martinique: "Martinique",
    guadeloupe: "Guadeloupe",
    saint_barthelemy: "Saint Barthélemy",
    saint_martin: "Saint Martin",
    saint_pierre_et_miquelon: "Saint Pierre and Miquelon",
    polynesie_francaise: "French Polynesia",
    nouvelle_caledonie: "New Caledonia",
    wallis_et_futuna: "Wallis and Futuna",
    la_reunion: "Réunion",
    mayotte: "Mayotte",
    taaf: "French Southern and Antarctic Lands",
  },
};

function isEn(lang) {
  return lang === "en";
}

function wrapLongToken(text) {
  if (text == null || text === "") return "";
  return String(text).replace(/([_/.-])/g, "$1\u200b");
}

function isOverlandLeg(_dossier, mark) {
  const from = String(mark?.from || "");
  const to = String(mark?.to || "");
  return /saint-maur/i.test(from) && /la\s*rochelle/i.test(to);
}

/* ---- small helpers for plain-language sentences ---- */

const MONTHS = {
  fr: ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
  en: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
};

function num(n, lang, digits = null) {
  const v = Number(n);
  if (!Number.isFinite(v)) return "—";
  const s = digits == null ? String(Math.round(v * 100) / 100) : v.toFixed(digits);
  return isEn(lang) ? s : s.replace(".", ",");
}

/** "NNO (329°)" — cardinal + degrees, French letters unless English. */
function heading(deg, lang) {
  const d = Number(deg);
  if (!Number.isFinite(d)) return "";
  let card = getCardinalDirection(d);
  if (isEn(lang)) card = card.replace(/O/g, "W");
  return `${card} (${Math.round(d)}°)`;
}

function monthName(m, lang) {
  const i = Number(m) - 1;
  const table = MONTHS[isEn(lang) ? "en" : "fr"];
  return table[i] || String(m);
}

function longDate(iso, lang) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso).slice(0, 10);
  const day = d.getUTCDate();
  const month = monthName(d.getUTCMonth() + 1, lang);
  return isEn(lang) ? `${day} ${month} ${d.getUTCFullYear()}` : `${day} ${month} ${d.getUTCFullYear()}`;
}

/** Engine reason codes → words. Unknown codes are kept as they are (honest, not hidden). */
const REASONS = {
  off_grid: ["hors de la grille du modèle", "outside the model grid"],
  no_feature_at_point: ["rien au point", "nothing at this point"],
  no_substrate_class: ["nature du fond non classée ici", "seabed class not mapped here"],
  not_generated: ["pas encore calculé", "not computed yet"],
  no_scene_in_bbox: ["aucune image récente ici", "no recent image here"],
  review_requires_admin: ["réservée à l’administration", "administrators only"],
  no_entity: ["rien à vérifier ici", "nothing to check here"],
  not_in_along_pearl: ["non collecté sur cette perle", "not collected on this pearl"],
  rtofs_not_ingested: ["RTOFS pas encore ingéré", "RTOFS not ingested yet"],
  null: ["pas de donnée", "no data"],
};

function why(code, lang) {
  const key = String(code ?? "null");
  const row = REASONS[key];
  if (row) return row[isEn(lang) ? 1 : 0];
  if (/^openmeteo_unavailable/.test(key)) return isEn(lang) ? "Open-Meteo did not answer" : "Open-Meteo n’a pas répondu";
  if (/^rtofs_unavailable/.test(key)) return isEn(lang) ? "RTOFS did not answer" : "RTOFS n’a pas répondu";
  return key;
}

function joinList(parts, lang) {
  if (!parts.length) return "";
  if (parts.length === 1) return parts[0];
  const last = parts[parts.length - 1];
  return `${parts.slice(0, -1).join(", ")}${isEn(lang) ? " and " : " et "}${last}`;
}

/** "Name (0,3 nm), Other (1,2 nm) et Last (5 nm)". The sheet link is in the UI, not in the text. */
function listPlaces(items, lang, max = 3, kind = null) {
  const slice = (items || []).slice(0, max);
  const parts = slice.map((x) => {
    const name = placeLabel(kind, x, lang);
    const nm = Number.isFinite(x.nm) ? ` (${num(x.nm, lang)} nm)` : "";
    return `${name}${nm}`;
  });
  return joinList(parts, lang);
}

function formatEta(hours, lang) {
  if (hours == null || !Number.isFinite(hours) || hours <= 0) return null;
  const en = isEn(lang);
  if (hours >= 48) {
    const days = Math.round(hours / 24);
    return en ? `${days} days` : `${days} jours`;
  }
  if (hours < 1) {
    const m = Math.max(1, Math.round(hours * 60));
    return `${m} min`;
  }
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (!m) return `${h} h`;
  return `${h} h ${String(m).padStart(2, "0")}`;
}

function zeeSentence(dossier, lang) {
  const en = isEn(lang);
  const zee = dossier?.zee;
  const highSeas = en
    ? "The boat is on the high seas: no exclusive economic zone, no entry formalities to plan."
    : "Le bateau est en haute mer : aucune ZEE, pas de formalités d’entrée à prévoir.";
  if (!zee) return highSeas;
  if (zee.ashore || String(zee.name || "").startsWith("À terre")) {
    const extra = String(zee.name || "").startsWith("À terre")
      ? zee.name.slice("À terre".length).trim()
      : "";
    return en
      ? `The boat is ashore${extra ? ` ${extra}` : ""}, outside any EEZ.`
      : `Le bateau est à terre${extra ? ` ${extra}` : ""}, hors de toute ZEE.`;
  }
  if (!zee.mrgid || zee.name === "Haute mer") return highSeas;
  const territory = TERRITORY[en ? "en" : "fr"][zee.territory];
  const where = territory ? `${zee.name} (${territory})` : zee.name;
  let formalities;
  if (zee.gold) {
    formalities = en
      ? "Entry formalities go through official ports of entry, listed below."
      : "Les formalités d’entrée passent par des ports officiels, listés ci-dessous.";
  } else if (zee.territory) {
    formalities = en
      ? "French EEZ; the entry formalities are not complete in our data yet."
      : "ZEE française ; les formalités d’entrée ne sont pas encore complètes dans nos données.";
  } else {
    formalities = en
      ? "Not a French EEZ: check the local entry formalities."
      : "Ce n’est pas une ZEE française : formalités d’entrée locales à vérifier.";
  }
  return en
    ? `The boat is sailing in ${where}. ${formalities}`
    : `Le bateau navigue dans ${where}. ${formalities}`;
}

function poeSentence(dossier, lang) {
  const en = isEn(lang);
  const poe = dossier?.poe || [];
  if (!poe.length) {
    if (!dossier?.zee?.mrgid) return "";
    return en
      ? "No official port of entry is known for this EEZ."
      : "Aucun port d’entrée officiel n’est connu pour cette ZEE.";
  }
  const listed = listPlaces(poe, lang, 4, "poe");
  return en
    ? `Nearest official ports of entry: ${listed}.`
    : `Ports d’entrée officiels les plus proches : ${listed}.`;
}

function ampSentence(dossier, lang) {
  const items = dossier?.amp || [];
  if (!items.length) return "";
  const listed = listPlaces(items, lang, 3, "amp");
  return isEn(lang)
    ? `Marine protected areas within 30 nm: ${listed}.`
    : `Aires marines protégées à moins de 30 milles : ${listed}.`;
}

function projectsSentence(dossier, lang) {
  const listed = listPlaces(dossier?.projects, lang, 3, "project");
  if (!listed) return "";
  return isEn(lang)
    ? `Projects and initiatives nearby: ${listed}.`
    : `Projets et initiatives à proximité : ${listed}.`;
}

function harboursSentence(dossier, lang) {
  const en = isEn(lang);
  const bits = [];
  const marinas = listPlaces(dossier?.nearby?.marinas, lang, 3, "marina");
  if (marinas) bits.push(en ? `marinas ${marinas}` : `marinas ${marinas}`);
  const capit = listPlaces(dossier?.nearby?.capitaineries, lang, 2, "capitainerie");
  if (capit) bits.push(en ? `harbour offices ${capit}` : `capitaineries ${capit}`);
  const wpi = listPlaces(dossier?.nearby?.wpi, lang, 2, "wpi");
  if (wpi) bits.push(en ? `commercial ports (WPI) ${wpi}` : `ports de commerce (WPI) ${wpi}`);
  if (!bits.length) return "";
  return en
    ? `Harbours nearby: ${bits.join("; ")}.`
    : `Ports à proximité : ${bits.join(" ; ")}.`;
}

function scienceSentence(dossier, lang) {
  const science = listPlaces(dossier?.science?.nearby, lang, 3, "science");
  if (!science) return "";
  return isEn(lang)
    ? `Scientific datasets around the boat: ${science}.`
    : `Données scientifiques disponibles autour du bateau : ${science}.`;
}

function aroundSentence(dossier, lang) {
  const en = isEn(lang);
  const bits = [
    ampSentence(dossier, lang),
    projectsSentence(dossier, lang),
    harboursSentence(dossier, lang),
    scienceSentence(dossier, lang),
    anchorageSentence(dossier, lang),
    atonSentence(dossier, lang),
  ].filter(Boolean);
  if (bits.length) return bits.join("\n\n");
  return en
    ? "Nothing notable within 30 nautical miles."
    : "Rien de notable à moins de 30 milles.";
}

function anchorageSentence(dossier, lang) {
  const listed = listPlaces(dossier?.nearby?.anchorages, lang, 3, "anchorage");
  if (!listed) return "";
  return isEn(lang)
    ? `Anchorages: ${listed}.`
    : `Mouillages : ${listed}.`;
}

function atonSentence(dossier, lang) {
  const en = isEn(lang);
  const aton = dossier?.aton;
  const listed = listPlaces(aton?.nearby, lang, 3, "aton");
  if (listed) {
    return en ? `Aids to navigation: ${listed}.` : `Balisage : ${listed}.`;
  }
  // A thin pearl never looked: say nothing rather than "not collected on this pearl".
  if (aton?.reason && aton.reason !== "not_in_along_pearl") {
    return en
      ? `No aid to navigation recorded here (${why(aton.reason, lang)}).`
      : `Pas de balisage recensé ici (${why(aton.reason, lang)}).`;
  }
  return "";
}

const DERIVED_WORDS = {
  coastline: ["trait de côte", "coastline"],
  sdb: ["bathymétrie satellite", "satellite bathymetry"],
  intertidal: ["zone intertidale", "intertidal zone"],
};

/** "S2B_MSIL2A_20260914T105619_N0512_R094_T31TDM_…" → { sat: "S2B", tile: "T31TDM", date: "2026-09-14" }. */
function parseSentinelId(id) {
  const m = /^(S2[AB])_MSIL(1C|2A)_(\d{4})(\d{2})(\d{2})T\d{6}_N\d+_R\d+_(T\w+?)_/.exec(String(id || ""));
  if (!m) return null;
  return { sat: m[1], level: m[2], date: `${m[3]}-${m[4]}-${m[5]}`, tile: m[6] };
}

export function satelliteSentence(dossier, lang) {
  const en = isEn(lang);
  const s = dossier?.satellites;
  if (!s) return "";
  const scene = s.scene || (s.scenes && s.scenes[0]);
  const derived = s.derived || {};
  const missing = Object.entries(derived)
    .filter(([, v]) => v && v.value == null);
  if (scene) {
    const parsed = parseSentinelId(scene.id);
    const when = longDate(scene.datetime || parsed?.date, lang);
    const product = /sentinel-2/i.test(scene.product || "") || parsed ? "Sentinel-2" : (scene.product || "Sentinel");
    const detail = parsed ? ` (${parsed.sat}${parsed.tile ? `, ${en ? "tile" : "tuile"} ${parsed.tile}` : ""})` : "";
    let tail = "";
    if (missing.length) {
      const names = missing.map(([k]) => (DERIVED_WORDS[k] ? DERIVED_WORDS[k][en ? 1 : 0] : k));
      const reasons = new Set(missing.map(([, v]) => v.reason || "null"));
      let reason = reasons.size === 1 ? why([...reasons][0], lang) : (en ? "not available" : "indisponibles");
      if (!en && names.length > 1 && reason === "pas encore calculé") reason = "pas encore calculés";
      const list = joinList(names, lang);
      const sentence = list[0].toUpperCase() + list.slice(1);
      tail = en ? ` ${sentence}: ${reason}.` : ` ${sentence} : ${reason}.`;
    }
    return en
      ? `Latest satellite image: ${product}${detail}${when ? ` on ${when}` : ""} (observation).${tail}`
      : `Dernière image satellite : ${product}${detail}${when ? ` du ${when}` : ""} (observation).${tail}`;
  }
  return en
    ? `No recent satellite image here (${why(s.reason, lang)}).`
    : `Aucune image satellite récente ici (${why(s.reason, lang)}).`;
}

function weatherSentence(dossier, lang) {
  const en = isEn(lang);
  const w = dossier?.weather;
  if (!w) return "";
  const wind = w.wind;
  const wave = w.wave;
  if (!wind && !wave) {
    if (w.status === "pending") {
      return en ? "Weather forecast: loading…" : "Prévision météo : chargement…";
    }
    return en
      ? `Weather forecast unavailable (${why(w.reason, lang)}).`
      : `Prévision météo indisponible (${why(w.reason, lang)}).`;
  }
  const bits = [];
  if (wind?.speedKnots != null) {
    const from = heading(wind.dirFromDeg, lang);
    bits.push(en
      ? `wind ${num(wind.speedKnots, lang)} kn${from ? ` from ${from}` : ""}`
      : `vent ${num(wind.speedKnots, lang)} kn${from ? ` de ${from}` : ""}`);
  }
  if (wave?.hs != null) {
    let sea = en ? `sea ${num(wave.hs, lang)} m` : `mer ${num(wave.hs, lang)} m`;
    if (wave.dirDeg != null) sea += en ? ` from ${heading(wave.dirDeg, lang)}` : ` de ${heading(wave.dirDeg, lang)}`;
    if (wave.periodS != null) sea += en ? `, period ${num(wave.periodS, lang)} s` : `, période ${num(wave.periodS, lang)} s`;
    bits.push(sea);
  }
  if (w.current && w.current.speedKnots != null) {
    const to = heading(w.current.dirToDeg, lang);
    bits.push(en
      ? `current ${num(w.current.speedKnots, lang)} kn${to ? ` toward ${to}` : ""} (RTOFS)`
      : `courant ${num(w.current.speedKnots, lang)} kn${to ? ` vers ${to}` : ""} (RTOFS)`);
  } else if (w.current == null && w.current_reason) {
    bits.push(en
      ? `current: ${why(w.current_reason, lang)}`
      : `courant : ${why(w.current_reason, lang)}`);
  }
  const model = w.model || w.source || "Open-Meteo";
  return en
    ? `Weather forecast (${model}): ${bits.join(", ")}.`
    : `Prévision météo (${model}) : ${bits.join(", ")}.`;
}

function emodnetSentence(dossier, lang) {
  const en = isEn(lang);
  const e = dossier?.emodnet;
  if (!e) return "";
  const bits = [];
  const depth = e.bathy?.depth_m;
  if (depth != null) bits.push(en ? `${num(depth, lang)} m on the chart` : `${num(depth, lang)} m sur la carte`);
  else if (e.bathy?.reason) bits.push(en ? `depth: ${why(e.bathy.reason, lang)}` : `profondeur : ${why(e.bathy.reason, lang)}`);
  if (e.seabed?.label) bits.push(en ? `seabed ${e.seabed.label}` : `nature du fond : ${e.seabed.label}`);
  else if (e.seabed?.reason === "no_substrate_class") bits.push(why(e.seabed.reason, lang));
  else if (e.seabed?.reason) bits.push(en ? `seabed: ${why(e.seabed.reason, lang)}` : `nature du fond : ${why(e.seabed.reason, lang)}`);
  if (e.cables?.nearby === true) bits.push(en ? "a submarine cable passes here" : "un câble sous-marin passe ici");
  else if (e.cables?.nearby === false || e.cables?.reason) {
    bits.push(en ? "no submarine cable at this point" : "aucun câble sous-marin au point");
  }
  if (!bits.length) {
    return en
      ? `Seabed (EMODnet): ${why(e.reason, lang)}.`
      : `Fond (EMODnet) : ${why(e.reason, lang)}.`;
  }
  return en
    ? `Seabed (EMODnet, observation): ${bits.join("; ")}.`
    : `Fond (EMODnet, observation) : ${bits.join(" ; ")}.`;
}

function reviewSentence(dossier, lang) {
  const en = isEn(lang);
  const r = dossier?.review;
  if (!r) return "";
  const bits = [];
  if (r.zee && r.zee.gold_on != null) {
    bits.push(en
      ? `EEZ formalities ${r.zee.gold_on ? "verified" : "not verified"}`
      : `formalités ZEE ${r.zee.gold_on ? "vérifiées" : "non vérifiées"}`);
  }
  if (r.amp && r.amp.gold_on != null) {
    bits.push(en
      ? `MPA rules ${r.amp.gold_on ? "verified" : "not verified"}`
      : `règles AMP ${r.amp.gold_on ? "vérifiées" : "non vérifiées"}`);
  }
  if (!bits.length) {
    // No sheet to tell: nothing to check here, or the sheet is an internal
    // (admin) status of Blue Intelligence — the visitor is not the one
    // missing a key, so the briefing stays silent about it.
    if (!r.reason || r.reason === "no_entity" || r.reason === "review_requires_admin") return "";
    return en
      ? `Verification sheet: ${why(r.reason, lang)}.`
      : `Fiche de vérification : ${why(r.reason, lang)}.`;
  }
  return en
    ? `Verification sheet: ${bits.join(", ")}.`
    : `Fiche de vérification : ${bits.join(", ")}.`;
}

function signedDelta(n, unit) {
  if (!Number.isFinite(n)) return "";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n} ${unit}`;
}

/**
 * Sentences about the machinery never reach the visitor (mirror of
 * story_cascade.tidy_story). Word boundaries that know accents: `\b` in
 * JavaScript stops at "é".
 */
const W = "(?<![\\p{L}\\d])";
const E = "(?![\\p{L}\\d])";
const STORY_META_RE = new RegExp([
  `${W}jug[eé]e?s?${E}`, `${W}juge${E}`, `${W}class[ée]e?s?${E}`, "classif", `${W}identifiant`, `${W}identifier${E}`, `${W}ID${E}`,
  "s[ée]v[ée]rit", `${W}severity${E}`, `${W}playhead${E}`, `${W}DOI${E}`, "aucune (?:information|donn[ée]e)",
  "no (?:additional|further|extra) (?:information|data|details?)", `${W}event type${E}`, "type d[’']?[ée]v[ée]nement",
  `${W}LOA${E}`, "tirant d[’']eau", `${W}draft${E}`, "briefing nautique", "skipper\\.used", "r[èe]gles? de croisi[èe]re", "cruise rules",
  `${W}watch${E}`, `${W}imm[ée]diate${E}`, "d[ée]cision a [ée]t[ée] prise", "the decision was taken",
].join("|"), "iu");

/** Keep the fact, drop the machinery; "" when nothing is left. Max two sentences. */
export function cleanStoryText(text) {
  const lines = String(text || "")
    .split("\n")
    .map((ln) => ln.replace(/[*_#>`]+/g, "").replace(/^\s*(?:[-•]|\d+[.)])\s+/, "").trim())
    .filter((ln) => ln && !(ln.length < 80 && !/[.!?…]$/.test(ln.replace(/:$/, ""))));
  const raw = lines.join(" ").replace(/\s{2,}/g, " ").trim();
  if (!raw) return "";
  const kept = raw.split(/(?<=[.!?…])\s+(?=\S)/).filter((s) => s.trim() && !STORY_META_RE.test(s));
  return kept.slice(0, 2).join(" ").trim();
}

export function phraseForEvent(ev, lang = "fr") {
  if (!ev) return "";
  if (ev.story?.status === "ready" && ev.story.text) {
    const tidy = cleanStoryText(ev.story.text);
    if (tidy) return tidy;
  }
  if (typeof ev.phrase === "string" && ev.phrase.trim()) return ev.phrase;
  const en = isEn(lang);
  const p = ev.payload || {};
  const name = ev.name || p.zee?.name || p.amp?.name || p.harbour?.name;
  switch (ev.type) {
    case "zee-enter":
      return en
        ? `We have just entered ${name || "this EEZ"}.`
        : `On vient d’entrer dans ${name || "cette ZEE"}.`;
    case "zee-exit":
      return en
        ? "The boat is back on the high seas — no EEZ to clear."
        : "Retour en haute mer — plus de ZEE à déclarer.";
    case "zee-ahead": {
      const when = p.whenNm ?? ev.whenNm;
      return en
        ? `Ahead${Number.isFinite(when) ? ` in ${Math.round(when)} nm` : ""}: ${name || "another EEZ"}.`
        : `Devant${Number.isFinite(when) ? ` dans ${Math.round(when)} nm` : ""} : ${name || "une autre ZEE"}.`;
    }
    case "amp-ahead": {
      const when = p.whenNm ?? ev.whenNm;
      const visit = p.amp?.visitable || p.visitable;
      return en
        ? `MPA on the track${Number.isFinite(when) ? ` in ${Math.round(when)} nm` : ""}: ${name || "MPA"}${visit ? " (visit page in the pack)" : ""}.`
        : `AMP sur le trait${Number.isFinite(when) ? ` dans ${Math.round(when)} nm` : ""} : ${name || "AMP"}${visit ? " (page visite dans le sac)" : ""}.`;
    }
    case "poe-ahead":
      return en
        ? `Official port of entry ahead: ${p.poe?.name || name || "PoE"}${p.poe?.nm != null ? ` (${p.poe.nm} nm)` : ""}.`
        : `Port d’entrée officiel devant : ${p.poe?.name || name || "PoE"}${p.poe?.nm != null ? ` (${p.poe.nm} nm)` : ""}.`;
    case "amp-enter": {
      const visit = p.amp?.visitable || p.visitable;
      return en
        ? `A marine protected area is now inside 30 nm: ${name || "MPA"}${visit ? " (visit page in the pack)" : ""}.`
        : `Une aire marine entre dans les 30 milles : ${name || "AMP"}${visit ? " (page visite dans le sac)" : ""}.`;
    }
    case "wind-shift": {
      const kind = p.kind || ev.kind || "forecast";
      const src = p.source ? `, ${p.source}` : "";
      const delta = signedDelta(p.dTws, "kn");
      return en
        ? `Wind ${p.tws} kn / ${p.twd}° (kind: ${kind}${src})${delta ? ` — ${delta}` : ""}.`
        : `Vent ${p.tws} kn / ${p.twd}° (kind: ${kind}${src})${delta ? ` — ${delta}` : ""}.`;
    }
    case "wind-gale": {
      const kind = p.kind || ev.kind || "forecast";
      return en
        ? `Gale: ${p.tws} kn (kind: ${kind}${p.galePct != null ? `, gale ${p.galePct}%` : ""}).`
        : `Coup de vent : ${p.tws} kn (kind: ${kind}${p.galePct != null ? `, gale ${p.galePct} %` : ""}).`;
    }
    case "current-shift": {
      const kind = p.kind || ev.kind || "forecast";
      return en
        ? `Current ${p.kn} kn / ${p.dir}° (kind: ${kind}${p.source ? `, ${p.source}` : ""})${p.invert ? " — direction reversed" : ""}.`
        : `Courant ${p.kn} kn / ${p.dir}° (kind: ${kind}${p.source ? `, ${p.source}` : ""})${p.invert ? " — inversion" : ""}.`;
    }
    case "hs-shift": {
      const kind = p.kind || ev.kind || "forecast";
      return en
        ? `Significant wave ${p.hs} m (kind: ${kind}${p.alert ? ", alert" : ""}).`
        : `Houle ${p.hs} m (kind: ${kind}${p.alert ? ", alerte" : ""}).`;
    }
    case "wx-alert": {
      const bits = [];
      if (p.rainMm != null) bits.push(en ? `rain ${p.rainMm} mm/h` : `pluie ${p.rainMm} mm/h`);
      if (p.gale) bits.push(en ? "gale" : "coup de vent");
      if (p.hs != null) bits.push(`Hs ${p.hs} m`);
      const kind = p.kind || "forecast";
      return en
        ? `Weather alert (kind: ${kind}): ${bits.join(" · ") || "threshold"}.`
        : `Alerte météo (kind: ${kind}) : ${bits.join(" · ") || "seuil"}.`;
    }
    case "marina-refuge": {
      const port = p.harbour?.name || name || (en ? "a harbour" : "un port");
      const nm = p.harbour?.nm;
      const rain = p.rainMm != null ? (en ? `Rain ${p.rainMm} mm/h (GFS). ` : `Pluie ${p.rainMm} mm/h (GFS). `) : "";
      return en
        ? `${rain}Refuge: ${port}${nm != null ? ` at ${nm} nm` : ""}.`
        : `${rain}Repli : ${port}${nm != null ? ` à ${nm} nm` : ""}.`;
    }
    case "depth-alert": {
      // Skipper wording: shelf (Coastal / Cruise) or grounding (Ocean). Never "haut-fond" for a 15 m shelf.
      if (p.label && Number.isFinite(p.alertM)) {
        const head = p.label === "talonnage"
          ? (en ? "Grounding risk" : "Risque de talonner")
          : (en ? "Approaching the shelf" : "On approche du plateau");
        return en
          ? `${head}: ${p.depthM} m sounded, under ${p.alertM} m (${p.source || "DTM"}, kind: observation; not for navigation).`
          : `${head} : ${p.depthM} m sondés, sous ${p.alertM} m (${p.source || "DTM"}, kind: observation ; ne convient pas à la navigation).`;
      }
      return en
        ? `Shallow sounding ${p.depthM} m (${p.source || "DTM"}, kind: observation; not for navigation).`
        : `Haut-fond ${p.depthM} m (${p.source || "DTM"}, kind: observation ; ne convient pas à la navigation).`;
    }
    case "group": {
      if (en && ev.digest?.en) return ev.digest.en;
      if (!en && ev.digest?.fr) return ev.digest.fr;
      const members = (p.members || []).join(" + ");
      return en
        ? `Along this leg: ${members}.`
        : `Depuis cette jambe : ${members}.`;
    }
    default:
      return "";
  }
}

function eventSentence(dossier, lang) {
  const ev = dossier?.event;
  if (!ev) return "";
  return phraseForEvent(ev, lang);
}

function legSentence(dossier, lang) {
  const en = isEn(lang);
  const mark = (dossier?.marks || []).find((m) => m.kind === "leg");
  const polar = dossier?.polar || {};
  if (mark?.vehicle === "plane" || mark?.phase === "air-out" || mark?.phase === "air-return") {
    const quay = mark.from || "";
    return en
      ? `The boat stays at the dock${quay ? ` in ${quay}` : ""} during the air hop.`
      : `Le bateau reste à quai${quay ? ` à ${quay}` : ""} pendant le transfert aérien.`;
  }
  const to = mark?.to;
  const from = mark?.from;
  const overland = isOverlandLeg(dossier, mark);
  const speed = !overland && Number.isFinite(polar.speedKnots) ? polar.speedKnots : null;
  const eta = formatEta(polar.etaHours, lang);
  const boat = polar.boat;
  const bits = [];
  if (to && (speed != null || eta || overland)) {
    if (overland) {
      bits.push(en
        ? `Overland leg${from ? ` from ${from}` : ""} to ${to}${eta ? `: still ${eta} on the road` : ""} (the boat is not at sea yet).`
        : `Étape terrestre${from ? ` de ${from}` : ""} vers ${to}${eta ? ` : encore ${eta} de route` : ""} (le bateau n’est pas encore en mer).`);
    } else {
      bits.push(en
        ? `Heading for ${to}${from ? ` from ${from}` : ""}${eta ? `: still ${eta} at sea` : ""}${speed != null ? ` at ${num(speed, lang)} knots` : ""}.`
        : `Cap sur ${to}${from ? ` depuis ${from}` : ""}${eta ? ` : encore ${eta} de mer` : ""}${speed != null ? ` à ${num(speed, lang)} nœuds` : ""}.`);
    }
  } else if (speed != null) {
    bits.push(en ? `Boat speed on this leg: ${num(speed, lang)} knots.` : `Vitesse sur cette jambe : ${num(speed, lang)} nœuds.`);
  }
  if (boat) {
    bits.push(en ? `Polar loaded: ${boat}.` : `Polaire chargée : ${boat}.`);
  }
  return bits.join(" ");
}

function depthSentence(dossier, lang) {
  const d = Number(dossier?.depthOffshore);
  if (!Number.isFinite(d) || Math.abs(d) < 1) return "";
  const m = Math.round(Math.abs(d));
  return isEn(lang)
    ? `Offshore depth about ${m} m (GEBCO Compilation Group; indicative, not for navigation).`
    : `Profondeur au large : environ ${m} m (GEBCO Compilation Group ; indicatif, ne convient pas à la navigation).`;
}

export function climatologySentence(dossier, lang) {
  const en = isEn(lang);
  const c = dossier?.climatology;
  if (!c) return "";
  const month = c.month;
  const point = c.point || c;
  const w = point.wind_atlas?.most_likely || point.wind_atlas?.vector_mean;
  const wave = point.wave;
  const cur = point.current;
  const zone = c.wind;
  const src = c.source;
  if (src === "unavailable" && !w && !zone) {
    return en
      ? "The climatology atlas did not answer; the clock keeps the typical wind of the zone."
      : "L’atlas de climatologie n’a pas répondu ; l’horloge garde le vent typique de la zone.";
  }
  const bits = [];
  if (w) {
    bits.push(en
      ? `typical wind ${num(w.speed_knots, lang)} kn from ${heading(w.dir_deg, lang)}`
      : `vent typique ${num(w.speed_knots, lang)} kn de ${heading(w.dir_deg, lang)}`);
  } else if (zone) {
    bits.push(en
      ? `typical wind of the zone ${num(zone.speedKnots, lang)} kn from ${heading(zone.dirFromDeg, lang)}`
      : `vent typique de la zone ${num(zone.speedKnots, lang)} kn de ${heading(zone.dirFromDeg, lang)}`);
  }
  if (wave?.hs_p50_m != null || wave?.hs_p90_m != null) {
    const parts = [];
    if (wave.hs_p50_m != null) parts.push(en ? `${num(wave.hs_p50_m, lang)} m on average` : `${num(wave.hs_p50_m, lang)} m en moyenne`);
    if (wave.hs_p90_m != null) parts.push(en ? `${num(wave.hs_p90_m, lang)} m on rough days (P90)` : `${num(wave.hs_p90_m, lang)} m les jours agités (P90)`);
    let sea = (en ? "sea " : "mer ") + parts.join(", ");
    if (wave.period_s != null) sea += en ? `, period ${num(wave.period_s, lang)} s` : `, période ${num(wave.period_s, lang)} s`;
    if (wave.dir_deg != null) sea += en ? `, from ${heading(wave.dir_deg, lang)}` : `, de ${heading(wave.dir_deg, lang)}`;
    bits.push(sea);
  }
  if (cur && cur.speed_knots != null) {
    const to = cur.direction_to_deg != null ? heading(cur.direction_to_deg, lang) : "";
    bits.push(en
      ? `current ${num(cur.speed_knots, lang)} kn${to ? ` toward ${to}` : ""}`
      : `courant ${num(cur.speed_knots, lang)} kn${to ? ` vers ${to}` : ""}`);
  }
  const rose = c.rose || point.wind_atlas;
  if (rose?.calm_pct != null) bits.push(en ? `calm ${num(rose.calm_pct, lang)}% of the time` : `calme ${num(rose.calm_pct, lang)} % du temps`);
  if (rose?.gale_pct != null) bits.push(en ? `gale ${num(rose.gale_pct, lang)}% of the time` : `coup de vent ${num(rose.gale_pct, lang)} % du temps`);
  if (rose?.stat === "rose" && Array.isArray(rose.directions_from) && rose.directions_from.length) {
    bits.push(en ? "wind rose available" : "rose des vents disponible");
  }
  const nearbyCyc = c.cyclone?.nearby ?? point.cyclone?.nearby;
  const crossings = c.crossings?.count ?? point.cyclone?.crossings_if_leg?.count;
  if (nearbyCyc != null || crossings != null) {
    const cyc = [];
    if (nearbyCyc != null) {
      cyc.push(nearbyCyc
        ? (en ? `${nearbyCyc} passed nearby` : `${nearbyCyc} passé${nearbyCyc > 1 ? "s" : ""} à proximité`)
        : (en ? "none nearby" : "aucun à proximité"));
    }
    if (crossings != null) {
      cyc.push(crossings
        ? (en ? `${crossings} track${crossings > 1 ? "s" : ""} cross this leg` : `${crossings} trajectoire${crossings > 1 ? "s" : ""} croise${crossings > 1 ? "nt" : ""} cette jambe`)
        : (en ? "none crosses this leg" : "aucune trajectoire ne croise cette jambe"));
    }
    bits.push((en ? "historical cyclones (IBTrACS): " : "cyclones historiques (IBTrACS) : ") + cyc.join(", "));
  }
  const period = c.period || point.period;
  const doi = c.doi?.wind || point.doi?.wind;
  const provenance = c.provenance?.wind || point.provenance?.wind;
  const when = monthName(month, lang);
  const head = src === "atlas"
    ? (en ? `Climatology for ${when} (Copernicus atlas` : `Climatologie de ${when} (atlas Copernicus`)
    : (en ? `Climatology for ${when} (zone fallback` : `Climatologie de ${when} (repli de zone`);
  const tail = [];
  if (period) tail.push(String(period).replace("-", "–"));
  if (doi) tail.push(`DOI ${doi}`);
  else if (provenance) {
    const product = String(provenance).split("·")[0].trim();
    if (product) tail.push(en ? `source ${product}` : `source ${product}`);
  }
  return `${head}${tail.length ? `, ${tail.join(", ")}` : ""})${bits.length ? ` : ${bits.join(" ; ")}.` : "."}`;
}

function sourceSentence(dossier, lang) {
  const en = isEn(lang);
  const bi = dossier?.sources?.bi;
  const zee = dossier?.sources?.zee;
  const notes = [];
  if (zee === "error" && dossier?.zee?.mrgid) {
    notes.push(en
      ? "MarineRegions did not answer for the EEZ."
      : "MarineRegions n’a pas répondu pour la ZEE.");
  }
  if (bi === "unavailable") {
    notes.push(en
      ? "Blue Intelligence layers did not answer: only the EEZ and the World Port Index are kept."
      : "Les couches Blue Intelligence n’ont pas répondu : seuls la ZEE et les ports WPI sont conservés.");
  } else if (bi === "partial") {
    notes.push(en
      ? "Some Blue Intelligence layers are missing: the briefing tells only what arrived."
      : "Certaines couches Blue Intelligence manquent : le briefing ne raconte que ce qui est arrivé.");
  }
  return notes.join(" ");
}

/** "thin" | "rich" for a pearl standing in for the live bag, null for the live bag itself. */
export function pearlKind(dossier) {
  if (!dossier) return null;
  if (dossier.pearl === "rich" || dossier.pearl === "thin") return dossier.pearl;
  return dossier.thin ? "thin" : null;
}

export function narrateIci(dossier, lang = "fr") {
  if (!dossier) return "";
  // A pearl (the along bag standing in while the full bag is on its way)
  // never collected weather, satellite or the sheet — those only make sense
  // now: say nothing about them rather than "not collected on this pearl".
  // A thin pearl also skipped the seabed and the aids to navigation; a rich
  // one (lot P) carries them and tells them.
  const kind = pearlKind(dossier);
  const live = kind == null;
  const thin = kind === "thin";
  const parts = [
    [zeeSentence(dossier, lang), poeSentence(dossier, lang)].filter(Boolean).join(" "),
    aroundSentence(dossier, lang),
    live ? satelliteSentence(dossier, lang) : "",
    live ? weatherSentence(dossier, lang) : "",
    thin ? "" : emodnetSentence(dossier, lang),
    live ? reviewSentence(dossier, lang) : "",
    eventSentence(dossier, lang),
    thin ? "" : depthSentence(dossier, lang),
    climatologySentence(dossier, lang),
    legSentence(dossier, lang),
    live ? sourceSentence(dossier, lang) : "",
  ].filter(Boolean);
  return parts.join("\n\n");
}

/**
 * Same briefing, split around the places it names so the UI can link them
 * (map focus + official sheet / Google Maps). Plain text is unchanged:
 * `segments.map((s) => s.text).join("")` === `narrateIci(dossier, lang)`.
 */
export function narrateIciSegments(dossier, lang = "fr") {
  const text = narrateIci(dossier, lang);
  if (!text) return [];
  return segmentBriefing(text, briefingEntities(dossier, lang));
}
