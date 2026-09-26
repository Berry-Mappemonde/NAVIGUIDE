import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  canLeadWithVoice,
  canSpeak,
  pickVoice,
  speak,
  splitUtterances,
  spokenText,
  stopSpeaking,
  utteranceRate,
  voiceEndKind,
  waitForVoices,
} from "./speak.js";

describe("speak", () => {
  it("spokenText drops links and glyphs, keeps sentences", () => {
    const raw = "Le bateau est en mer ↗ https://sextant.ifremer.fr/x ◎\nVent 8 kn de NNO (329°) · Hs 0,6 m.";
    assert.equal(spokenText(raw), "Le bateau est en mer. Vent 8 kn de NNO (329°) Hs 0,6 m.");
    assert.equal(spokenText(""), "");
    assert.equal(spokenText(null), "");
  });

  it("is a no-op without speechSynthesis", () => {
    assert.equal(canSpeak({}), false);
    assert.equal(speak("bonjour", "fr", { win: {} }), false);
    stopSpeaking({}); // must not throw
  });

  it("speaks through the provided window in the right language", () => {
    const spoken = [];
    let cancelled = 0;
    class Utter { constructor(text) { this.text = text; } }
    const win = {
      SpeechSynthesisUtterance: Utter,
      speechSynthesis: {
        speaking: false,
        cancel: () => { cancelled += 1; },
        getVoices: () => [{ lang: "fr-FR", name: "Amélie" }, { lang: "en-GB", name: "Daniel" }],
        speak: (u) => spoken.push(u),
      },
    };
    assert.equal(speak("Bonjour ↗ https://a.b", "fr", { win }), true);
    assert.equal(cancelled, 1);
    assert.equal(spoken[0].text, "Bonjour");
    assert.equal(spoken[0].lang, "fr-FR");
    assert.equal(spoken[0].voice.name, "Amélie");
    assert.equal(speak("Hello", "en", { win }), true);
    assert.equal(spoken[1].lang, "en-GB");
    assert.equal(spoken[1].voice.name, "Daniel");
    assert.equal(speak("   ", "fr", { win }), false);
    assert.equal(canLeadWithVoice(win), true);
    assert.equal(canLeadWithVoice({}), false);
    assert.equal(canLeadWithVoice({
      ...win,
      navigator: { webdriver: true },
    }), false);
    const heard = [];
    speak("Cap au large", "fr", {
      win,
      rate: 2,
      onBoundary: (i) => heard.push(i),
    });
    assert.equal(spoken[2].rate, 1.25);
    spoken[2].onboundary({ charIndex: 4 });
    assert.deepEqual(heard, [4]);
    assert.equal(utteranceRate("en", 1), 0.95);
    assert.equal(spoken[1].rate, 0.95);
  });
});

