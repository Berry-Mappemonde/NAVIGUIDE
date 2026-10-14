import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DEFAULT_SECONDS_PER_DAY, FILM_TARGET_SECONDS, MIN_CARD_MS, FILM_RECALE_MS, cardDwellMs, measuredCps, cardsBetween, chapterAtElapsed, chapterZoomEstimate, filmChaptersFromStory, filmPlan, journalTimeline, nextMovingTime, positionAt, publishFilmEnd, publishFilmStart, replayProgress, replaySample, replayWindow, sentenceIsStationary, sentenceSpan, stepFilmTime, trimQueue, voiceShouldWait,
} from "../engine/replay.js";
import { FILM_UI_MS } from "../map/filmCamera.js";
import { buildFilmScript } from "../engine/expeditionStory.js";
import {
  DEFAULT_T0_ISO,
  etaHoursToFilmNm,
  formatFilmClockLine,
  rebaseIso,
} from "../engine/voyageClock.js";
import { canLeadWithVoice, stopSpeaking, waitForVoices, voiceEndKind } from "../utils/speak.js";
import { EventBubbleGate, FilmEventScoreGate, filmEventCard, pickFilmEvent, publishEventBubble } from "../components/eventBubble.js";

const API = import.meta.env?.VITE_API_URL ?? "";

export function chapterHasLeg(ch) {
  return [ch?.fromLat, ch?.fromLon, ch?.toLat, ch?.toLon].every((n) => (
    n != null && n !== "" && Number.isFinite(Number(n))
  ));
}

/** Script remote : on garde le texte serveur ; lat/lon manquants viennent du local. */
/** Le script distant ne vaut que s'il porte l'année du t0 demandé (lot RD5). */
/**
 * Ligne d'état Suivre : mêmes milles et heures de mer (durées réelles),
 * date civile décalée vers le t0 choisi. Identité si t0 = départ officiel.
 * Ne touche pas au t0 Simulation.
 */
export function followClockLineFromT0({
  sailNm,
  seaHours,
  iso,
  fromT0 = DEFAULT_T0_ISO,
  t0 = DEFAULT_T0_ISO,
  lang = "fr",
} = {}) {
  return formatFilmClockLine({
    sailNm,
    seaHours,
    iso: rebaseIso(iso, fromT0, t0),
    lang,
  });
}

/** ETA / restants : heures d'horloge, indépendantes du t0 Simulation. */
export function followEtaFromClock(clock, fromFilmNm, toFilmNm, { atQuay = false } = {}) {
  return etaHoursToFilmNm(clock, fromFilmNm, toFilmNm, { atQuay });
}

export function filmTextHasT0Year(chapters, t0) {
  const year = new Date(t0 || "").getUTCFullYear();
  if (!Number.isFinite(year)) return true;
  const text = String(chapters?.[0]?.text || "");
  if (!text) return false;
  return text.includes(String(year));
}

const RE7_STALE = /Bay of Biscay|milles nautiques du départ|station croisée\s*:\s*Station croisée|Aucun port d'entr[ée]e|entrée dans Entrée dans/i;

/** Au-delà : ready seulement avec l'empreinte RG6/RG7 (intégral long, lot RC21). */
export const FILM_READY_MAX_WORDS = 800;

