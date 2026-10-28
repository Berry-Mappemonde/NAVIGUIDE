/**
 * Codes de raison des couches « Ici » → mots du briefing.
 *
 * Le serveur (ici_layers.py, ici_engine.py) dit pourquoi une donnée manque
 * par un code stable : « outside_us_enc;overpass_unavailable:ConnectError ».
 * Le briefing recopiait jadis le code inconnu tel quel, pour ne rien cacher.
 * Il dit maintenant la raison en clair ; le code brut reste lisible en
 * info-bulle (segment `reason.code`, BriefingText) : rien n'est perdu.
 */

import enDict from "../i18n/en.js";
import frDict from "../i18n/fr.js";

const UNREACHABLE = ["source injoignable pour l’instant", "source unreachable right now"];

/** Code entier (ou détail après « : ») → [fr, en]. */
export const REASON_WORDS = Object.freeze({
  off_grid: ["hors de la grille du modèle", "outside the model grid"],
  no_feature_at_point: ["aucune donnée à ce point", "no data at this point"],
  no_sample_at_point: ["pas de sondage à ce point", "no sounding at this point"],
  no_substrate_class: ["nature du fond non classée ici", "seabed class not mapped here"],
  not_generated: ["pas encore calculé", "not computed yet"],
  no_scene_in_bbox: ["aucune image récente ici", "no recent image here"],
  no_aid_in_bbox: ["aucun dans le rayon de recherche", "none within the search radius"],
  // US_BBOXES (ici_layers.py) ne couvre que les 50 États et Porto Rico : on dit
  // ce que l'appli a fait (pas lu les cartes NOAA ici), pas où ces cartes existent.
  outside_us_enc: ["cartes NOAA non consultées dans cette zone", "NOAA charts not read in this area"],
  no_osm_seamark: ["aucune marque cartographiée à proximité", "no seamark mapped nearby"],
  openmeteo_empty: ["pas de prévision à ce point", "no forecast at this point"],
  fiche_not_found: ["pas de fiche pour ce lieu", "no sheet for this place"],
  review_requires_admin: ["réservée à l’administration", "administrators only"],
  no_entity: ["rien à vérifier ici", "nothing to check here"],
  not_in_along_pearl: ["non collecté sur cette perle", "not collected on this pearl"],
  rtofs_not_ingested: ["courants pas encore chargés", "currents not loaded yet"],
  // weather_pipeline.py : une prévision périmée attend son rafraîchissement.
  stale_pending: ["prévision en cours de mise à jour", "forecast being refreshed"],
  "hors ligne": ["hors ligne", "offline"],
});

/** Préfixe d'un code `prefix:détail` (layer_code) → [fr, en]. */
export const SOURCE_DOWN_WORDS = Object.freeze({
  overpass_unavailable: ["serveur de cartes injoignable pour l’instant", "map server unreachable right now"],
  cdse_stac_unavailable: ["catalogue d’images injoignable pour l’instant", "image catalogue unreachable right now"],
  review_unavailable: ["service de vérification injoignable pour l’instant", "verification service unreachable right now"],
  // Pas de nom de source ici : « Open-Meteo » et « RTOFS » deviennent des liens
  // dans le briefing, et le code ne trouverait plus sa phrase.
  openmeteo_unavailable: ["service météo sans réponse", "weather service did not answer"],
  rtofs_unavailable: ["service des courants sans réponse", "currents service did not answer"],
  aton_unavailable: UNREACHABLE,
  emodnet_unavailable: UNREACHABLE,
  wms_unavailable: UNREACHABLE,
  depth_sample_unavailable: UNREACHABLE,
});

/** Code inconnu : phrase générique, le code reste en info-bulle. */
export const GENERIC_WORDS = Object.freeze(["donnée indisponible", "data unavailable"]);

/** Traceback, classe Python, HTTPStatusError : jamais à l'écran, même en info-bulle. */
export function cleanReason(code) {
  let key = String(code ?? "null");
  key = key.replace(/Traceback \(most recent call last\):[\s\S]*/g, "");
  key = key.replace(/<class ['"][^'"]+['"]>/g, "");
  key = key.replace(/:?\bHTTPStatusError\b/g, "");
  key = key.replace(/:+/g, ":").replace(/^:+|:+$/g, "");
  return key.trim() || "unavailable";
}

