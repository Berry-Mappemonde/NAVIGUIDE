/**
 * Lecture à voix haute — `speechSynthesis` du navigateur : gratuit, local,
 * zéro LLM (décision du 18 sept. 2026 : l'histoire est *lue*, pas dictée).
 * Lot R3 : voix prêtes, phrases courtes, keep-alive Chrome, repli linéaire.
 */

export const VOICES_WAIT_MS = 1000;
export const VOICE_IMMEDIATE_END_MS = 500;
export const UTTERANCE_KEEPALIVE_MS = 10_000;
export const SENTENCE_MAX_CHARS = 200;

export const VOICE_PREFS = {
  en: [
    "Google UK English Female",
    "Google US English",
    "Samantha",
    "Daniel",
    "Karen",
    "Moira",
  ],
  fr: [
    "Google français",
    "Thomas",
    "Amélie",
    "Audrey",
  ],
};

let keepAliveTimer = null;
/** Incrémenté à chaque `stopSpeaking` : un `onend` de `cancel()` ne relance rien. */
let speakGeneration = 0;

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

/** Voix réellement disponible (Playwright / headless : on reste en mode linéaire). */
export function canLeadWithVoice(win = typeof window !== "undefined" ? window : null) {
  if (!canSpeak(win)) return false;
  if (win.navigator?.webdriver) return false;
  try {
    return (win.speechSynthesis.getVoices() || []).length > 0;
  } catch {
    return false;
  }
}

export function isSpeaking(win = typeof window !== "undefined" ? window : null) {
  return Boolean(win?.speechSynthesis?.speaking);
}

function clearKeepAlive() {
  if (keepAliveTimer == null) return;
  const clearFn = typeof clearInterval === "function" ? clearInterval : null;
  try { clearFn?.(keepAliveTimer); } catch { /* ignore */ }
  keepAliveTimer = null;
}

export function stopSpeaking(win = typeof window !== "undefined" ? window : null) {
  speakGeneration += 1;
  clearKeepAlive();
  try {
    win?.speechSynthesis?.cancel();
  } catch {
    /* no synthesis available */
  }
}

export function getVoices(win = typeof window !== "undefined" ? window : null) {
  try {
    return win?.speechSynthesis?.getVoices?.() || [];
  } catch {
    return [];
  }
}

/** Attend `voiceschanged` au plus `timeoutMs` (Chrome : liste vide au premier appel). */
export function waitForVoices(win = typeof window !== "undefined" ? window : null, timeoutMs = VOICES_WAIT_MS) {
  const existing = getVoices(win);
  if (existing.length) return Promise.resolve(existing);
  const synth = win?.speechSynthesis;
  if (!synth) return Promise.resolve([]);
  return new Promise((resolve) => {
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      try { synth.removeEventListener?.("voiceschanged", onChange); } catch { /* ignore */ }
      if (synth.onvoiceschanged === onChange) synth.onvoiceschanged = null;
      resolve(getVoices(win));
    };
    const onChange = () => finish();
    try { synth.addEventListener?.("voiceschanged", onChange); } catch { /* ignore */ }
    try { synth.onvoiceschanged = onChange; } catch { /* ignore */ }
    const wait = Number.isFinite(Number(timeoutMs)) ? Math.max(0, Number(timeoutMs)) : VOICES_WAIT_MS;
    const start = typeof setTimeout === "function" ? setTimeout : null;
    if (start) {
      const t = start(finish, wait);
      if (t && typeof t.unref === "function") t.unref();
    } else {
      finish();
    }
  });
}

export function pickVoice(voices, lang = "fr") {
  const list = Array.isArray(voices) ? voices : [];
  const key = lang === "en" ? "en" : "fr";
  const prefs = VOICE_PREFS[key];
  for (const name of prefs) {
    const hit = list.find((v) => String(v?.name || "") === name);
    if (hit) return hit;
  }
  const prefix = key;
  return list.find((v) => String(v?.lang || "").toLowerCase().startsWith(prefix)) || null;
}

export function utteranceRate(lang, rate) {
  const n = Number(rate);
  if (Number.isFinite(n) && n !== 1) {
    return Math.max(0.9, Math.min(1.25, n));
  }
  return lang === "en" ? 0.95 : 1;
}

/**
 * Découpe un chapitre en phrases ≤ `max` caractères, avec l'index de départ
 * dans le texte d'origine (charIdx global monotone).
 */
export function splitUtterances(text, max = SENTENCE_MAX_CHARS) {
  const src = String(text || "");
  if (!src) return [];
  const limit = Number.isFinite(Number(max)) && Number(max) > 0 ? Number(max) : SENTENCE_MAX_CHARS;
  const rawParts = src.match(/[^.!?…]+(?:[.!?…]+|$)/g) || [src];
  const pieces = [];
  for (const raw of rawParts) {
    const sentence = raw.replace(/^\s+/, "");
    if (!sentence) continue;
    if (sentence.length <= limit) {
      pieces.push(sentence);
      continue;
    }
    let buf = "";
    for (const word of sentence.split(/\s+/)) {
      if (!word) continue;
      const next = buf ? `${buf} ${word}` : word;
      if (next.length <= limit) {
        buf = next;
        continue;
      }
      if (buf) pieces.push(buf);
      if (word.length <= limit) {
        buf = word;
      } else {
        for (let i = 0; i < word.length; i += limit) {
          const slice = word.slice(i, i + limit);
          if (slice.length === limit) pieces.push(slice);
          else buf = slice;
        }
      }
    }
    if (buf) pieces.push(buf);
  }
  let from = 0;
  return pieces.map((piece) => {
    const start = src.indexOf(piece, from);
    const at = start < 0 ? from : start;
    from = at + piece.length;
    return { text: piece, start: at };
  });
}

