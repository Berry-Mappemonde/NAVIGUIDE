import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  EVENT_BUBBLE_MIN_MS,
  EventBubbleGate,
  bubbleId,
  bubbleTitle,
  createEventPopupOptions,
  ensureEventPopup,
  followPopupToMarker,
  pickFilmEvent,
} from "./eventBubble.js";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "EventBubble.jsx"), "utf8");
const logic = readFileSync(join(here, "eventBubble.js"), "utf8");
const sceneSrc = readFileSync(join(here, "..", "map", "MapSceneController.js"), "utf8");
const hook = readFileSync(join(here, "..", "hooks", "useReplay.js"), "utf8");
const cards = readFileSync(join(here, "MomentCards.jsx"), "utf8");

function fakePopup() {
  return {
    ll: null,
    content: null,
    setLatLng(v) {
      this.ll = Array.isArray(v) ? { lat: v[0], lng: v[1] } : v;
      return this;
    },
    getLatLng() { return this.ll; },
    setContent(c) { this.content = c; return this; },
    openOn() { return this; },
    remove() { return this; },
  };
}

function fakeMarker(lat, lng) {
  return {
    ll: { lat, lng },
    getLatLng() { return this.ll; },
    setLatLng(v) {
      this.ll = Array.isArray(v) ? { lat: v[0], lng: v[1] } : v;
    },
  };
}

describe("EventBubble — contrat (lot F4)", () => {
  it("L.popup : autoPan false, pas de croix, classe event-bubble, 280 px", () => {
    const opts = createEventPopupOptions();
    assert.equal(opts.autoPan, false);
    assert.equal(opts.closeButton, false);
    assert.equal(opts.className, "event-bubble");
    assert.equal(opts.maxWidth, 280);
    assert.equal(opts.minWidth, 280);
    assert.match(logic, /autoPan:\s*false/);
    assert.match(src, /ensureEventPopup/);
    assert.match(src, /className:\s*"event-bubble"|createEventPopupOptions/);
  });

  it("la bulle suit le marqueur (popup.getLatLng() = bateau après update)", () => {
    const popup = fakePopup();
    const marker = fakeMarker(46.15, -1.16);
    followPopupToMarker(popup, marker);
    assert.equal(popup.getLatLng().lat, marker.getLatLng().lat);
    assert.equal(popup.getLatLng().lng, marker.getLatLng().lng);
    marker.setLatLng([14.6, -61.07]);
    followPopupToMarker(popup, marker);
    assert.deepEqual(popup.getLatLng(), marker.getLatLng());
  });

  it("une seule bulle à la fois (un seul L.popup, la carte courante remplace)", () => {
    const created = [];
    const L = {
      popup(opts) {
        const p = { ...fakePopup(), opts };
        created.push(p);
        return p;
      },
    };
    const first = ensureEventPopup(null, L);
    const again = ensureEventPopup(first, L);
    assert.equal(created.length, 1);
    assert.equal(again, first);
    let t = 0;
    const gate = new EventBubbleGate({ now: () => t });
    assert.equal(bubbleId(gate.propose({ id: "a" })), "a");
    t = 4000;
    assert.equal(bubbleId(gate.propose({ id: "b" })), "b");
    assert.equal(bubbleId(gate.card), "b");
  });

  it("minimum 3 s avant de remplacer (faux timers)", () => {
    let t = 0;
    const gate = new EventBubbleGate({ now: () => t });
    assert.equal(bubbleId(gate.propose({ id: "a", title: "A" })), "a");
    t = 1000;
    assert.equal(bubbleId(gate.propose({ id: "b", title: "B" })), "a", "encore dans les 3 s");
    t = EVENT_BUBBLE_MIN_MS - 1;
    gate.tick();
    assert.equal(bubbleId(gate.card), "a");
    t = EVENT_BUBBLE_MIN_MS;
    gate.tick();
    assert.equal(bubbleId(gate.card), "b");
    const afterEsc = gate.dismiss();
    assert.equal(afterEsc, null);
    t = EVENT_BUBBLE_MIN_MS + 10;
    assert.equal(gate.propose({ id: "b", title: "B" }), null, "Échap : la même carte ne revient pas");
    assert.equal(bubbleId(gate.propose({ id: "c", title: "C" })), "c");
  });

  it("titre borné à 40 caractères ; pick film : charIdx (voix) / date (sans voix)", () => {
    assert.equal(bubbleTitle({ title: "Court" }).length <= 40, true);
    const long = "X".repeat(50);
    assert.equal(bubbleTitle({ title: long }).length, 40);
    const chapter = {
      idx: 0,
      events: [
        { id: "depart", charIdx: 0, card: { id: "depart", kind: "stop", at: "2026-05-15T06:00:00Z", title: "Départ" } },
        { id: "wx", charIdx: 80, card: { id: "wx", kind: "wx", at: "2026-05-27T12:00:00Z", title: "Coup de vent" } },
      ],
    };
    assert.equal(pickFilmEvent({ chapter, charIdx: 10, voiceLed: true })?.id, "depart");
    assert.equal(pickFilmEvent({ chapter, charIdx: 80, voiceLed: true })?.id, "wx");
    assert.equal(pickFilmEvent({
      chapter, voiceLed: false, tMs: Date.parse("2026-05-15T08:00:00Z"),
    })?.id, "depart");
    assert.equal(pickFilmEvent({
      chapter, voiceLed: false, tMs: Date.parse("2026-05-27T13:00:00Z"),
    })?.id, "wx");
  });

  it("la scène resynchronise la popup après syncMarkers ; le film et la carte NOW l’ouvrent", () => {
    assert.match(sceneSrc, /this\.eventBubble = attachEventBubble\(this, L\)/);
    assert.match(sceneSrc, /this\.eventBubble\?\.sync\(\)/);
    assert.match(sceneSrc, /mainBoatMarker\(/);
    assert.match(hook, /pickFilmEvent/);
    assert.match(hook, /publishEventBubble/);
    assert.match(cards, /publishEventBubble/);
    assert.match(cards, /isNowAlertOrDecision/);
    assert.match(src, /keydown/);
    assert.match(src, /Escape/);
    assert.match(src, /data-testid="event-bubble"/);
  });
});
