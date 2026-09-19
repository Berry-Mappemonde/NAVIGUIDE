import { useEffect, useRef } from "react";
import { speak, stopSpeaking } from "../utils/speak.js";

/**
 * Replay voice (lot E, moved out of App.jsx in lot J): each time the story
 * gains a paragraph — a leg closed, the next one begun — the newly current
 * paragraph is read aloud. Same browser voice as « Écouter », no LLM.
 * Stopped with the replay or when the voice switch is off.
 */
export function useReplayVoice({ active, voice, paragraphs, lang = "fr" }) {
  const spokenRef = useRef({ count: 0, text: "" });
  useEffect(() => {
    if (!active) {
      if (spokenRef.current.text) stopSpeaking();
      spokenRef.current = { count: 0, text: "" };
      return;
    }
    const last = paragraphs[paragraphs.length - 1] || "";
    if (!voice || !last || last === spokenRef.current.text) return;
    if (paragraphs.length !== spokenRef.current.count || !spokenRef.current.text) {
      spokenRef.current = { count: paragraphs.length, text: last };
      stopSpeaking();
      speak(last, lang);
    }
  }, [active, voice, paragraphs, lang]);
}