describe("speak lot R3", () => {
  it("découpe en phrases ≤ 200 caractères et garde un charIdx global croissant", () => {
    const long = `${"La mer est belle. ".repeat(8)}${"Vent fort, mer formée, cap à l'ouest sans relâche. ".repeat(6)}Fin.`;
    const chunks = splitUtterances(long, 200);
    assert.ok(chunks.length >= 2);
    assert.ok(chunks.every((c) => c.text.length <= 200));
    const idxs = [];
    for (const c of chunks) {
      idxs.push(c.start);
      idxs.push(c.start + Math.max(0, c.text.length - 1));
    }
    for (let i = 1; i < idxs.length; i++) {
      assert.ok(idxs[i] >= idxs[i - 1], `charIdx ${idxs[i - 1]} → ${idxs[i]}`);
    }
    assert.ok(idxs[idxs.length - 1] >= idxs[0]);
  });

  it("choisit la voix par liste de préférence sur une liste factice", () => {
    const en = [
      { name: "Alex", lang: "en-US" },
      { name: "Daniel", lang: "en-GB" },
      { name: "Google UK English Female", lang: "en-GB" },
    ];
    assert.equal(pickVoice(en, "en").name, "Google UK English Female");
    const fr = [
      { name: "Audrey", lang: "fr-FR" },
      { name: "Thomas", lang: "fr-FR" },
      { name: "Google français", lang: "fr-FR" },
    ];
    assert.equal(pickVoice(fr, "fr").name, "Google français");
    assert.equal(pickVoice([{ name: "Moira", lang: "en-IE" }], "en").name, "Moira");
    assert.equal(pickVoice([{ name: "Samantha", lang: "en-US" }], "en").name, "Samantha");
  });

  it("onend immédiat sans boundary : une relance, puis linéaire sans onEnd", () => {
    assert.equal(voiceEndKind({ hadBoundary: false, elapsedMs: 80, alreadyRetried: false }), "retry");
    assert.equal(voiceEndKind({ hadBoundary: false, elapsedMs: 80, alreadyRetried: true }), "linear");
    assert.equal(voiceEndKind({ hadBoundary: true, elapsedMs: 80, alreadyRetried: false }), "advance");
    assert.equal(voiceEndKind({
      hadBoundary: false, elapsedMs: 80, alreadyRetried: false, hasMoreChunks: true,
    }), "advance");
    assert.equal(voiceEndKind({
      hadBoundary: false, elapsedMs: 80, alreadyRetried: true, hasMoreChunks: true,
    }), "advance");

    const spoken = [];
    class Utter { constructor(text) { this.text = text; } }
    const win = {
      SpeechSynthesisUtterance: Utter,
      performance: { now: () => 0 },
      speechSynthesis: {
        speaking: false,
        cancel() {},
        getVoices: () => [{ lang: "fr-FR", name: "Thomas" }],
        speak(u) {
          spoken.push(u);
          u.onend?.();
        },
      },
    };
    let ended = 0;
    let failed = 0;
    speak("Bonjour tout le monde.", "fr", {
      win,
      onEnd: () => { ended += 1; },
      onLeadFailed: () => { failed += 1; },
    });
    assert.equal(spoken.length, 2, "une relance de la même utterance");
    assert.equal(failed, 1);
    assert.equal(ended, 0, "le chapitre ne se termine pas — le film reste en linéaire");
    stopSpeaking(win);
  });

  it("onend prématuré au milieu des chunks → le texte continue au chunk suivant", () => {
    const long = `${"La mer est belle et le vent porte. ".repeat(8)}${"Cap à l'ouest sans relâche vers l'escale suivante. ".repeat(6)}Fin du chapitre.`;
    const chunks = splitUtterances(long, 200);
    assert.ok(chunks.length >= 2, "le texte doit tenir en plusieurs chunks");

    const spoken = [];
    class Utter { constructor(text) { this.text = text; } }
    const win = {
      SpeechSynthesisUtterance: Utter,
      performance: { now: () => 0 },
      speechSynthesis: {
        speaking: false,
        cancel() {},
        getVoices: () => [{ lang: "fr-FR", name: "Thomas" }],
        speak(u) { spoken.push(u); },
      },
    };
    let ended = 0;
    let failed = 0;
    speak(long, "fr", {
      win,
      onEnd: () => { ended += 1; },
      onLeadFailed: () => { failed += 1; },
    });
    assert.equal(spoken.length, 1);
    assert.equal(spoken[0].text, chunks[0].text);
    spoken[0].onend?.();
    assert.equal(spoken.length, 2, "chunk suivant parlé, pas d'abandon");
    assert.equal(spoken[1].text, chunks[1].text);
    assert.equal(failed, 0, "pas de bascule linéaire tant qu'il reste des chunks");
    assert.equal(ended, 0, "le chapitre ne se termine pas sur l'incident");
    stopSpeaking(win);
    spoken[1].onend?.();
    spoken[1].onerror?.();
    assert.equal(spoken.length, 2, "cancel : pas de relance");
    assert.equal(ended, 0);
    assert.equal(failed, 0);
  });

  it("waitForVoices résout tout de suite si la liste est déjà là", async () => {
    const win = { speechSynthesis: { getVoices: () => [{ name: "Thomas", lang: "fr-FR" }] } };
    const voices = await waitForVoices(win, 50);
    assert.equal(voices[0].name, "Thomas");
  });
});
