import { KIND_ICON } from "../engine/journalFormat.js";

export const EVENT_BUBBLE_MIN_MS = 3000;
export const EVENT_BUBBLE_FADE_MS = 200;
export const EVENT_BUBBLE_WIDTH = 280;
export const EVENT_BUBBLE_TITLE_MAX = 40;

export function createEventPopupOptions() {
  return {
    autoPan: false,
    closeButton: false,
    className: "event-bubble",
    maxWidth: EVENT_BUBBLE_WIDTH,
    minWidth: EVENT_BUBBLE_WIDTH,
    closeOnClick: false,
    autoClose: false,
    keepInView: false,
  };
}

export function ensureEventPopup(popup, L) {
  return popup || L.popup(createEventPopupOptions());
}

export function bubbleId(card) {
  if (!card) return null;
  return card.key || card.id || card.stableKey || `${card.kind || "?"}:${card.at || card.title || ""}`;
}

export function isNowAlertOrDecision(card) {
  if (!card) return false;
  if (card.severity === "alert") return true;
  if (card.lane === "now") return true;
  return card.judge === "now";
}

export function bubbleTitle(card, max = EVENT_BUBBLE_TITLE_MAX) {
  const raw = String(card?.title || card?.kind || "").trim();
  if (raw.length <= max) return raw;
  return `${raw.slice(0, Math.max(1, max - 1)).trimEnd()}…`;
}

export function bubbleFacts(card) {
  const text = String(card?.text || "").trim();
  if (!text) return "";
  const sentences = text.split(/(?<=[.!?])\s+/).filter(Boolean);
  return sentences.slice(0, 2).join(" ");
}

export function bubbleKindIcon(card) {
  return KIND_ICON[card?.kind] || "•";
}

export function bubbleChips(card) {
  const facts = card?.facts && typeof card.facts === "object" ? card.facts : {};
  const src = { ...facts, ...card };
  const chips = [];
  const wind = Number(src.windKnots ?? src.windKn ?? src.maxWindKnots);
  const hs = Number(src.hs ?? src.maxHs);
  const days = Number(src.daysAtQuay ?? src.quayDays);
  if (Number.isFinite(wind)) chips.push({ id: "wind", kn: Math.round(wind) });
  if (Number.isFinite(hs)) chips.push({ id: "hs", m: hs });
  if (Number.isFinite(days) && days > 0) chips.push({ id: "quay", n: Math.round(days) });
  return chips;
}

function eventMs(ev, chapter, plan) {
  const raw = ev?.card?.at || ev?.t || ev?.at || "";
  const parsed = Date.parse(raw);
  if (Number.isFinite(parsed)) return parsed;
  if (plan?.timeAt && chapter && ev) return plan.timeAt(chapter.idx, ev.charIdx);
  return null;
}

/** Voix : dernier événement dont `charIdx` est franchi. Sans voix : à la date. */
export function pickFilmEvent({
  chapter,
  charIdx = 0,
  tMs = null,
  voiceLed = false,
  plan = null,
} = {}) {
  const events = chapter?.events || [];
  if (!events.length) return null;
  let best = null;
  for (const ev of events) {
    if (voiceLed) {
      if ((Number(ev.charIdx) || 0) <= charIdx) best = ev;
      continue;
    }
    const at = eventMs(ev, chapter, plan);
    if (at != null && tMs != null) {
      if (at <= tMs) best = ev;
    } else if ((Number(ev.charIdx) || 0) <= charIdx) {
      best = ev;
    }
  }
  return best;
}

/**
 * Une seule carte à la fois, minimum 3 s, Échap la ferme sans toucher au film.
 * `now` est injectable (faux timers).
 */
export class EventBubbleGate {
  constructor({ now = () => Date.now() } = {}) {
    this.now = now;
    this.card = null;
    this.since = 0;
    this.pending = undefined;
    this.hasPending = false;
    this.dismissed = null;
  }

  reset() {
    this.card = null;
    this.since = 0;
    this.pending = undefined;
    this.hasPending = false;
    this.dismissed = null;
  }

  dismiss() {
    this.dismissed = bubbleId(this.card);
    this.card = null;
    this.since = this.now();
    this.pending = undefined;
    this.hasPending = false;
    return null;
  }

  tick() {
    if (!this.hasPending) return this.card;
    if (this.now() - this.since < EVENT_BUBBLE_MIN_MS) return this.card;
    this.card = this.pending;
    this.since = this.now();
    this.pending = undefined;
    this.hasPending = false;
    return this.card;
  }

  propose(candidate) {
    this.tick();
    const id = bubbleId(candidate);
    if (candidate && this.dismissed && id === this.dismissed) return this.card;
    if (candidate && id !== this.dismissed) this.dismissed = null;
    if (!candidate) return this.card;
    if (bubbleId(this.card) === id) return this.card;
    if (this.card && this.now() - this.since < EVENT_BUBBLE_MIN_MS) {
      this.pending = candidate;
      this.hasPending = true;
      return this.card;
    }
    this.card = candidate;
    this.since = this.now();
    this.pending = undefined;
    this.hasPending = false;
    return this.card;
  }
}

export function followPopupToMarker(popup, marker) {
  if (!popup || !marker) return null;
  const ll = marker.getLatLng();
  popup.setLatLng(ll);
  return popup.getLatLng();
}

export function publishEventBubble(card) {
  if (typeof window === "undefined") return;
  window.__naviguideEventBubble = card || null;
  window.__naviguideScene?.eventBubble?.setCard(card || null);
}
