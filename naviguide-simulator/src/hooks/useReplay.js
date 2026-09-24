import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DEFAULT_SECONDS_PER_DAY, MIN_CARD_MS, FILM_TARGET_SECONDS, FILM_RECALE_MS, advanceReplayTime, calibrateRate, cardDwellMs, cardsBetween, chapterAtElapsed, filmChaptersFromStory, filmPlan, journalTimeline, positionAt, publishFilmEnd, publishFilmStart, replayProgress, replaySample, replayWindow, trimQueue,
} from "../engine/replay.js";
import { buildFilmScript } from "../engine/expeditionStory.js";
import { DEFAULT_T0_ISO } from "../engine/voyageClock.js";
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
export function filmTextHasT0Year(chapters, t0) {
  const year = new Date(t0 || "").getUTCFullYear();
  if (!Number.isFinite(year)) return true;
  const text = String(chapters?.[0]?.text || "");
  if (!text) return false;
  return text.includes(String(year));
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

/** Avance linéaire : le dernier chapitre est atteint à la durée cible, pas avant. */
export function linearFilmAt(elapsed, plan) {
  const seconds = Number(plan?.targetSeconds) || 0;
  const ch = chapterAtElapsed(plan, elapsed);
  const lastIdx = Math.max(0, (plan?.chapters?.length || 1) - 1);
  return {
    chapterIdx: ch?.idx ?? 0,
    finish: elapsed >= seconds,
    lastReached: (ch?.idx ?? 0) >= lastIdx,
  };
}

export const APPROACH_FRAC = 0.8;

/**
 * Stop du film (lot RA5) : coupe la voix, libère la caméra (fin de
 * `filmActive` + `publishFilmEnd`), annule la boucle. L'appelant remet
 * `active=false` — MapSceneController quitte alors le suivi film.
 */
export function applyReplayStop({
  cancelRaf,
  stopVoice,
  releaseCamera,
} = {}) {
  (stopVoice || stopSpeaking)();
  (releaseCamera || publishFilmEnd)();
  cancelRaf?.();
  return {
    active: false,
    tMs: null,
    card: null,
    progress: 0,
    chapterIdx: 0,
    chapterText: "",
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
  const [targetSeconds, setTargetSeconds] = useState(FILM_TARGET_SECONDS);
  const [chapterIdx, setChapterIdx] = useState(0);
  const [chapterText, setChapterText] = useState("");
  const [filmLeg, setFilmLeg] = useState(null);
  const [voiceRate, setVoiceRate] = useState(1);
  const [progress, setProgress] = useState(0);
  const [filmSource, setFilmSource] = useState("rules");
  const [filmStyle, setFilmStyle] = useState("raw");
  const [hasWritten, setHasWritten] = useState(false);
  const remotePlanRef = useRef(null);
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
  const voiceCharRef = useRef(0);
  const voiceFailedRef = useRef(false);
  const tMsRef = useRef(null);
  const voiceTargetRef = useRef(null);
  const recaleRemainRef = useRef(0);
  const voiceRef = useRef(voice);
  voiceRef.current = voice;
  const filmBubbleRef = useRef(new EventBubbleGate());
  const filmScoreRef = useRef(new FilmEventScoreGate());
  const publishedBubbleRef = useRef(null);
  const clockRef = useRef(clock);
  clockRef.current = clock;

  const stop = useCallback(() => {
    stoppingRef.current = true;
    finishedRef.current = true;
    filmBubbleRef.current.reset();
    filmScoreRef.current.reset();
    publishedBubbleRef.current = null;
    publishEventBubble(null);
    const cleared = applyReplayStop({
      cancelRaf: () => {
        if (rafRef.current) cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      },
    });
    setActive(cleared.active);
    setTMs(cleared.tMs);
    setCard(cleared.card);
    setChapterIdx(cleared.chapterIdx);
    setChapterText(cleared.chapterText);
    setFilmLeg(cleared.filmLeg);
    setVoiceRate(1);
    setProgress(cleared.progress);
    queueRef.current = [];
    lastTRef.current = null;
    tMsRef.current = null;
    voiceTargetRef.current = null;
    recaleRemainRef.current = 0;
    planRef.current = null;
  }, []);

  const applyChapter = useCallback((ch) => {
    if (!ch) return;
    chapterIdxRef.current = ch.idx;
    voiceCharRef.current = 0;
    voiceTargetRef.current = Number.isFinite(ch.tA) ? ch.tA : null;
    recaleRemainRef.current = 0;
    if (Number.isFinite(ch.tA)) tMsRef.current = ch.tA;
    setChapterIdx(ch.idx);
    setChapterText(ch.text || "");
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
    setTimeout(() => stop(), 400);
  }, [stop]);

  useEffect(() => {
    if (!enabled) return undefined;
    waitForVoices(typeof window !== "undefined" ? window : null, 1000);
    return undefined;
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return undefined;
    const ac = new AbortController();
    const style = filmStyle === "written" ? "written" : "raw";
    const q = `lang=${encodeURIComponent(lang)}&seconds=${encodeURIComponent(targetSeconds)}&style=${style}&t0=${encodeURIComponent(t0)}`;
    remotePlanRef.current = null;
    fetch(`${API}/voyage/official/film?${q}`, { signal: ac.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.chapters?.length) {
          remotePlanRef.current = data;
          if (ac.signal.aborted) return;
          setHasWritten(Boolean(data.hasWritten));
          setFilmSource(data.source || "rules");
          return;
        }
        if (ac.signal.aborted || remotePlanRef.current) return;
        setHasWritten(false);
        if (filmStyle !== "written") setFilmSource("rules");
      })
      .catch((err) => {
        if (err?.name === "AbortError" || ac.signal.aborted || remotePlanRef.current) return;
        setHasWritten(false);
        setFilmSource("rules");
      });
    return () => ac.abort();
  }, [enabled, lang, targetSeconds, filmStyle, t0]);

  const start = useCallback(() => {
    const w = replayWindow(clock, Date.now());
    if (!w) return false;
    const remote = remotePlanRef.current;
    const local = buildFilmScript({
      clock,
      marks,
      live: destination,
      journal,
      lang,
      now: Date.now(),
      seconds: targetSeconds,
      t0,
    });
    const fallback = filmChaptersFromStory({
      clock,
      marks,
      live: destination,
      journal,
      lang,
      nowMs: Date.now(),
      t0,
    });
    const remoteOk = remote && filmTextHasT0Year(remote.chapters, t0);
    const picked = pickFilmChapters(remoteOk ? remote : null, local, fallback);
    const chapters = picked.chapters;
    setFilmSource(picked.source || local.source || "rules");
    const plan = filmPlan({ chapters, targetSeconds });
    if (!plan.chapters.length) return false;
    windowRef.current = w;
    planRef.current = plan;
    queueRef.current = [];
    cardSinceRef.current = 0;
    lastTRef.current = plan.timeAt(0, 0);
    tMsRef.current = lastTRef.current;
    voiceTargetRef.current = lastTRef.current;
    recaleRemainRef.current = 0;
    finishedRef.current = false;
    stoppingRef.current = false;
    startWallRef.current = 0;
    chapterStartedAtRef.current = 0;
    voiceCharRef.current = 0;
    voiceFailedRef.current = false;
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
    return true;
  }, [clock, marks, destination, journal, lang, targetSeconds, applyChapter, t0]);

  useEffect(() => {
    if (!enabled && active) stop();
  }, [enabled, active, stop]);

  const onVoiceBoundary = useCallback((charIdx) => {
    const plan = planRef.current;
    if (!plan || finishedRef.current) return;
    voiceCharRef.current = charIdx;
    const next = plan.timeAt(chapterIdxRef.current, charIdx);
    if (next == null) return;
    voiceTargetRef.current = next;
    recaleRemainRef.current = FILM_RECALE_MS;
  }, []);

  const onVoiceLeadFailed = useCallback(() => {
    if (stoppingRef.current || finishedRef.current) return;
    voiceFailedRef.current = true;
  }, []);

  const onVoiceEnd = useCallback(() => {
    const plan = planRef.current;
    if (!plan || finishedRef.current || stoppingRef.current) return;
    if (!voiceRef.current || voiceFailedRef.current || !canLeadWithVoice()) return;
    const idx = chapterIdxRef.current;
    const ch = plan.chapters[idx];
    if (ch) {
      tMsRef.current = ch.tB;
      lastTRef.current = ch.tB;
      setTMs(ch.tB);
    }
    const chapterElapsed = chapterStartedAtRef.current
      ? (performance.now() - chapterStartedAtRef.current) / 1000
      : 0;
    const wallElapsed = startWallRef.current
      ? (performance.now() - startWallRef.current) / 1000
      : chapterElapsed;
    if (idx === 0 && plan.chapters.length > 1) {
      const remainingChars = plan.chapters.slice(1).reduce((s, c) => s + c.chars, 0);
      setVoiceRate(calibrateRate({
        chapterChars: ch?.chars,
        elapsedSeconds: chapterElapsed,
        remainingChars,
        remainingBudgetSeconds: plan.targetSeconds - wallElapsed,
      }));
    }
    if (idx + 1 >= plan.chapters.length) {
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
      const elapsed = (now - startWallRef.current) / 1000;
      setProgress(Math.max(0, Math.min(1, elapsed / plan.targetSeconds)));
      const voiceClock = Boolean(
        voiceRef.current
        && !voiceFailedRef.current
        && canLeadWithVoice(),
      );
      const voiceLed = Boolean(voiceClock && voiceCharRef.current > 0);

      const ingest = (next) => {
        if (next == null) return;
        const from = lastTRef.current ?? next;
        const fresh = cardsBetween(timelineRef.current, from, next, lang);
        if (fresh.length) queueRef.current = trimQueue([...queueRef.current, ...fresh]);
        lastTRef.current = next;
        tMsRef.current = next;
        setTMs(next);
      };

      let charIdx = voiceCharRef.current;
      const linear = linearFilmAt(elapsed, plan);
      const done = !voiceClock && linear.finish && linear.lastReached
        && !stoppingRef.current;
      if (done) {
        const last = plan.chapters[plan.chapters.length - 1];
        ingest(last?.tB ?? w.endMs);
        finish();
      } else if (!voiceClock) {
        const ch = chapterAtElapsed(plan, elapsed);
        if (ch && ch.idx !== chapterIdxRef.current) applyChapter(ch);
        const frac = ch && ch.seconds > 0 ? (elapsed - ch.startWall) / ch.seconds : 1;
        const f = Math.max(0, Math.min(1, frac));
        charIdx = f * (ch?.chars || 1);
        ingest(ch ? ch.tA + f * (ch.tB - ch.tA) : plan.timeAt(0, 0));
      } else {
        const ch = plan.chapters[chapterIdxRef.current];
        const cur = tMsRef.current ?? lastTRef.current ?? ch?.tA;
        const stepped = advanceReplayTime({
          t: cur,
          dt: dt / 1000,
          chapter: ch,
          targetT: voiceTargetRef.current,
          recaleRemainMs: recaleRemainRef.current,
        });
        recaleRemainRef.current = stepped.recaleRemainMs;
        ingest(stepped.t);
      }

      const chapter = plan.chapters[chapterIdxRef.current];
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
        const prevFilm = window.__naviguideFilm || {};
        window.__naviguideFilm = {
          ...prevFilm,
          chapterIdx: chapterIdxRef.current,
          elapsed,
          charIdx,
          tMs: lastTRef.current,
          lat: pos?.lat ?? null,
          lon: pos?.lon ?? null,
          filmNm: pos?.filmNm ?? null,
          bubbleId: shown ? (shown.key || shown.id || null) : null,
          bubbleKind: shown?.kind || null,
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
    filmLeg,
    voiceRate,
    onVoiceBoundary,
    onVoiceEnd,
    onVoiceLeadFailed,
    filmSource,
    filmStyle,
    setFilmStyle,
    hasWritten,
  };
}
