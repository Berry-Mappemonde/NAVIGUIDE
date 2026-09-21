import { useEffect, useRef } from "react";
import { canSpeak, speak, stopSpeaking, waitForVoices } from "../utils/speak.js";

/**
 * Replay voice (lot F1 / R3) : un chapitre à la fois, après voiceschanged.
 * `onboundary` pousse l'index de caractère ; `onend` passe au chapitre
 * suivant. Échec voix → `onLeadFailed` (linéaire, film non terminé).
 */
export function useReplayVoice({
  active,
  voice,
  lang = "fr",
  chapterText = "",
  chapterIdx = 0,
  rate = 1,
  onBoundary,
  onEnd,
  onLeadFailed,
} = {}) {
  const spokenRef = useRef({ idx: -1, text: "" });
  const onBoundaryRef = useRef(onBoundary);
  const onEndRef = useRef(onEnd);
  const onLeadFailedRef = useRef(onLeadFailed);
  onBoundaryRef.current = onBoundary;
  onEndRef.current = onEnd;
  onLeadFailedRef.current = onLeadFailed;

  useEffect(() => {
    if (!active) {
      if (spokenRef.current.text) stopSpeaking();
      spokenRef.current = { idx: -1, text: "" };
      return undefined;
    }
    if (!voice || !chapterText || !canSpeak()) return undefined;
    const win = typeof window !== "undefined" ? window : null;
    if (win?.navigator?.webdriver) return undefined;
    if (spokenRef.current.idx === chapterIdx && spokenRef.current.text === chapterText) return undefined;
    spokenRef.current = { idx: chapterIdx, text: chapterText };
    stopSpeaking();
    let cancelled = false;
    waitForVoices(win, 1000).then((voices) => {
      if (cancelled) return;
      if (!voices.length) {
        onLeadFailedRef.current?.();
        return;
      }
      speak(chapterText, lang, {
        rate,
        win,
        onBoundary: (charIdx) => onBoundaryRef.current?.(charIdx),
        onEnd: () => onEndRef.current?.(),
        onLeadFailed: () => onLeadFailedRef.current?.(),
      });
    });
    return () => {
      cancelled = true;
      stopSpeaking();
    };
  }, [active, voice, chapterText, chapterIdx, rate, lang]);
}