const CODE_SHAPE = /^[\w.:;/+-]+$/;

function partWords(part, en) {
  const i = en ? 1 : 0;
  const dict = en ? enDict : frDict;
  if (part === "unavailable") return { text: dict.iciReasonUnavailable, known: true };
  if (part === "no_data") return { text: dict.iciReasonNoData, known: true };
  if (REASON_WORDS[part]) return { text: REASON_WORDS[part][i], known: true };
  const cut = part.indexOf(":");
  const base = cut < 0 ? part : part.slice(0, cut);
  const detail = cut < 0 ? "" : part.slice(cut + 1);
  if (detail === "no_data") return { text: dict.iciReasonNoData, known: true };
  if (REASON_WORDS[detail]) return { text: REASON_WORDS[detail][i], known: true };
  if (SOURCE_DOWN_WORDS[base]) return { text: SOURCE_DOWN_WORDS[base][i], known: true };
  if (/_unavailable$/.test(base)) return { text: UNREACHABLE[i], known: true };
  return { text: GENERIC_WORDS[i], known: false };
}

/**
 * Raison brute → { text, code, known }.
 *   text  — ce que dit le briefing (jamais un code) ;
 *   code  — le code nettoyé, pour l'info-bulle (null s'il n'y a rien à montrer) ;
 *   known — false si un morceau du code n'a pas de mots (phrase générique).
 * Une raison déjà en mots (avec des espaces) est gardée telle quelle.
 */
export function reasonWords(raw, lang = "fr") {
  const en = lang === "en";
  const dict = en ? enDict : frDict;
  if (raw == null || raw === "null") return { text: dict.iciReasonNoData, code: null, known: true };
  const code = cleanReason(raw);
  if (REASON_WORDS[code]) return { text: REASON_WORDS[code][en ? 1 : 0], code, known: true };
  if (!CODE_SHAPE.test(code)) return { text: code, code: null, known: true };
  const parts = code.split(";").map((p) => p.trim()).filter(Boolean);
  const said = parts.map((p) => partWords(p, en));
  const texts = [...new Set(said.map((s) => s.text))];
  return {
    text: texts.join(en ? "; " : " ; "),
    code,
    known: said.every((s) => s.known),
  };
}

function isLetter(ch) {
  return Boolean(ch) && /\p{L}/u.test(ch);
}

/** First whole-phrase hit (not glued to a letter on either side), or -1. */
function phraseAt(text, phrase) {
  let from = 0;
  for (;;) {
    const at = text.indexOf(phrase, from);
    if (at < 0) return -1;
    if (!isLetter(text[at - 1]) && !isLetter(text[at + phrase.length])) return at;
    from = at + 1;
  }
}

/**
 * Hang each code on the words that say it, in the plain spans of the briefing
 * (places and source links stay as they are). The text never changes:
 * the joined segments still equal `narrateIci()`. `reasons` come in the order
 * the briefing wrote them; a phrase not found is skipped.
 */
export function markReasons(segments, reasons) {
  const out = [...(segments || [])];
  // Cursor: each reason is looked for after the previous one, in writing order.
  let start = 0;
  for (const r of reasons || []) {
    if (!r?.code || !r.text) continue;
    for (let i = start; i < out.length; i += 1) {
      const seg = out[i];
      if (seg.entity || seg.reason) continue;
      const at = phraseAt(seg.text, r.text);
      if (at < 0) continue;
      const end = at + r.text.length;
      const parts = [];
      if (at > 0) parts.push({ text: seg.text.slice(0, at) });
      parts.push({ text: r.text, reason: { code: r.code } });
      if (end < seg.text.length) parts.push({ text: seg.text.slice(end) });
      out.splice(i, 1, ...parts);
      start = i + (at > 0 ? 2 : 1);
      break;
    }
  }
  return out;
}
