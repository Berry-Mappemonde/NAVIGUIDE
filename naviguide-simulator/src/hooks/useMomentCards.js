import { useCallback, useEffect, useRef, useState } from "react";
import { advanceMoments, dismissNow, emptyMoments, nextFree } from "../engine/momentCard.js";

const TICK_MS = 1000;

/**
 * La carte du moment : une carte NOW (sécurité / décision) et un bloc FREE
 * (information) nourris par le registre d’événements jugés et le sac
 * `ici()`. Un tick par seconde fait vivre les expirations ; tout le reste
 * est pur (`engine/momentCard.js`). Ne bloque jamais la lecture.
 */
export function useMomentCards({
  enabled = true,
  events,
  bag,
  filmCum,
  playing = false,
  mode = "simulation",
  lang = "fr",
  legId = null,
  leg = null,
}) {
  const [state, setState] = useState(() => emptyMoments());
  const inputRef = useRef({ events, bag, filmCum, playing, mode, lang, legId, leg });
  inputRef.current = { events, bag, filmCum, playing, mode, lang, legId, leg };

  const step = useCallback((nowMs = Date.now()) => {
    setState((prev) => advanceMoments(prev, { ...inputRef.current, nowMs }));
  }, []);

  // New inputs → one step right away (a fresh event shows without waiting the tick).
  useEffect(() => {
    if (!enabled) return;
    step();
  }, [enabled, events, bag, filmCum, playing, mode, lang, legId, leg, step]);

  useEffect(() => {
    if (!enabled) return undefined;
    const id = setInterval(() => step(), TICK_MS);
    return () => clearInterval(id);
  }, [enabled, step]);

  useEffect(() => {
    if (!enabled) setState(emptyMoments());
  }, [enabled]);

  const dismiss = useCallback(() => setState((prev) => dismissNow(prev, Date.now())), []);
  const next = useCallback(() => setState((prev) => nextFree(prev, Date.now())), []);

  // Recette (dev only): `window.__naviguideMoments` shows queues and inputs.
  if (import.meta.env?.DEV && typeof window !== "undefined") {
    window.__naviguideMoments = { state, enabled, inputs: inputRef.current };
  }

  return {
    now: enabled ? state.now : null,
    free: enabled && !state.now ? state.free : null,
    freeLeft: state.freeQueue.length,
    nowLeft: state.nowQueue.length,
    dismiss,
    next,
  };
}
