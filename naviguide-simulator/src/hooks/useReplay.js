import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DEFAULT_SECONDS_PER_DAY, MIN_CARD_MS, advance, cardDwellMs, cardsBetween, journalTimeline, replayProgress, replaySample, replayWindow, trimQueue,
} from "../engine/replay.js";

/**
 * « Revoir l'expédition » (lot E) : rejoue la route de Saint-Maur à la
 * position d'aujourd'hui sur l'horloge officielle. Un jour d'expédition par
 * seconde ; la position vient de l'horloge, le vent des GRIB journalisés, les
 * cartes des lignes du journal. `live` remplace le bateau officiel pendant le
 * replay ; à la fin (ou sur Stop), retour au live. Never a fetch, never a chat.
 */
export function useReplay({ clock, journal, enabled = false, lang = "fr", secondsPerDay = DEFAULT_SECONDS_PER_DAY } = {}) {
  const [active, setActive] = useState(false);
  const [tMs, setTMs] = useState(null);
  const [card, setCard] = useState(null);
  const [voice, setVoice] = useState(true);
  const queueRef = useRef([]);
  const cardSinceRef = useRef(0);
  const lastTRef = useRef(null);
  const rafRef = useRef(null);
  const timeline = useMemo(() => journalTimeline(journal), [journal]);
  const timelineRef = useRef(timeline);
  timelineRef.current = timeline;
  const windowRef = useRef(null);

  const stop = useCallback(() => {
    setActive(false);
    setTMs(null);
    setCard(null);
    queueRef.current = [];
    lastTRef.current = null;
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
  }, []);

  const start = useCallback(() => {
    const w = replayWindow(clock, Date.now());
    if (!w) return false;
    windowRef.current = w;
    queueRef.current = [];
    cardSinceRef.current = 0;
    lastTRef.current = w.startMs;
    setCard(null);
    setTMs(w.startMs);
    setActive(true);
    return true;
  }, [clock]);

  useEffect(() => {
    if (!enabled && active) stop();
  }, [enabled, active, stop]);

  // The loop: wall clock → expedition time; journal lines passed → cards, one at a time.
  useEffect(() => {
    if (!active) return undefined;
    let prev = performance.now();
    const tick = (now) => {
      const dt = Math.min(200, now - prev);
      prev = now;
      setTMs((cur) => {
        if (cur == null) return cur;
        const { tMs: next, done } = advance(cur, dt, windowRef.current, secondsPerDay);
        const from = lastTRef.current ?? cur;
        const fresh = cardsBetween(timelineRef.current, from, next, lang);
        if (fresh.length) queueRef.current = trimQueue([...queueRef.current, ...fresh]);
        lastTRef.current = next;
        if (done) {
          // Let the last card breathe, then hand back to the live boat.
          setTimeout(() => stop(), queueRef.current.length ? MIN_CARD_MS : 800);
          return next;
        }
        return next;
      });
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
  }, [active, secondsPerDay, lang, stop]);

  const live = useMemo(() => (active && tMs != null ? replaySample(clock, tMs, timeline) : null), [active, tMs, clock, timeline]);
  const progress = active && tMs != null ? replayProgress(tMs, windowRef.current) : 0;

  const dismissCard = useCallback(() => {
    setCard(null);
    cardSinceRef.current = 0;
  }, []);

  return { active, tMs, live, card, progress, voice, setVoice, start, stop, dismissCard, timeline };
}
