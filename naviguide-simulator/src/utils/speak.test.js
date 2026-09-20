import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { canLeadWithVoice, canSpeak, speak, spokenText, stopSpeaking } from "./speak.js";

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
  });
});