/**
 * onend sans boundary en < 500 ms :
 * — des chunks restent → avancer (reprendre au suivant, jamais finir) ;
 * — dernier chunk → une relance, puis mode linéaire.
 */
export function voiceEndKind({
  hadBoundary,
  elapsedMs,
  alreadyRetried,
  hasMoreChunks = false,
} = {}) {
  const elapsed = Number(elapsedMs);
  if (!hadBoundary && Number.isFinite(elapsed) && elapsed < VOICE_IMMEDIATE_END_MS) {
    if (hasMoreChunks) return "advance";
    return alreadyRetried ? "linear" : "retry";
  }
  return "advance";
}

function nowMs(win) {
  const perf = win?.performance || (typeof performance !== "undefined" ? performance : null);
  if (perf && typeof perf.now === "function") return perf.now();
  return Date.now();
}

function armKeepAlive(win) {
  clearKeepAlive();
  const start = win?.setInterval?.bind(win) || (typeof setInterval === "function" ? setInterval : null);
  if (!start) return;
  keepAliveTimer = start(() => {
    try {
      const synth = win?.speechSynthesis;
      if (!synth?.speaking) return;
      // `pause()`+`resume()` coupe l'utterance (onend) : on ne fait que `resume()`.
      synth.resume();
    } catch { /* Chrome keep-alive */ }
  }, UTTERANCE_KEEPALIVE_MS);
  if (keepAliveTimer && typeof keepAliveTimer.unref === "function") keepAliveTimer.unref();
}

function beginUtterances(body, lang, opts, voices) {
  const win = opts.win;
  const generation = speakGeneration;
  const stillThisSpeak = () => generation === speakGeneration;
  const chunks = splitUtterances(body, SENTENCE_MAX_CHARS);
  if (!chunks.length) {
    if (stillThisSpeak()) opts.onEnd?.();
    return;
  }
  const voice = pickVoice(voices, lang);
  const rate = utteranceRate(lang, opts.rate);
  const utterLang = lang === "en" ? "en-GB" : "fr-FR";
  let chunkIdx = 0;
  let retried = false;

  const speakChunk = () => {
    if (!stillThisSpeak()) return;
    if (chunkIdx >= chunks.length) {
      clearKeepAlive();
      if (stillThisSpeak()) opts.onEnd?.();
      return;
    }
    const chunk = chunks[chunkIdx];
    const utter = new win.SpeechSynthesisUtterance(chunk.text);
    utter.lang = utterLang;
    utter.rate = rate;
    if (voice) utter.voice = voice;
    let hadBoundary = false;
    let settled = false;
    const started = nowMs(win);
    utter.onboundary = (ev) => {
      hadBoundary = true;
      const idx = Number(ev?.charIndex);
      if (Number.isFinite(idx)) opts.onBoundary?.(chunk.start + idx);
    };
    const finishUtter = () => {
      if (!stillThisSpeak() || settled) return;
      settled = true;
      const hasMoreChunks = chunkIdx < chunks.length - 1;
      const kind = voiceEndKind({
        hadBoundary,
        elapsedMs: nowMs(win) - started,
        alreadyRetried: retried,
        hasMoreChunks,
      });
      if (kind === "retry") {
        retried = true;
        speakChunk();
        return;
      }
      if (kind === "linear") {
        clearKeepAlive();
        if (opts.onLeadFailed) opts.onLeadFailed();
        else opts.onEnd?.();
        return;
      }
      retried = false;
      chunkIdx += 1;
      speakChunk();
    };
    utter.onend = finishUtter;
    utter.onerror = finishUtter;
    armKeepAlive(win);
    win.speechSynthesis.speak(utter);
  };
  speakChunk();
}

/**
 * Reads `text` aloud in `lang` ("fr" | "en"). Returns false when the browser
 * cannot speak. `onEnd` fires when the reading finishes or is cancelled.
 * `onLeadFailed` : onend immédiat après une relance → le film passe en linéaire
 * sans se terminer. Sans ce callback (Écouter), onEnd libère le bouton.
 */
export function speak(text, lang = "fr", {
  onEnd,
  onBoundary,
  onLeadFailed,
  rate = 1,
  win = typeof window !== "undefined" ? window : null,
} = {}) {
  if (!canSpeak(win)) return false;
  const body = spokenText(text);
  if (!body) return false;
  stopSpeaking(win);
  const opts = { onEnd, onBoundary, onLeadFailed, rate, win };
  const voices = getVoices(win);
  if (voices.length) {
    beginUtterances(body, lang, opts, voices);
    return true;
  }
  waitForVoices(win, VOICES_WAIT_MS).then((ready) => {
    beginUtterances(body, lang, opts, ready);
  });
  return true;
}
