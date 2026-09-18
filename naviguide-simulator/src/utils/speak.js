/**
 * Lecture à voix haute — `speechSynthesis` du navigateur : gratuit, local,
 * zéro LLM (décision du 18 sept. 2026 : l'histoire est *lue*, pas dictée).
 */

/** Briefing text as spoken: no URLs, no arrows/glyphs, tidy spaces. */
export function spokenText(text) {
  return String(text || "")
    .replace(/https?:\/\/\S+/g, "")
    .replace(/[↗◎•·|]/g, " ")
    .replace(/\s*\n+\s*/g, ". ")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+([,.;:!?])/g, "$1")
    .replace(/\.\s*\./g, ".")
    .trim();
}

export function canSpeak(win = typeof window !== "undefined" ? window : null) {
  return Boolean(win?.speechSynthesis && typeof win.SpeechSynthesisUtterance === "function");
}

export function isSpeaking(win = typeof window !== "undefined" ? window : null) {
  return Boolean(win?.speechSynthesis?.speaking);
}

export function stopSpeaking(win = typeof window !== "undefined" ? window : null) {
  try {
    win?.speechSynthesis?.cancel();
  } catch {
    /* no synthesis available */
  }
}

/**
 * Reads `text` aloud in `lang` ("fr" | "en"). Returns false when the browser
 * cannot speak. `onEnd` fires when the reading finishes or is cancelled.
 */
export function speak(text, lang = "fr", { onEnd, win = typeof window !== "undefined" ? window : null } = {}) {
  if (!canSpeak(win)) return false;
  const body = spokenText(text);
  if (!body) return false;
  stopSpeaking(win);
  const utter = new win.SpeechSynthesisUtterance(body);
  utter.lang = lang === "en" ? "en-GB" : "fr-FR";
  utter.rate = 1.0;
  const voices = (() => {
    try { return win.speechSynthesis.getVoices() || []; } catch { return []; }
  })();
  const match = voices.find((v) => String(v.lang || "").toLowerCase().startsWith(utter.lang.slice(0, 2).toLowerCase()));
  if (match) utter.voice = match;
  if (onEnd) {
    utter.onend = () => onEnd();
    utter.onerror = () => onEnd();
  }
  win.speechSynthesis.speak(utter);
  return true;
}
