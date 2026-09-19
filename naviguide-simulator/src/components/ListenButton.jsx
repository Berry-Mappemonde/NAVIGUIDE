import { useEffect, useState } from "react";
import { Square, Volume2 } from "lucide-react";
import { canSpeak, speak, stopSpeaking } from "../utils/speak.js";

/**
 * « Écouter » — le récit lu à voix haute par le navigateur (zéro LLM).
 * Lives in the film bar (playback controls) since 19 Sept. 2026; the same
 * button also reads a moment card. `text` may be a string or a list of
 * paragraphs (read in order, empty ones skipped).
 */
export function ListenButton({ text, t, lang, compact = false, testId = "briefing-listen", className = "" }) {
  const [speaking, setSpeaking] = useState(false);
  const body = Array.isArray(text) ? text.filter(Boolean).join("\n\n") : (text || "");
  useEffect(() => () => stopSpeaking(), []);
  // A new text while speaking: stop, the button goes back to « Écouter ».
  useEffect(() => {
    if (speaking) {
      stopSpeaking();
      setSpeaking(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [body]);
  if (!canSpeak() || !body) return null;
  const toggle = () => {
    if (speaking) {
      stopSpeaking();
      setSpeaking(false);
      return;
    }
    const ok = speak(body, lang, { onEnd: () => setSpeaking(false) });
    setSpeaking(ok);
  };
  const label = speaking ? t("briefingListenStop") : t("briefingListen");
  return (
    <button
      type="button"
      onClick={toggle}
      data-testid={testId}
      aria-pressed={speaking}
      title={label}
      className={`flex items-center gap-1 rounded-md text-[10px] font-semibold border transition-colors
        ${compact ? "h-7 px-2" : "px-1.5 py-0.5 rounded-full"}
        ${speaking ? "bg-sky-600/40 text-sky-100 border-sky-400/40" : "bg-white/5 text-white/80 border-white/10 hover:bg-white/10 hover:text-white"}
        ${className}`}
    >
      {speaking ? <Square size={11} /> : <Volume2 size={11} />}
      {label}
    </button>
  );
}
