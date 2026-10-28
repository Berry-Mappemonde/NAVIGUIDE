import { haversineNm } from "../utils/geo.js";
import { castAtClock } from "./clockCast.js";

/**
 * Raccord entre chapitres : la tête de lecture ne saute plus.
 *
 * Le lecteur passe au chapitre suivant quand le texte est dit, pas quand le
 * bateau est arrivé. applyChapter pose alors la tête à `tA` du chapitre
 * suivant : sur l'horloge de production, Panamá → Papeete (≈ 4 400 milles)
 * en une image, et le vol Cayenne → Halifax entre deux images.
 *
 * filmGlideStep garde l'heure affichée continue : un pas qui déplacerait
 * l'acteur suivi de plus de FILM_GLIDE_JUMP_NM devient une glisse sur
 * l'horloge (bateau, avion, bateau B suivent leur route), de 250 ms pour
 * un petit raccord à FILM_GLIDE_MS pour un océan.
 * Le texte, lui, ne tient pas : seule l'image rattrape.
 */
export const FILM_GLIDE_JUMP_NM = 60;
export const FILM_GLIDE_MS = 1800;
/** Une glisse courte pour un petit raccord (≈ 100 milles), longue pour un océan. */
export const FILM_GLIDE_MIN_MS = 250;
export const FILM_GLIDE_MS_PER_NM = 0.6;

export function filmGlideMs(nm, maxMs = FILM_GLIDE_MS) {
  return Math.max(FILM_GLIDE_MIN_MS, Math.min(maxMs, nm * FILM_GLIDE_MS_PER_NM));
}

function followAt(clock, t) {
  const c = castAtClock(clock, t);
  const f = c?.follow;
  return f && Number.isFinite(f.lat) && Number.isFinite(f.lon) ? f : null;
}

/** Distance (milles) que l'acteur suivi parcourt entre deux heures de l'horloge. */
export function followJumpNm(clock, fromT, toT) {
  const a = followAt(clock, fromT);
  const b = followAt(clock, toT);
  if (!a || !b) return 0;
  return haversineNm(a.lat, a.lon, b.lat, b.lon);
}

/** Échantillons de l'heure dans une glisse : un vol de 5 h dans 4 jours reste visible. */
export const FILM_GLIDE_SAMPLES = 240;

/**
 * Table (heure, milles cumulés de l'acteur suivi) entre deux heures. La glisse
 * avance à vitesse constante en MILLES, pas en heures : sinon le vol
 * Cayenne → Halifax tient dans une ou deux images d'une glisse de quatre jours.
 */
function glideTable(clock, fromT, toT, n = FILM_GLIDE_SAMPLES) {
  const ts = [];
  const cum = [];
  let prev = null;
  let total = 0;
  for (let i = 0; i <= n; i++) {
    const t = fromT + ((toT - fromT) * i) / n;
    const p = followAt(clock, t);
    if (prev && p) total += haversineNm(prev.lat, prev.lon, p.lat, p.lon);
    if (p) prev = p;
    ts.push(t);
    cum.push(total);
  }
  return { ts, cum, total };
}

function timeAtShare(table, share) {
  const { ts, cum, total } = table;
  if (!(total > 0)) return ts[0] + (ts[ts.length - 1] - ts[0]) * share;
  const goal = share * total;
  let lo = 0;
  let hi = cum.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (cum[mid] < goal) lo = mid; else hi = mid;
  }
  const span = cum[hi] - cum[lo];
  const u = span > 0 ? (goal - cum[lo]) / span : 1;
  return ts[lo] + (ts[hi] - ts[lo]) * Math.max(0, Math.min(1, u));
}

/**
 * Un pas de la tête de lecture.
 * @param {object|null} state glisse en cours ou null
 * @returns {{ t: number, state: object|null }}
 */
export function filmGlideStep(state, {
  fromT,
  toT,
  nowMs,
  clock,
  jumpNm = FILM_GLIDE_JUMP_NM,
  durationMs = FILM_GLIDE_MS,
} = {}) {
  const to = Number(toT);
  if (!Number.isFinite(to)) return { t: toT, state: null };
  const from = Number(fromT);
  if (state) {
    // Retour en arrière (Stop, relance) : on lâche la glisse.
    if (to < state.fromT) return { t: to, state: null };
    const u = Math.max(0, Math.min(1, (nowMs - state.startedAt) / Math.max(1, state.durationMs)));
    if (u >= 1) return { t: Math.max(state.toT, to), state: null };
    const e = u * u * (3 - 2 * u);
    // La cible a pu avancer pendant la glisse (le chapitre suivant joue déjà) :
    // la table reste celle du saut ; au bout, on rejoint la tête demandée.
    return { t: timeAtShare(state.table, e), state };
  }
  if (!Number.isFinite(from) || !clock || to <= from) return { t: to, state: null };
  const jump = followJumpNm(clock, from, to);
  if (jump <= jumpNm) return { t: to, state: null };
  const table = glideTable(clock, from, to);
  return {
    t: from,
    state: {
      fromT: from,
      toT: to,
      startedAt: nowMs,
      durationMs: filmGlideMs(Math.max(jump, table.total), durationMs),
      table,
    },
  };
}
