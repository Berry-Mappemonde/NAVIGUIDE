import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DEFAULT_SECONDS_PER_DAY, MIN_CARD_MS, FILM_TARGET_SECONDS, calibrateRate, cardDwellMs, cardsBetween, chapterAtElapsed, filmChaptersFromStory, filmPlan, journalTimeline, publishFilmEnd, publishFilmStart, replayProgress, replaySample, replayWindow, trimQueue,
} from "../engine/replay.js";
import { buildFilmScript } from "../engine/expeditionStory.js";
import { canLeadWithVoice } from "../utils/speak.js";

const API = import.meta.env?.VITE_API_URL ?? "";

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
  const voiceRef = useRef(voice);
  voiceRef.current = voice;

  const stop = useCallback(() => {
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
    const chapters = remote?.chapters?.length ? remote.chapters : (local.chapters?.length ? local.chapters : filmChaptersFromStory({
      clock,
      marks,
      live: destination,
      journal,
      lang,
      nowMs: Date.now(),
    }));
    if (!remote?.chapters?.length) setFilmSource(local.source || "rules");
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
    setVoiceRate(1);
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

  const onVoiceEnd = useCallback(() => {
    const plan = planRef.current;
    if (!plan || finishedRef.current) return;
    if (!voiceRef.current || !canLeadWithVoice()) return;
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
      if (typeof window !== "undefined") {
        const prev = window.__naviguideFilm || {};
        window.__naviguideFilm = {
          ...prev,
          chapterIdx: chapterIdxRef.current,
          elapsed,
        };
      }
      const voiceLed = Boolean(voiceRef.current && canLeadWithVoice());

      const ingest = (next) => {
        if (next == null) return;
        const from = lastTRef.current ?? next;
        const fresh = cardsBetween(timelineRef.current, from, next, lang);
        if (fresh.length) queueRef.current = trimQueue([...queueRef.current, ...fresh]);
        lastTRef.current = next;
        setTMs(next);
      };

      const done = !voiceLed && elapsed >= plan.targetSeconds;
      if (done) {
        ingest(w.endMs);
        finish();
      } else if (!voiceLed) {
        const ch = chapterAtElapsed(plan, elapsed);
        if (ch && ch.idx !== chapterIdxRef.current) applyChapter(ch);
        const frac = ch && ch.seconds > 0 ? (elapsed - ch.startWall) / ch.seconds : 1;
        const charIdx = Math.floor(Math.max(0, Math.min(1, frac)) * (ch?.chars || 1));
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
        if (elapsed > 1.5 && voiceCharRef.current === 0 && chapterIdxRef.current === 0) {
          voiceRef.current = false;
        }
        if (elapsed > plan.targetSeconds + 20) finish();
      }

      // Card rotation: the current one stays MIN_CARD_MS when the queue is
      // quiet, less when lines pile up — the cards never lag the boat.
      if (queueRef.current.length && now - cardSinceRef.current >= cardDwellMs(queueRef.current.length)) {
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
    filmSource,
    filmStyle,
    setFilmStyle,
    hasWritten,
  };
}