const RG6_OPENING = /Berry-Mappemonde quitte|L['’]expédition Berry-Mappemonde|Berry-Mappemonde leaves|The Berry-Mappemonde expedition/i;
const RG6_MILES_DAYS = /milles|jours de mer|days at sea|\bmiles\b/i;
const RG7_CLOSE = /Aujourd['’]hui, le bateau|Today, the boat/i;

export function filmWordCount(text) {
  return (String(text || "").match(/\S+/g) || []).length;
}

/** Ouverture RG6/RG7 + milles/jours, ou clôture « Aujourd'hui, le bateau ». */
export function filmHasRg6Rg7Fingerprint(text) {
  const blob = String(text || "");
  if (RG7_CLOSE.test(blob)) return true;
  return RG6_OPENING.test(blob) && RG6_MILES_DAYS.test(blob);
}

export function isRe7OfficialFilm(data) {
  const chapters = data?.chapters || [];
  if (!chapters.length) return false;
  const blob = chapters.map((c) => c.text || "").join(" ");
  if (RE7_STALE.test(blob)) return false;
  if (filmWordCount(blob) <= FILM_READY_MAX_WORDS) return true;
  return filmHasRg6Rg7Fingerprint(blob);
}

/** pending | ready | stale | empty | absent */
export function officialFilmStatus(data, { fetchFailed = false } = {}) {
  if (fetchFailed) return "absent";
  if (isRe7OfficialFilm(data)) return "ready";
  if (data?.chapters?.length) return "stale";
  if (data == null) return "pending";
  return "empty";
}

/**
 * Revoir en Suivre : horloge officielle + /film RE7 de ce checkout.
 * absent / pending / stale / empty : pas de repli Simulation (plus de
 * récit La Rochelle → Ajaccio sur un HTTP 500).
 */
export function canStartOfficialReplay({
  requireOfficialFilm = true,
  officialClock = null,
  fallbackClock = null,
  remoteStatus = "pending",
} = {}) {
  if (!requireOfficialFilm) return Boolean(officialClock || fallbackClock);
  if (remoteStatus === "ready") return Boolean(officialClock);
  return false;
}

export function pickFilmChapters(remote, local, fallback = []) {
  const r = remote?.chapters || [];
  const l = local?.chapters || [];
  if (r.length) {
    return {
      chapters: r.map((ch) => {
        if (chapterHasLeg(ch)) return ch;
        const src = l.find((c) => c.id && c.id === ch.id)
          || l.find((c) => c.fromName && ch.fromName && c.fromName === ch.fromName && c.toName === ch.toName);
        return src && chapterHasLeg(src)
          ? { ...ch, fromLat: src.fromLat, fromLon: src.fromLon, toLat: src.toLat, toLon: src.toLon }
          : ch;
      }),
      source: remote.source || "rules",
      remote: true,
    };
  }
  if (l.length) return { chapters: l, source: local.source || "rules", remote: false };
  return { chapters: fallback, source: "rules", remote: false };
}

/** onend immédiat sans boundary : une relance, puis linéaire, film non terminé. */
export function voiceLeadPolicy({
  hadBoundary,
  elapsedMs,
  alreadyRetried,
  chapterIdx = 0,
  chapterCount = 1,
  hasMoreChunks = false,
} = {}) {
  const kind = voiceEndKind({ hadBoundary, elapsedMs, alreadyRetried, hasMoreChunks });
  if (kind === "retry") return { mode: "retry", finish: false, chapterIdx };
  if (kind === "linear") return { mode: "linear", finish: false, chapterIdx };
  const last = chapterIdx + 1 >= chapterCount;
  return { mode: "advance", finish: last && !hasMoreChunks, chapterIdx: last ? chapterIdx : chapterIdx + 1 };
}

/**
 * Caméra live (Polynésie) seulement si le film est vraiment fini
 * ou si le porteur a cliqué Stop — jamais sur un incident de voix.
 */
export function shouldReturnToLive({ userStopped = false, filmFinished = false, voiceIncident = false } = {}) {
  if (voiceIncident && !userStopped && !filmFinished) return false;
  return Boolean(userStopped || filmFinished);
}

/** Avance linéaire : le dernier chapitre est atteint à la durée parlée, pas avant. */
/** Pas de frontière 2 s après le début d’un chapitre : synthèse considérée absente (RG9 / E2). */
export const FILM_VOICE_STALL_MS = 2000;
/** Onglet caché → reprise : le bateau rejoint la voix en au plus 2 s, sans saut (RG9 / E3). */
export const FILM_VISIBILITY_CATCHUP_MS = 2000;

/** Part du récit déjà dite (0..1) : caractères prononcés / caractères du film. */
export function spokenProgress(plan, chapterIdx, charIdx) {
  const list = plan?.chapters || [];
  const total = list.reduce((s, c) => s + (Number(c.chars) || 0), 0);
  if (!total) return 0;
  const i = Math.max(0, Math.min(list.length - 1, Number(chapterIdx) || 0));
  let before = 0;
  for (let k = 0; k < i; k += 1) before += Number(list[k].chars) || 0;
  const cur = Math.max(0, Math.min(Number(list[i]?.chars) || 0, Number(charIdx) || 0));
  return Math.max(0, Math.min(1, (before + cur) / total));
}

export function linearFilmAt(elapsed, plan) {
  const t = Number(elapsed) || 0;
  const total = filmSpeakChars(plan);
  const speakSec = total > 0 ? total / FILM_ESTIMATE_CPS : (Number(plan?.targetSeconds) || 0);
  const spoken = total > 0 ? Math.min(total, Math.max(0, t) * FILM_ESTIMATE_CPS) : 0;
  const ch = total > 0 ? chapterAtSpokenChars(plan, spoken) : chapterAtElapsed(plan, t);
  const lastIdx = Math.max(0, (plan?.chapters?.length || 1) - 1);
  const lastReached = (ch?.idx ?? 0) >= lastIdx;
  const allSpoken = total <= 0 || t + 1e-6 >= speakSec;
  return {
    chapterIdx: ch?.idx ?? 0,
    charIdx: ch?.localCharIdx ?? 0,
    finish: speakSec > 0 && t >= speakSec && lastReached && allSpoken,
    lastReached,
  };
}

/** ~ FILM_BUDGET_CHARS / 150 s : la voix ne meuble pas, le temps suit le texte. */
export const FILM_CHARS_PER_SECOND = 16;
/** Débit d'estimation (RG8) = débit vocal constant depuis le 27 sept. Pas de recalibrage. */
export const FILM_ESTIMATE_CPS = 15;

export function filmSpeakChars(plan) {
  const listed = Number(plan?.totalChars);
  if (Number.isFinite(listed) && listed > 0) return listed;
  return (plan?.chapters || []).reduce(
    (s, c) => s + (Number(c.chars) || String(c?.text || "").length || 0),
    0,
  );
}

export function wallClockSpeakSeconds(plan, cps = FILM_ESTIMATE_CPS) {
  const chars = filmSpeakChars(plan);
  const rate = Number(cps) > 0 ? Number(cps) : FILM_ESTIMATE_CPS;
  if (chars > 0 && rate > 0) return chars / rate;
  return Number(plan?.targetSeconds) || 0;
}

export function chapterAtSpokenChars(plan, spokenChars) {
  const list = plan?.chapters || [];
  if (!list.length) return null;
  let acc = 0;
  const x = Math.max(0, Number(spokenChars) || 0);
  for (const ch of list) {
    const n = Math.max(1, Number(ch.chars) || String(ch.text || "").length || 1);
    if (x < acc + n - 1e-9) {
      return { ...ch, localCharIdx: x - acc };
    }
    acc += n;
  }
  const last = list[list.length - 1];
  return { ...last, localCharIdx: Math.max(1, Number(last.chars) || 1) };
}

export function visibilityCatchupStep({
  fromT,
  toT,
  elapsedMs = 0,
  durationMs = FILM_VISIBILITY_CATCHUP_MS,
} = {}) {
  const from = Number(fromT);
  const to = Number(toT);
  const d = Math.max(1, Number(durationMs) || FILM_VISIBILITY_CATCHUP_MS);
  const u = Math.max(0, Math.min(1, (Number(elapsedMs) || 0) / d));
  const e = 1 - (1 - u) * (1 - u);
  const fallback = Number.isFinite(to) ? to : from;
  const t = Number.isFinite(from) && Number.isFinite(to)
    ? from + (to - from) * e
    : fallback;
  return { t, u, done: u >= 1 };
}

export function filmSpeakSeconds(chapters) {
  const chars = (chapters || []).reduce((s, c) => s + String(c?.text || "").length, 0);
  return Math.max(1, Math.round(chars / FILM_CHARS_PER_SECOND));
}

export function filmEstimatedSeconds(chars, cps = FILM_ESTIMATE_CPS) {
  const n = Number(chars) || 0;
  if (n <= 0) return 0;
  const rate = Number(cps) > 0 ? Number(cps) : FILM_ESTIMATE_CPS;
  return Math.max(1, Math.round(n / rate));
}

export function formatFilmEstimateClock(seconds) {
  const s = Math.max(0, Math.round(Number(seconds) || 0));
  if (!s) return "";
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, "0")}`;
}

export function pickFilmEstimateSeconds(targetSeconds, estimates, fallbackSeconds = 0) {
  const key = String(Number(targetSeconds) || 0);
  const map = estimates && typeof estimates === "object" ? estimates : null;
  const row = map?.[key] || map?.fr?.[key];
  const fromMap = Number(row?.estimatedSeconds);
  if (Number.isFinite(fromMap) && fromMap > 0) return fromMap;
  const fb = Number(fallbackSeconds);
  return Number.isFinite(fb) && fb > 0 ? fb : 0;
}

/** Même langue / style / t0 : un changement de budget 2:30↔3:00 ne démonte pas les pilules. */
export function filmQueryKeepsReady(prev, next) {
  if (!prev || !next) return false;
  if (prev === next) return true;
  const strip = (q) => String(q).replace(/seconds=[^&]*/, "seconds=");
  return strip(prev) === strip(next);
}

/** Durée cochée → budget ; aucune → le temps que prend le journal. */
export function resolveFilmTargetSeconds(selected, chapters) {
  const n = Number(selected);
  if (Number.isFinite(n) && n > 0) return n;
  return filmSpeakSeconds(chapters);
}

/** Re-clic sur la même durée = décoché (0). */
export function toggleFilmDuration(current, clicked) {
  const a = Number(current);
  const b = Number(clicked);
  if (Number.isFinite(a) && Number.isFinite(b) && a === b) return 0;
  return Number.isFinite(b) && b > 0 ? b : 0;
}

/** Budget coché : on attend la fin du budget, même si la voix a fini (KO #302). */
export function shouldHoldFilmForBudget({
  userBudget = 0, wallElapsed = 0, lastChapter = false,
} = {}) {
  return Boolean(lastChapter) && Number(userBudget) > 0 && Number(wallElapsed) < Number(userBudget);
}

export const APPROACH_FRAC = 0.8;

/**
 * Stop du film (lot RA5) : coupe la voix, libère la caméra (fin de
 * `filmActive` + `publishFilmEnd`), annule la boucle. L'appelant remet
 * `active=false` — MapSceneController quitte alors le suivi film.
 */
/** Dernière phrase de clôture, pour qu'elle reste lisible après l'arrêt (ligne tronquée). */
export function closingSubtitle(text) {
  const parts = String(text || "").split(/(?<=[.!?…])\s+/).filter(Boolean);
  const last = parts[parts.length - 1] || "";
  if (/aujourd|today/i.test(last)) return last;
  return String(text || "");
}

/** Phrases avion RF5 déjà présentes dans le chapitre — on ne les invente pas. */
export const FILM_AIR_PHRASE_RE =
  /prend l[''']avion pour|the crew flies to|retour en avion vers|return flight to/i;

/**
 * Ligne visible du sous-titre (lot RC16) : si le chapitre contient les
 * phrases avion RF5, on les montre ; sinon le texte du chapitre inchangé.
 */
export function visibleFilmSubtitle(text) {
  const raw = String(text || "").trim();
  if (!raw) return "";
  if (!FILM_AIR_PHRASE_RE.test(raw)) return raw;
  const airSentence = /[^.!?…\n]*?(?:prend l[''']avion pour|the crew flies to|retour en avion vers|return flight to)[^.!?…]*(?:[.!?…]|$)/gi;
  const found = raw.match(airSentence) || [];
  const parts = [];
  const seen = new Set();
  for (const piece of found) {
    const s = piece.trim();
    if (!s) continue;
    const key = s.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    parts.push(s);
  }
  return parts.length ? parts.join(" ") : raw;
}

export function filmSubtitleShowsAir(text) {
  return FILM_AIR_PHRASE_RE.test(String(text || ""));
}

export function splitFilmSentences(text, starts) {
  const raw = String(text || "");
  if (!raw) return [];
  const given = Array.isArray(starts)
    ? starts.map(Number).filter((n) => Number.isFinite(n) && n >= 0).sort((a, b) => a - b)
    : [];
  if (given.length) {
    const out = [];
    for (let i = 0; i < given.length; i += 1) {
      const a = given[i];
      const b = i + 1 < given.length ? given[i + 1] : raw.length;
      const piece = raw.slice(a, b);
      if (piece.trim()) out.push({ start: a, text: piece.trim() });
    }
    return out;
  }
  const parts = raw.split(/(?<=[.!?…])\s+/).filter(Boolean);
  const out = [];
  let from = 0;
  for (const p of parts) {
    const at = raw.indexOf(p, from);
    const start = at >= 0 ? at : from;
    out.push({ start, text: p });
    from = start + p.length;
  }
  return out;
}

export function filmSentenceAt(text, charIdx, starts) {
  const sentences = splitFilmSentences(text, starts);
  if (!sentences.length) return { start: 0, text: String(text || "") };
  const x = Math.max(0, Number(charIdx) || 0);
  let cur = sentences[0];
  for (const s of sentences) {
    if (x >= s.start) cur = s;
    else break;
  }
  return cur;
}

function spokenPlaceName(name) {
  return String(name || "").replace(/\s*\([^)]*\)\s*/g, " ").replace(/\s+/g, " ").trim();
}

export function filmPlaceInSentence(sentence, {
  fromName = "",
  toName = "",
  anchors = [],
  charIdx = 0,
} = {}) {
  const text = sentence?.text || "";
  const origin = Number(sentence?.start) || 0;
  const names = [];
  const push = (n) => {
    const s = spokenPlaceName(n);
    if (s && s.length >= 2 && !names.includes(s)) names.push(s);
  };
  push(toName);
  push(fromName);
  for (const a of anchors || []) {
    if (a?.name) push(a.name);
    if (a?.place) push(a.place);
  }
  names.sort((a, b) => b.length - a.length);
  const x = Math.max(0, Number(charIdx) || 0);
  for (const name of names) {
    const at = text.indexOf(name);
    if (at < 0) continue;
    if (x + 1e-9 < origin + at) continue;
    return { name, start: at, end: at + name.length };
  }
  return null;
}

export function filmSubtitleAt(text, charIdx, opts = {}) {
  const starts = opts.sentenceStarts || opts.sentences;
  const sentence = filmSentenceAt(text, charIdx, starts);
  const place = filmPlaceInSentence(sentence, { ...opts, charIdx });
  return {
    sentence: sentence.text,
    start: sentence.start,
    place: place?.name || "",
    placeStart: place?.start ?? -1,
    placeEnd: place?.end ?? -1,
  };
}

/**
 * Ligne de la barre : une phrase dès charIdx=0 (lot RC23 / revue #413).
 * Seek et pinned : la phrase sous le curseur, jamais le chapitre entier.
 * Extrait avion RC16 : les phrases « avion » / « flies » déjà dans le
 * chapitre (aller et retour), jamais le reste du chapitre.
 */
export function filmBarSubtitle({
  chapterText = "",
  charIdx = 0,
  pinned: _pinned = false,
  sentenceStarts,
  fromName,
  toName,
  anchors,
} = {}) {
  const raw = String(chapterText || "");
  if (!raw) return { text: "", place: "", sentenceMode: false };
  if (FILM_AIR_PHRASE_RE.test(raw)) {
    return { text: visibleFilmSubtitle(raw), place: "", sentenceMode: true };
  }
  const x = Math.max(0, Number(charIdx) || 0);
  const sub = filmSubtitleAt(raw, x, { sentenceStarts, fromName, toName, anchors });
  return { text: sub.sentence, place: sub.place, sentenceMode: true };
}

export function filmSubtitleHighlight(text, place) {
  const raw = String(text || "");
  const name = String(place || "");
  if (!raw || !name) return { before: raw, place: "", after: "" };
  const at = raw.indexOf(name);
  if (at < 0) return { before: raw, place: "", after: "" };
  return { before: raw.slice(0, at), place: name, after: raw.slice(at + name.length) };
}

export function applyReplayStop({
  cancelRaf,
  stopVoice,
  releaseCamera,
  keepChapterText = false,
  chapterText = "",
} = {}) {
  (stopVoice || stopSpeaking)();
  (releaseCamera || publishFilmEnd)();
  cancelRaf?.();
  const kept = keepChapterText ? closingSubtitle(chapterText) : "";
  return {
    active: false,
    tMs: null,
    card: null,
    progress: kept ? 1 : 0,
    chapterIdx: 0,
    chapterText: kept,
    filmLeg: null,
  };
}

function shortStopName(name) {
  return String(name || "").replace(/\s*\([^)]*\)\s*/g, " ").replace(/\s+/g, " ").trim();
}

/** Bulle à l'approche de l'escale d'arrivée du chapitre (affichage RA3 ; choix R9). */
export function approachStopEvent(chapter, { frac } = {}) {
  const name = shortStopName(chapter?.toName);
  if (!name) return null;
  const f = Number(frac);
  if (!(f >= APPROACH_FRAC)) return null;
  const arrival = String(chapter.text || "")
    .split(/(?<=[.!?])\s+/)
    .filter((s) => /arriv/i.test(s))
    .pop() || "";
  const id = `approach:${chapter.idx}:${name}`;
  return {
    id,
    kind: "stop",
    score: 3,
    card: {
      id,
      key: id,
      kind: "stop",
      title: name,
      text: arrival,
    },
  };
}

/** 60 frames linéaires : positions le long du trait, y compris le dernier chapitre. */
export function stepAlongPlan({ plan, clock, frames = 60, dt = 1 / 60, elapsed0 = 0 } = {}) {
  const positions = [];
  let elapsed = Number(elapsed0) || 0;
  for (let i = 0; i < frames; i++) {
    elapsed += dt;
    const linear = linearFilmAt(elapsed, plan);
    const ch = chapterAtElapsed(plan, elapsed);
    const frac = ch && ch.seconds > 0
      ? Math.max(0, Math.min(1, (elapsed - ch.startWall) / ch.seconds))
      : 1;
    const tMs = ch ? ch.tA + frac * (ch.tB - ch.tA) : plan.timeAt(0, 0);
    const pos = positionAt(clock, tMs);
    positions.push({
      ...(pos || {}),
      chapterIdx: ch?.idx ?? 0,
      tMs,
      finish: linear.finish,
      lastReached: linear.lastReached,
    });
  }
  return positions;
}

/**
 * « Revoir l'expédition » (lot E, cinématique F1 / fluide R4) : rejoue la
 * route de Saint-Maur à aujourd'hui. Le temps avance chaque frame ; la voix
 * recale vers timeAt(charIdx) en ≤ 300 ms. Sans voix, avance linéaire
 * continue sur 150 s (ou 180 s). `live` remplace le bateau officiel pendant
 * le film ; à la fin réelle ou sur Stop, retour au live — jamais sur
 * un incident de voix (lot RB6).
 */
export function useReplay({
  clock,
  fallbackClock = null,
  requireOfficialFilm = true,
  journal,
  enabled = false,
  lang = "fr",
  secondsPerDay = DEFAULT_SECONDS_PER_DAY,
  marks = [],
  destination = null,
  t0 = DEFAULT_T0_ISO,
} = {}) {
  const [active, setActive] = useState(false);
  const [tMs, setTMs] = useState(null);
  const [card, setCard] = useState(null);
  // Lot O — voice is piloted by the film-bar Écouter button (no replay-voice).
  const [voice, setVoice] = useState(true);
  const [targetSeconds, setTargetSeconds] = useState(0);
  const [chapterIdx, setChapterIdx] = useState(0);
  const [chapterText, setChapterText] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [subtitlePlace, setSubtitlePlace] = useState("");
  const [filmLeg, setFilmLeg] = useState(null);
  const [voiceRate, setVoiceRate] = useState(1);
  const [progress, setProgress] = useState(0);
  const [filmSource, setFilmSource] = useState("rules");
  const [filmStyle, setFilmStyle] = useState("raw");
  const [hasWritten, setHasWritten] = useState(false);
  const [estimatedSeconds, setEstimatedSeconds] = useState(0);
  const [variantEstimates, setVariantEstimates] = useState(null);
  const remotePlanRef = useRef(null);
  // Langue et budget du plan chargé : on ne garde le plan « prêt » pendant un rechargement que s'il
  // répond à la MÊME demande — sinon un clic Revoir juste après le passage en anglais jouait le film
  // français (spec rb5 / ra2 en CI, 28 sept.).
  const remotePlanKeyRef = useRef("");
  const [remoteStatus, setRemoteStatus] = useState("pending");
  const remoteStatusRef = useRef("pending");
  const setFilmStatus = useCallback((s) => {
    remoteStatusRef.current = s;
    setRemoteStatus(s);
  }, []);
  const pinnedIdxRef = useRef(null);
  const seekChapterRef = useRef(null);
  const queueRef = useRef([]);
  const cardSinceRef = useRef(0);
  const lastTRef = useRef(null);
  const rafRef = useRef(null);
  const timeline = useMemo(() => journalTimeline(journal), [journal]);
  const timelineRef = useRef(timeline);
  timelineRef.current = timeline;
  const windowRef = useRef(null);
  const planRef = useRef(null);
  const chapterIdxRef = useRef(0);
  const startWallRef = useRef(0);
  const chapterStartedAtRef = useRef(0);
  const finishedRef = useRef(false);
  const stoppingRef = useRef(false);
  const chapterTextRef = useRef("");
  const finishRef = useRef(() => {});
  const voiceCharRef = useRef(0);
  const voiceFailedRef = useRef(false);
  const voiceSpokenAllRef = useRef(false);
  const voiceBoundaryAtRef = useRef(0);
  const tMsRef = useRef(null);
  const voiceTargetRef = useRef(null);
  const recaleRemainRef = useRef(0);
  const voiceRef = useRef(voice);
  voiceRef.current = voice;
  const filmBubbleRef = useRef(new EventBubbleGate());
  const filmScoreRef = useRef(new FilmEventScoreGate());
  const publishedBubbleRef = useRef(null);
  const clockRef = useRef(clock);
  if (clock) clockRef.current = clock;
  const budgetRef = useRef(0);
  const lastUiAtRef = useRef(0);
  const hiddenRef = useRef(false);
  const hiddenTRef = useRef(null);
  const hiddenElapsedRef = useRef(0);
  const displayElapsedRef = useRef(0);
  const catchupRef = useRef(null);
  const lastSubtitleRef = useRef("");
  const lastBoundaryCharRef = useRef(0);
  const lastBoundaryAtRef = useRef(0);
  const voiceHoldRef = useRef(false);
  const phraseEndedRef = useRef(false);
  const skipRampRef = useRef(null);
  const filmElapsedRef = useRef(0);
  const linearHoldRef = useRef(false);

  const stop = useCallback((opts) => {
    const keep = Boolean(opts && opts.keepSubtitle);
    stoppingRef.current = true;
    finishedRef.current = true;
    pinnedIdxRef.current = null;
    filmBubbleRef.current.reset();
    filmScoreRef.current.reset();
    publishedBubbleRef.current = null;
    publishEventBubble(null);
    const cleared = applyReplayStop({
      cancelRaf: () => {
        if (rafRef.current) cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      },
      keepChapterText: keep,
      chapterText: keep ? chapterTextRef.current : "",
    });
    setActive(cleared.active);
    setTMs(cleared.tMs);
    setCard(cleared.card);
    setChapterIdx(cleared.chapterIdx);
    setChapterText(cleared.chapterText);
    chapterTextRef.current = cleared.chapterText || "";
    setSubtitle(cleared.chapterText || "");
    setSubtitlePlace("");
    lastSubtitleRef.current = cleared.chapterText || "";
    setFilmLeg(cleared.filmLeg);
    catchupRef.current = null;
    hiddenRef.current = false;
    setVoiceRate(1);
    setProgress(cleared.progress);
    queueRef.current = [];
    lastTRef.current = null;
    tMsRef.current = null;
    voiceTargetRef.current = null;
    recaleRemainRef.current = 0;
    lastBoundaryCharRef.current = 0;
    lastBoundaryAtRef.current = 0;
    voiceHoldRef.current = false;
    phraseEndedRef.current = false;
    skipRampRef.current = null;
    filmElapsedRef.current = 0;
    linearHoldRef.current = false;
    planRef.current = null;
  }, []);

  const applyChapter = useCallback((ch) => {
    if (!ch) return;
    chapterIdxRef.current = ch.idx;
    voiceCharRef.current = 0;
    voiceBoundaryAtRef.current = 0;
    chapterStartedAtRef.current = typeof performance !== "undefined" ? performance.now() : 0;
    voiceTargetRef.current = Number.isFinite(ch.tA) ? ch.tA : null;
    recaleRemainRef.current = 0;
    lastBoundaryCharRef.current = 0;
    lastBoundaryAtRef.current = typeof performance !== "undefined" ? performance.now() : 0;
    voiceHoldRef.current = false;
    phraseEndedRef.current = false;
    skipRampRef.current = null;
    if (Number.isFinite(ch.tA)) tMsRef.current = ch.tA;
    setChapterIdx(ch.idx);
    chapterTextRef.current = ch.text || "";
    setChapterText(ch.text || "");
    const first = filmBarSubtitle({
      chapterText: ch.text || "",
      charIdx: 0,
      pinned: pinnedIdxRef.current != null,
      sentenceStarts: ch.sentenceStarts,
      fromName: ch.fromName,
      toName: ch.toName,
      anchors: ch.anchors,
    });
    setSubtitle(first.text);
    setSubtitlePlace(first.place);
    lastSubtitleRef.current = first.text;
    setFilmLeg({
      fromLat: ch.fromLat, fromLon: ch.fromLon, toLat: ch.toLat, toLon: ch.toLon,
    });
  }, []);

  const finish = useCallback(() => {
    if (finishedRef.current || stoppingRef.current) return;
    if (!shouldReturnToLive({ filmFinished: true })) return;
    finishedRef.current = true;
    const w = windowRef.current;
    if (w) setTMs(w.endMs);
    setProgress(1);
    publishFilmEnd();
    setTimeout(() => stop({ keepSubtitle: true }), 400);
  }, [stop]);
  finishRef.current = finish;

  useEffect(() => {
    if (!enabled) return undefined;
    waitForVoices(typeof window !== "undefined" ? window : null, 1000);
    return undefined;
  }, [enabled]);

  useEffect(() => {
    if (!enabled) {
      setFilmStatus("pending");
      remotePlanRef.current = null;
      setEstimatedSeconds(0);
      setVariantEstimates(null);
      return undefined;
    }
    let cancelled = false;
    let retryTimer = 0;
    const ac = new AbortController();
    const style = filmStyle === "written" ? "written" : "raw";
    const q = `lang=${encodeURIComponent(lang)}&seconds=${encodeURIComponent(targetSeconds)}&style=${style}&t0=${encodeURIComponent(t0)}`;

    const applyEstimates = (data) => {
      const chapters = data?.chapters || [];
      const chars = Number(data?.chars) || chapters.reduce((n, c) => n + String(c?.text || "").length, 0);
      const est = Number(data?.estimatedSeconds) > 0
        ? Number(data.estimatedSeconds)
        : filmEstimatedSeconds(chars);
      setEstimatedSeconds(est);
      setVariantEstimates(data?.estimates && typeof data.estimates === "object" ? data.estimates : null);
    };

    const applyData = (data) => {
      if (cancelled) return true;
      if (isRe7OfficialFilm(data)) {
        remotePlanRef.current = data;
        remotePlanKeyRef.current = q;
        setHasWritten(Boolean(data.hasWritten));
        setFilmSource(data.source || "rules");
        applyEstimates(data);
        setFilmStatus("ready");
        return true;
      }
      if (data?.chapters?.length) {
        remotePlanRef.current = data;
        remotePlanKeyRef.current = q;
        applyEstimates(data);
        setFilmStatus("stale");
        return true;
      }
      return false;
    };

    const markAbsent = () => {
      remotePlanRef.current = null;
      setHasWritten(false);
      setFilmSource("rules");
      setEstimatedSeconds(0);
      setVariantEstimates(null);
      setFilmStatus("absent");
    };

    const load = () => {
      if (cancelled) return;
      const keepReady = remoteStatusRef.current === "ready" && remotePlanRef.current
        && filmQueryKeepsReady(remotePlanKeyRef.current, q);
      if (!keepReady) {
        setFilmStatus("pending");
        remotePlanRef.current = null;
      }
      fetch(`${API}/voyage/official/film?${q}`, { signal: ac.signal })
        .then((r) => {
          if (!r.ok) return { fail: true };
          return r.json().then((data) => ({ data })).catch(() => ({ fail: true }));
        })
        .then((pack) => {
          if (cancelled || ac.signal.aborted) return;
          if (!pack || pack.fail) {
            markAbsent();
            return;
          }
          if (applyData(pack.data)) return;
          setFilmStatus("empty");
          retryTimer = setTimeout(load, 2000);
        })
        .catch((err) => {
          if (err?.name === "AbortError" || cancelled || ac.signal.aborted) return;
          markAbsent();
        });
    };

    load();
    return () => {
      cancelled = true;
      ac.abort();
      clearTimeout(retryTimer);
    };
  }, [enabled, lang, targetSeconds, filmStyle, t0, setFilmStatus]);

  const canStart = canStartOfficialReplay({
    requireOfficialFilm,
    officialClock: clock,
    fallbackClock,
    remoteStatus,
  });

  const seekChapter = useCallback((idx) => {
    const plan = planRef.current;
    if (!plan?.chapters?.length) return false;
    const last = plan.chapters.length - 1;
    const n = Math.max(0, Math.min(last, Number(idx)));
    const ch = plan.chapters[n];
    if (!ch) return false;
    pinnedIdxRef.current = ch.idx;
    applyChapter(ch);
    const at = Number.isFinite(ch.tB) ? ch.tB : ch.tA;
    if (Number.isFinite(at)) {
      tMsRef.current = at;
      lastTRef.current = at;
      setTMs(at);
    }
    if (ch.idx >= last) setProgress(1);
    if (typeof window !== "undefined") {
      const prev = window.__naviguideFilm || {};
      window.__naviguideFilm = {
        ...prev,
        chapterIdx: ch.idx,
        chapterText: ch.text || "",
        chapterCount: plan.chapters.length,
      };
    }
    return true;
  }, [applyChapter]);
  seekChapterRef.current = seekChapter;

  const start = useCallback(() => {
    const status = remoteStatusRef.current;
    const remote = remotePlanRef.current;
    let clockToUse = clock;
    let remoteToUse = remote;
    if (requireOfficialFilm) {
      if (status === "ready" && isRe7OfficialFilm(remote) && clock) {
        clockToUse = clock;
        remoteToUse = remote;
      } else {
        return false;
      }
    }
    const w = replayWindow(clockToUse, Date.now());
    if (!w) return false;
    const local = buildFilmScript({
      clock: clockToUse,
      marks,
      live: destination,
      journal,
      lang,
      now: Date.now(),
      seconds: targetSeconds,
      t0,
    });
    const fallback = filmChaptersFromStory({
      clock: clockToUse,
      marks,
      live: destination,
      journal,
      lang,
      nowMs: Date.now(),
      t0,
    });
    const remoteOk = Boolean(
      remoteToUse?.chapters?.length
      && (isRe7OfficialFilm(remoteToUse) || filmTextHasT0Year(remoteToUse.chapters, t0)),
    );
    const picked = pickFilmChapters(remoteOk ? remoteToUse : null, local, fallback);
    const chapters = picked.chapters;
    setFilmSource(picked.source || local.source || "rules");
    const userBudget = Number(targetSeconds) > 0 ? Number(targetSeconds) : 0;
    budgetRef.current = userBudget;
    // Case décochée : pas de budget imposé (RD7), mais le plan tient 2:30 (F1).
    const planSeconds = userBudget > 0 ? userBudget : FILM_TARGET_SECONDS;
    const plan = filmPlan({ chapters, targetSeconds: planSeconds });
    if (!plan.chapters.length) return false;
    clockRef.current = clockToUse;
    pinnedIdxRef.current = null;
    windowRef.current = w;
    planRef.current = plan;
    queueRef.current = [];
    cardSinceRef.current = 0;
    lastTRef.current = plan.timeAt(0, 0);
    tMsRef.current = lastTRef.current;
    voiceTargetRef.current = lastTRef.current;
    recaleRemainRef.current = 0;
    lastBoundaryCharRef.current = 0;
    lastBoundaryAtRef.current = 0;
    voiceHoldRef.current = false;
    phraseEndedRef.current = false;
    skipRampRef.current = null;
    filmElapsedRef.current = 0;
    linearHoldRef.current = false;
    finishedRef.current = false;
    stoppingRef.current = false;
    startWallRef.current = 0;
    chapterStartedAtRef.current = 0;
    voiceCharRef.current = 0;
    voiceFailedRef.current = !canLeadWithVoice();
    voiceSpokenAllRef.current = false;
    voiceBoundaryAtRef.current = 0;
    catchupRef.current = null;
    hiddenRef.current = false;
    displayElapsedRef.current = 0;
    hiddenTRef.current = null;
    hiddenElapsedRef.current = 0;
    setVoiceRate(1);
    filmBubbleRef.current.reset();
    filmScoreRef.current.reset();
    publishedBubbleRef.current = null;
    publishEventBubble(null);
    setCard(null);
    applyChapter(plan.chapters[0]);
    setTMs(plan.timeAt(0, 0));
    setProgress(0);
    setActive(true);
    publishFilmStart(plan.targetSeconds);
    if (typeof window !== "undefined") {
      const prev = window.__naviguideFilm || {};
      window.__naviguideFilm = {
        ...prev,
        budgetSeconds: userBudget,
        chapterCount: plan.chapters.length,
        chapters: plan.chapters.map((c) => ({
          idx: c.idx,
          text: c.text || "",
          fromName: c.fromName || "",
          toName: c.toName || "",
        })),
        seekChapter: (idx) => seekChapterRef.current?.(idx),
        finishFilm: () => finishRef.current?.(),
      };
    }
    return true;
  }, [clock, requireOfficialFilm, marks, destination, journal, lang, targetSeconds, applyChapter, t0]);

  useEffect(() => {
    if (!enabled && active) stop();
  }, [enabled, active, stop]);

  const onVoiceBoundary = useCallback((charIdx) => {
    const plan = planRef.current;
    if (!plan || finishedRef.current) return;
    voiceCharRef.current = charIdx;
    voiceBoundaryAtRef.current = performance.now();
    lastBoundaryCharRef.current = charIdx;
    lastBoundaryAtRef.current = voiceBoundaryAtRef.current;
    const next = plan.timeAt(chapterIdxRef.current, charIdx);
    if (next == null) return;
    voiceTargetRef.current = next;
    recaleRemainRef.current = FILM_RECALE_MS;
  }, []);

  const onSentenceStart = useCallback((startChar) => {
    phraseEndedRef.current = false;
    voiceHoldRef.current = false;
    const at = Math.max(0, Number(startChar) || 0);
    voiceCharRef.current = at;
    lastBoundaryCharRef.current = at;
    lastBoundaryAtRef.current = typeof performance !== "undefined" ? performance.now() : 0;
    recaleRemainRef.current = 0;
  }, []);

  const onSentenceEnd = useCallback((endChar) => {
    phraseEndedRef.current = true;
    const plan = planRef.current;
    const ch = plan?.chapters?.[chapterIdxRef.current];
    if (!plan || !ch) return;
    const sent = sentenceSpan(ch, Math.max(0, (Number(endChar) || 1) - 1));
    const cur = tMsRef.current ?? sent.endT;
    const atQuay = Boolean(clockRef.current)
      && sentenceIsStationary(clockRef.current, sent.startT, sent.endT);
    const wait = voiceShouldWait({
      t: cur, sentenceEndT: sent.endT, phraseEnded: true, atQuay,
    });
    voiceHoldRef.current = Boolean(wait.wait);
    if (wait.skip && clockRef.current) {
      const toT = nextMovingTime(clockRef.current, ch, Math.max(cur, sent.endT));
      if (Number.isFinite(toT) && toT > cur + 50) {
        skipRampRef.current = {
          fromT: cur, toT, startedAt: performance.now(), durationMs: 1000,
        };
        voiceHoldRef.current = true;
      }
    }
  }, []);

  const isVoiceHeld = useCallback(() => voiceHoldRef.current, []);

  const onVoiceLeadFailed = useCallback(() => {
    if (stoppingRef.current || finishedRef.current) return;
    voiceFailedRef.current = true;
  }, []);

  const onVoiceEnd = useCallback(() => {
    const plan = planRef.current;
    if (!plan || finishedRef.current || stoppingRef.current) return;
    if (!voiceRef.current || voiceFailedRef.current || !canLeadWithVoice()) return;
    // E2 : onend sans mot dit → horloge murale, jamais finish() au chapitre 0.
    if (!(voiceBoundaryAtRef.current > 0 && voiceCharRef.current > 0)) {
      voiceFailedRef.current = true;
      return;
    }
    const idx = chapterIdxRef.current;
    // RG12 : pas de bond à tB — le gouverneur a déjà rejoint l'ancre, ou la rampe d'escale.
    const wallElapsed = startWallRef.current
      ? (performance.now() - startWallRef.current) / 1000
      : 0;
    // Débit constant (27 sept.) : on ne recalibre plus la voix pour tenir le budget — c'était
    // l'accélération audible après le premier chapitre. Le budget (2:30 / 3:00) choisit le TEXTE
    // côté serveur ; la durée réelle suit la voix, et le bateau suit la voix.
    if (idx + 1 >= plan.chapters.length) {
      if (shouldHoldFilmForBudget({
        userBudget: budgetRef.current,
        wallElapsed,
        lastChapter: true,
      })) {
        // Voix finie avant le budget : on tient la dernière image ; la boucle finira au budget.
        voiceSpokenAllRef.current = true;
        return;
      }
      finish();
      return;
    }
    chapterStartedAtRef.current = performance.now();
    applyChapter(plan.chapters[idx + 1]);
  }, [applyChapter, finish]);

  // The loop: wall clock → expedition time; journal lines passed → cards, one at a time.
  useEffect(() => {
    if (!active) return undefined;
    let prev = performance.now();
    const tick = (now) => {
      const dt = Math.min(200, now - prev);
      prev = now;
      if (startWallRef.current === 0) {
        startWallRef.current = now;
        chapterStartedAtRef.current = now;
      }
      const plan = planRef.current;
      const w = windowRef.current;
      if (!plan || !w || finishedRef.current) {
        rafRef.current = requestAnimationFrame(tick);
        return;
      }
      const wallElapsed = (now - startWallRef.current) / 1000;
      const catchup = catchupRef.current;
      let elapsed = wallElapsed;
      if (catchup) {
        const u = Math.max(0, Math.min(1, (now - catchup.startedAt) / Math.max(1, catchup.durationMs)));
        const ease = 1 - (1 - u) * (1 - u);
        elapsed = catchup.fromElapsed + (catchup.toElapsed - catchup.fromElapsed) * ease;
      } else if (!linearHoldRef.current) {
        filmElapsedRef.current += dt / 1000;
      }
      if (!catchup) elapsed = filmElapsedRef.current;
      displayElapsedRef.current = elapsed;
      const speakDenom = Math.max(wallClockSpeakSeconds(plan), Number(plan.targetSeconds) || 0, 1);
      const uiDue = now - lastUiAtRef.current >= FILM_UI_MS;
      if (!canLeadWithVoice()) {
        voiceFailedRef.current = true;
      }
      const chapterAge = chapterStartedAtRef.current ? now - chapterStartedAtRef.current : 0;
      if (
        voiceRef.current && !voiceFailedRef.current && !voiceSpokenAllRef.current
        && !voiceHoldRef.current
        && chapterAge >= FILM_VOICE_STALL_MS
        && (
          voiceBoundaryAtRef.current === 0
          || now - voiceBoundaryAtRef.current > FILM_VOICE_STALL_MS
        )
      ) {
        voiceFailedRef.current = true;
      }
      const voiceClock = Boolean(
        voiceRef.current
        && !voiceFailedRef.current
        && canLeadWithVoice(),
      );
      const voiceLed = Boolean(voiceClock && voiceCharRef.current > 0);
      if (uiDue) {
        lastUiAtRef.current = now;
        setProgress(voiceClock
          ? spokenProgress(plan, chapterIdxRef.current, voiceCharRef.current)
          : Math.max(0, Math.min(1, elapsed / speakDenom)));
      }

      const ingest = (next) => {
        if (next == null) return;
        const from = lastTRef.current ?? next;
        const fresh = cardsBetween(timelineRef.current, from, next, lang);
        if (fresh.length) queueRef.current = trimQueue([...queueRef.current, ...fresh]);
        lastTRef.current = next;
        tMsRef.current = next;
        if (uiDue) setTMs(next);
      };

      let charIdx = voiceCharRef.current;
      const linear = linearFilmAt(elapsed, plan);
      // E2 : fini seulement à la dernière phrase (horloge 15 car./s), jamais au budget
      // au milieu du récit ni sur un onend sans mot. Voix vraiment finie : on tient le budget.
      const voiceAllDone = Boolean(voiceSpokenAllRef.current) && (
        budgetRef.current <= 0 || wallElapsed >= plan.targetSeconds
      );
      const done = !stoppingRef.current && (
        voiceAllDone
        || (!voiceClock && linear.finish && linear.lastReached)
      );
      if (done) {
        const last = plan.chapters[plan.chapters.length - 1];
        ingest(last?.tB ?? w.endMs);
        finish();
      } else if (catchup) {
        const liveTarget = voiceClock && voiceCharRef.current > 0
          ? plan.timeAt(chapterIdxRef.current, voiceCharRef.current)
          : plan.timeAt(linear.chapterIdx, linear.charIdx);
        if (liveTarget != null) catchup.toT = liveTarget;
        const stepped = visibilityCatchupStep({
          fromT: catchup.fromT,
          toT: catchup.toT,
          elapsedMs: now - catchup.startedAt,
          durationMs: catchup.durationMs,
        });
        ingest(stepped.t);
        if (!voiceClock) {
          const ch = pinnedIdxRef.current != null
            ? plan.chapters[pinnedIdxRef.current]
            : plan.chapters[linear.chapterIdx];
          if (ch && ch.idx !== chapterIdxRef.current) applyChapter(ch);
          charIdx = pinnedIdxRef.current != null ? (ch?.chars || 1) : linear.charIdx;
        }
        if (stepped.done) {
          catchupRef.current = null;
          filmElapsedRef.current = wallElapsed;
        }
      } else if (!voiceClock) {
        const pinned = pinnedIdxRef.current;
        const ch = pinned != null ? plan.chapters[pinned] : plan.chapters[linear.chapterIdx];
        if (ch && ch.idx !== chapterIdxRef.current) applyChapter(ch);
        if (pinned != null && ch) {
          charIdx = ch.chars || 1;
          ingest(Number.isFinite(ch.tB) ? ch.tB : plan.timeAt(0, 0));
        } else {
          charIdx = linear.charIdx;
          const sent = sentenceSpan(ch, charIdx);
          const phraseEnded = Boolean(ch) && charIdx + 1e-6 >= sent.end;
          const cur = tMsRef.current ?? lastTRef.current ?? ch?.tA;
          const mapZoom = typeof window !== "undefined"
            ? Number(window.__naviguideScene?.map?.getZoom?.())
            : NaN;
          const stepped = stepFilmTime({
            t: cur,
            dt: dt / 1000,
            chapter: ch,
            plan,
            chapterIdx: ch?.idx ?? 0,
            charIdx,
            clock: clockRef.current,
            zoom: Number.isFinite(mapZoom) ? mapZoom : chapterZoomEstimate(ch),
            lat: ch?.fromLat,
            voiceLed: false,
            phraseEnded,
            skipRamp: skipRampRef.current,
            nowMs: now,
          });
          skipRampRef.current = stepped.skipRamp;
          linearHoldRef.current = Boolean(stepped.voiceHold);
          voiceHoldRef.current = Boolean(stepped.voiceHold);
          ingest(stepped.t);
        }
      } else {
        const ch = plan.chapters[chapterIdxRef.current];
        const cur = tMsRef.current ?? lastTRef.current ?? ch?.tA;
        const mapZoom = typeof window !== "undefined"
          ? Number(window.__naviguideScene?.map?.getZoom?.())
          : NaN;
        const since = lastBoundaryAtRef.current
          ? (now - lastBoundaryAtRef.current) / 1000
          : 0;
        const stepped = stepFilmTime({
          t: cur,
          dt: dt / 1000,
          chapter: ch,
          plan,
          chapterIdx: chapterIdxRef.current,
          charIdx: voiceCharRef.current,
          cps: measuredCps(voiceCharRef.current, chapterStartedAtRef.current ? now - chapterStartedAtRef.current : 0),
          lastBoundaryChar: lastBoundaryCharRef.current,
          sinceBoundaryS: since,
          recaleRemainMs: recaleRemainRef.current,
          clock: clockRef.current,
          zoom: Number.isFinite(mapZoom) ? mapZoom : chapterZoomEstimate(ch),
          lat: ch?.fromLat,
          voiceLed: true,
          phraseEnded: phraseEndedRef.current,
          skipRamp: skipRampRef.current,
          nowMs: now,
        });
        recaleRemainRef.current = stepped.recaleRemainMs;
        skipRampRef.current = stepped.skipRamp;
        voiceHoldRef.current = Boolean(stepped.voiceHold);
        ingest(stepped.t);
      }

      const chapter = plan.chapters[chapterIdxRef.current];
      const sub = filmBarSubtitle({
        chapterText: chapter?.text || "",
        charIdx,
        pinned: pinnedIdxRef.current != null,
        sentenceStarts: chapter?.sentenceStarts,
        fromName: chapter?.fromName,
        toName: chapter?.toName,
        anchors: chapter?.anchors,
      });
      if (uiDue && sub.text !== lastSubtitleRef.current) {
        lastSubtitleRef.current = sub.text;
        setSubtitle(sub.text);
        setSubtitlePlace(sub.place);
      } else if (uiDue) {
        setSubtitlePlace(sub.place);
      }
      const span = chapter && Number.isFinite(chapter.tB - chapter.tA) ? (chapter.tB - chapter.tA) : 0;
      const approachFrac = span > 0
        ? Math.max(0, Math.min(1, (lastTRef.current - chapter.tA) / span))
        : (charIdx / (chapter?.chars || 1));
      if (typeof window !== "undefined" && publishedBubbleRef.current && !window.__naviguideEventBubble) {
        filmBubbleRef.current.dismiss();
        publishedBubbleRef.current = null;
        setCard(null);
      }
      const filmEv = pickFilmEvent({
        chapter,
        charIdx,
        tMs: lastTRef.current,
        voiceLed,
        plan,
      }) || approachStopEvent(chapter, { frac: approachFrac });
      const accepted = filmScoreRef.current.accept(filmEv);
      const shown = filmBubbleRef.current.propose(filmEventCard(accepted));
      if (shown !== publishedBubbleRef.current) {
        publishedBubbleRef.current = shown;
        if (shown) {
          cardSinceRef.current = now;
          setCard(shown);
        }
        publishEventBubble(shown);
      }
      if (typeof window !== "undefined") {
        const pos = positionAt(clockRef.current, lastTRef.current);
        const sample = replaySample(clockRef.current, lastTRef.current, timelineRef.current);
        const prevFilm = window.__naviguideFilm || {};
        window.__naviguideFilm = {
          ...prevFilm,
          chapterIdx: chapterIdxRef.current,
          chapterText: chapter?.text || prevFilm.chapterText || "",
          subtitle: sub.text,
          subtitlePlace: sub.place,
          chapterCount: plan.chapters.length,
          elapsed,
          charIdx,
          tMs: lastTRef.current,
          lat: pos?.lat ?? sample?.lat ?? null,
          lon: pos?.lon ?? sample?.lon ?? null,
          heading: sample?.bearing ?? prevFilm.heading ?? null,
          filmNm: pos?.filmNm ?? sample?.filmNm ?? null,
          bubbleId: shown ? (shown.key || shown.id || null) : null,
          bubbleKind: shown?.kind || null,
          seekChapter: prevFilm.seekChapter || ((idx) => seekChapterRef.current?.(idx)),
          finishFilm: prevFilm.finishFilm || (() => finishRef.current?.()),
        };
      }

      // Card rotation: journal lines fill the sidebar only when no chapter
      // event is on screen — the bubble and the NOW card stay the same text.
      if (!shown && queueRef.current.length && now - cardSinceRef.current >= cardDwellMs(queueRef.current.length)) {
        const nextCard = queueRef.current.shift();
        cardSinceRef.current = now;
        setCard(nextCard);
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    };
  }, [active, secondsPerDay, lang, stop, finish, applyChapter]);

  useEffect(() => {
    if (!active || typeof document === "undefined") return undefined;
    const onVis = () => {
      const now = typeof performance !== "undefined" ? performance.now() : Date.now();
      const plan = planRef.current;
      if (document.hidden) {
        hiddenRef.current = true;
        hiddenTRef.current = tMsRef.current;
        hiddenElapsedRef.current = displayElapsedRef.current;
        return;
      }
      if (!hiddenRef.current) return;
      hiddenRef.current = false;
      const wallElapsed = startWallRef.current ? (now - startWallRef.current) / 1000 : 0;
      const fromT = hiddenTRef.current ?? tMsRef.current;
      const fromElapsed = hiddenElapsedRef.current ?? displayElapsedRef.current ?? wallElapsed;
      let toT = tMsRef.current;
      if (plan) {
        const voiceClock = Boolean(
          voiceRef.current && !voiceFailedRef.current && canLeadWithVoice(),
        );
        if (voiceClock && voiceCharRef.current > 0) {
          const next = plan.timeAt(chapterIdxRef.current, voiceCharRef.current);
          if (next != null) toT = next;
        } else {
          const linear = linearFilmAt(wallElapsed, plan);
          const next = plan.timeAt(linear.chapterIdx, linear.charIdx);
          if (next != null) toT = next;
        }
      }
      catchupRef.current = {
        fromT,
        toT,
        fromElapsed,
        toElapsed: wallElapsed,
        startedAt: now,
        durationMs: FILM_VISIBILITY_CATCHUP_MS,
      };
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, [active]);

  const live = useMemo(() => (active && tMs != null ? replaySample(clock, tMs, timeline) : null), [active, tMs, clock, timeline]);
  const clockProgress = active && tMs != null ? replayProgress(tMs, windowRef.current) : 0;

  const dismissCard = useCallback(() => {
    filmBubbleRef.current.dismiss();
    publishedBubbleRef.current = null;
    publishEventBubble(null);
    setCard(null);
    cardSinceRef.current = 0;
  }, []);

  return {
    active,
    tMs,
    live,
    card,
    progress: active ? progress || clockProgress : 0,
    voice,
    setVoice,
    start,
    stop,
    dismissCard,
    timeline,
    targetSeconds,
    setTargetSeconds,
    chapterIdx,
    chapterText,
    subtitle,
    subtitlePlace,
    filmLeg,
    voiceRate,
    onVoiceBoundary,
    onVoiceEnd,
    onVoiceLeadFailed,
    onSentenceStart,
    onSentenceEnd,
    isVoiceHeld,
    filmSource,
    filmStyle,
    setFilmStyle,
    hasWritten,
    canStart,
    seekChapter,
    remoteStatus,
    estimatedSeconds,
    variantEstimates,
  };
}
