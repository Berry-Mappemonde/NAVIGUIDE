import { useEffect, useRef } from "react";
import { sentenceStartsFromText } from "../engine/replay.js";
import { canLeadWithVoice, canSpeak, speak, stopSpeaking, waitForVoices } from "../utils/speak.js";

function sentencesOf(text) {
  const raw = String(text || "");
  if (!raw) return [];
  const starts = sentenceStartsFromText(raw);
  return starts.map((start, i) => ({
    start,
    text: raw.slice(start, i + 1 < starts.length ? starts[i + 1] : raw.length),
  })).filter((s) => s.text.trim());
}

function waitWhile(held, cancelled, intervalMs = 40) {
  return new Promise((resolve) => {
    const tick = () => {
      if (cancelled()) return resolve(false);
      if (!held()) return resolve(true);
      const start = typeof setTimeout === "function" ? setTimeout : null;
      if (!start) return resolve(true);
      const id = start(tick, intervalMs);
      if (id && typeof id.unref === "function") id.unref();
    };
    tick();
  });
}

function speakSentence(text, lang, { rate, win, onBoundary, onLeadFailed }) {
  return new Promise((resolve) => {
    let settled = false;
    const done = () => {
      if (settled) return;
      settled = true;
      resolve();
    };
    const ok = speak(text, lang, {
      rate,
      win,
      onBoundary,
      onEnd: done,
      onLeadFailed: () => {
        onLeadFailed?.();
        done();
      },
    });
    if (!ok) done();
  });
}

/**
 * Replay voice (lot F1 / R3 / RG12) : une phrase à la fois, après voiceschanged.
 * `onboundary` pousse l'index de caractère ; en fin de phrase la voix attend
 * que le bateau ait rejoint l'ancre (silence, jamais coupée au milieu).
 * `onend` du chapitre seulement après la dernière phrase et l'attente.
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
  onSentenceStart,
  onSentenceEnd,
  isVoiceHeld,
} = {}) {
  const spokenRef = useRef({ idx: -1, text: "" });
  const onBoundaryRef = useRef(onBoundary);
  const onEndRef = useRef(onEnd);
  const onLeadFailedRef = useRef(onLeadFailed);
  const onSentenceStartRef = useRef(onSentenceStart);
  const onSentenceEndRef = useRef(onSentenceEnd);
  const isVoiceHeldRef = useRef(isVoiceHeld);
  onBoundaryRef.current = onBoundary;
  onEndRef.current = onEnd;
  onLeadFailedRef.current = onLeadFailed;
  onSentenceStartRef.current = onSentenceStart;
  onSentenceEndRef.current = onSentenceEnd;
  isVoiceHeldRef.current = isVoiceHeld;

  useEffect(() => {
    if (!active) {
      if (spokenRef.current.text) stopSpeaking();
      spokenRef.current = { idx: -1, text: "" };
      return undefined;
    }
    if (!voice || !chapterText) return undefined;
    const win = typeof window !== "undefined" ? window : null;
    if (!canSpeak(win) || !canLeadWithVoice(win)) {
      onLeadFailedRef.current?.();
      return undefined;
    }
    if (spokenRef.current.idx === chapterIdx && spokenRef.current.text === chapterText) return undefined;
    spokenRef.current = { idx: chapterIdx, text: chapterText };
    stopSpeaking();
    let cancelled = false;
    const sentences = sentencesOf(chapterText);
    waitForVoices(win, 1000).then(async (voices) => {
      if (cancelled) return;
      if (!voices.length) {
        onLeadFailedRef.current?.();
        return;
      }
      const list = sentences.length ? sentences : [{ start: 0, text: chapterText }];
      for (let i = 0; i < list.length; i += 1) {
        if (cancelled) return;
        const s = list[i];
        onSentenceStartRef.current?.(s.start);
        await speakSentence(s.text, lang, {
          rate,
          win,
          onBoundary: (charIdx) => onBoundaryRef.current?.(s.start + (Number(charIdx) || 0)),
          onLeadFailed: () => onLeadFailedRef.current?.(),
        });
        if (cancelled) return;
        onSentenceEndRef.current?.(s.start + s.text.length);
        const ok = await waitWhile(
          () => Boolean(isVoiceHeldRef.current?.()),
          () => cancelled,
        );
        if (!ok) return;
      }
      if (!cancelled) onEndRef.current?.();
    });
    return () => {
      cancelled = true;
      stopSpeaking();
    };
  }, [active, voice, chapterText, chapterIdx, rate, lang]);
}
