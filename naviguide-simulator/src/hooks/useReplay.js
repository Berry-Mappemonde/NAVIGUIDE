import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DEFAULT_SECONDS_PER_DAY, MIN_CARD_MS, FILM_TARGET_SECONDS, calibrateRate, cardDwellMs, cardsBetween, chapterAtElapsed, filmChaptersFromStory, filmPlan, journalTimeline, publishFilmEnd, publishFilmStart, replayProgress, replaySample, replayWindow, trimQueue,
} from "../engine/replay.js";
import { buildFilmScript } from "../engine/expeditionStory.js";
import { canLeadWithVoice, waitForVoices, voiceEndKind } from "../utils/speak.js";
import { EventBubbleGate, pickFilmEvent, publishEventBubble } from "../components/eventBubble.js";

const API = import.meta.env?.VITE_API_URL ?? "";

export function chapterHasLeg(ch) {
  return [ch?.fromLat, ch?.fromLon, ch?.toLat, ch?.toLon].every((n) => (
    n != null && n !== "" && Number.isFinite(Number(n))
  ));
}

/** Script API sans emprise (marks horloge sans lat/lon) : on prend le brut local. */
export function pickFilmChapters(remote, local, fallback = []) {
  const r = remote?.chapters || [];
  const l = local?.chapters || [];
  if (r.length && r.some(chapterHasLeg)) {
    return {
      chapters: r.map((ch) => {
        if (chapterHasLeg(ch)) return ch;
        const src = l.find((c) => c.id === ch.id)
          || l.find((c) => c.fromName === ch.fromName && c.toName === ch.toName);
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
} = {}) {
  const kind = voiceEndKind({ hadBoundary, elapsedMs, alreadyRetried });
  if (kind === "retry") return { mode: "retry", finish: false, chapterIdx };
  if (kind === "linear") return { mode: "linear", finish: false, chapterIdx };
  const last = chapterIdx + 1 >= chapterCount;
  return { mode: "advance", finish: last, chapterIdx: last ? chapterIdx : chapterIdx + 1 };
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

/**
 * « Revoir l'expédition » (lot E, cinématique lot F1) : rejoue la route de
 * Saint-Maur à aujourd'hui. La voix mène (onboundary / onend) ; sans voix,
 * avance linéaire sur 150 s (ou 180 s). `live` remplace le bateau officiel
 * pendant le film ; à la fin (ou sur Stop), retour au live.
 */
export function useReplay({
  clock,
  journal,
  enabled = false,
  lang = "fr",
  secondsPerDay = DEFAULT_SECONDS_PER_DAY,
  marks = [],
  destination = null,
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
  const voiceCharRef = useRef(0);
  const voiceFailedRef = useRef(false);
  const voiceRef = useRef(voice);
  voiceRef.current = voice;
  const filmBubbleRef = useRef(new EventBubbleGate());
  const publishedBubbleRef = useRef(null);

  const stop = useCallback(() => {
    filmBubbleRef.current.reset();
    publishedBubbleRef.current = null;
    publishEventBubble(null);
    setActive(false);
    setTMs(null);
    setCard(null);
    setChapterIdx(0);
    setChapterText("");
    setFilmLeg(null);
    setVoiceRate(1);
    setProgress(0);
    queueRef.current = [];
    lastTRef.current = null;
    planRef.current = null;
    finishedRef.current = false;
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
  }, []);

  const applyChapter = useCallback((ch) => {
    if (!ch) return;
    chapterIdxRef.current = ch.idx;
    voiceCharRef.current = 0;
    setChapterIdx(ch.idx);
    setChapterText(ch.text || "");
    setFilmLeg({
      fromLat: ch.fromLat, fromLon: ch.fromLon, toLat: ch.toLat, toLon: ch.toLon,
    });
  }, []);

  const finish = useCallback(() => {
    if (finishedRef.current) return;
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
    if (!enabled || !clock) return undefined;
    const ac = new AbortController();
    const style = filmStyle === "written" ? "written" : "raw";
    const q = `lang=${encodeURIComponent(lang)}&seconds=${encodeURIComponent(targetSeconds)}&style=${style}`;
    fetch(`${API}/voyage/official/film?${q}`, { signal: ac.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data?.chapters?.length) {
          remotePlanRef.current = null;
          setHasWritten(false);
          if (filmStyle !== "written") setFilmSource("rules");
          return;
        }
        remotePlanRef.current = data;
        setHasWritten(Boolean(data.hasWritten));
        setFilmSource(data.source || "rules");
      })
      .catch(() => {
        remotePlanRef.current = null;
        setHasWritten(false);
        setFilmSource("rules");
      });
    return () => ac.abort();
  }, [enabled, clock, journal, lang, targetSeconds, filmStyle]);

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
    });
    const fallback = filmChaptersFromStory({
      clock,
      marks,
      live: destination,
      journal,
      lang,
      nowMs: Date.now(),
    });
    const picked = pickFilmChapters(remote, local, fallback);
    const chapters = picked.chapters;
    setFilmSource(picked.source || local.source || "rules");
    const plan = filmPlan({ chapters, targetSeconds });
    if (!plan.chapters.length) return false;
    windowRef.current = w;
    planRef.current = plan;
    queueRef.current = [];
    cardSinceRef.current = 0;
    lastTRef.current = plan.timeAt(0, 0);
    finishedRef.current = false;
    startWallRef.current = 0;
    chapterStartedAtRef.current = 0;
    voiceCharRef.current = 0;
    voiceFailedRef.current = false;
    setVoiceRate(1);
    filmBubbleRef.current.reset();
    publishedBubbleRef.current = null;
    setCard(null);
    applyChapter(plan.chapters[0]);
    setTMs(plan.timeAt(0, 0));
    setProgress(0);
    setActive(true);
    publishFilmStart(plan.targetSeconds);
    return true;
  }, [clock, marks, destination, journal, lang, targetSeconds, applyChapter]);

  useEffect(() => {
    if (!enabled && active) stop();
  }, [enabled, active, stop]);

  const onVoiceBoundary = useCallback((charIdx) => {
    const plan = planRef.current;
    if (!plan || finishedRef.current) return;
    voiceCharRef.current = charIdx;
    const next = plan.timeAt(chapterIdxRef.current, charIdx);
    if (next != null) setTMs(next);
  }, []);

  const onVoiceLeadFailed = useCallback(() => {
    voiceFailedRef.current = true;
  }, []);

  const onVoiceEnd = useCallback(() => {
    const plan = planRef.current;
    if (!plan || finishedRef.current) return;
    if (!voiceRef.current || voiceFailedRef.current || !canLeadWithVoice()) return;
    const idx = chapterIdxRef.current;
    const ch = plan.chapters[idx];
    if (ch) setTMs(ch.tB);
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
      const voiceLed = Boolean(
        voiceRef.current
        && !voiceFailedRef.current
        && canLeadWithVoice()
        && voiceCharRef.current > 0,
      );

      const ingest = (next) => {
        if (next == null) return;
        const from = lastTRef.current ?? next;
        const fresh = cardsBetween(timelineRef.current, from, next, lang);
        if (fresh.length) queueRef.current = trimQueue([...queueRef.current, ...fresh]);
        lastTRef.current = next;
        setTMs(next);
      };

      let charIdx = voiceCharRef.current;
      const linear = linearFilmAt(elapsed, plan);
      const done = !voiceLed && linear.finish;
      if (done) {
        ingest(w.endMs);
        finish();
      } else if (!voiceLed) {
        const ch = chapterAtElapsed(plan, elapsed);
        if (ch && ch.idx !== chapterIdxRef.current) applyChapter(ch);
        const frac = ch && ch.seconds > 0 ? (elapsed - ch.startWall) / ch.seconds : 1;
        charIdx = Math.floor(Math.max(0, Math.min(1, frac)) * (ch?.chars || 1));
        ingest(plan.timeAt(ch?.idx ?? 0, charIdx));
      } else {
        setTMs((cur) => {
          if (cur == null) return cur;
          const from = lastTRef.current ?? cur;
          const fresh = cardsBetween(timelineRef.current, from, cur, lang);
          if (fresh.length) queueRef.current = trimQueue([...queueRef.current, ...fresh]);
          lastTRef.current = cur;
          return cur;
        });
      }

      const chapter = plan.chapters[chapterIdxRef.current];
      const filmEv = pickFilmEvent({
        chapter,
        charIdx,
        tMs: lastTRef.current,
        voiceLed,
        plan,
      });
      const shown = filmBubbleRef.current.propose(filmEv?.card || null);
      if (shown !== publishedBubbleRef.current) {
        publishedBubbleRef.current = shown;
        if (shown) {
          cardSinceRef.current = now;
          setCard(shown);
        }
        publishEventBubble(shown);
      }
      if (typeof window !== "undefined") {
        const prevFilm = window.__naviguideFilm || {};
        window.__naviguideFilm = {
          ...prevFilm,
          chapterIdx: chapterIdxRef.current,
          elapsed,
          charIdx,
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
