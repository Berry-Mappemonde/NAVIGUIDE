import { useEffect, useRef } from "react";
import { canLeadWithVoice, speak, stopSpeaking } from "../utils/speak.js";

/**
 * Replay voice (lot F1) : un chapitre à la fois. `onboundary` pousse
 * l'index de caractère (le bateau suit) ; `onend` passe au chapitre
 * suivant. Même voix navigateur que « Écouter », pas de LLM.
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
} = {}) {
  const spokenRef = useRef({ idx: -1, text: "" });
  const onBoundaryRef = useRef(onBoundary);
  const onEndRef = useRef(onEnd);
  onBoundaryRef.current = onBoundary;
  onEndRef.current = onEnd;

  useEffect(() => {
    if (!active) {
      if (spokenRef.current.text) stopSpeaking();
      spokenRef.current = { idx: -1, text: "" };
      return;
    }
    if (!voice || !chapterText || !canLeadWithVoice()) return;
    if (spokenRef.current.idx === chapterIdx && spokenRef.current.text === chapterText) return;
    spokenRef.current = { idx: chapterIdx, text: chapterText };
    stopSpeaking();
    speak(chapterText, lang, {
      rate,
      onBoundary: (charIdx) => onBoundaryRef.current?.(charIdx),
      onEnd: () => onEndRef.current?.(),
    });
  }, [active, voice, chapterText, chapterIdx, rate, lang]);
}
