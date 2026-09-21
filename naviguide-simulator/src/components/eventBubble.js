import { KIND_ICON } from "../engine/journalFormat.js";

export const EVENT_BUBBLE_MIN_MS = 3000;
export const EVENT_BUBBLE_FADE_MS = 200;
export const EVENT_BUBBLE_WIDTH = 280;
export const EVENT_BUBBLE_TITLE_MAX = 40;
export const BUBBLE_SCORE_SHOW = 2;
export const BUBBLE_SCORE_SUM = 3;
export const BUBBLE_SCORE_WINDOW_MS = 20_000;

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

/** Score bulle : 1 / 2 / 3, sinon inféré du kind (script local sans score). */
export function bubbleScore(ev) {
  const n = Number(ev?.score ?? ev?.card?.score);
  if (n === 1 || n === 2 || n === 3) return n;
  const kind = ev?.kind || ev?.card?.kind;
  if (kind === "stop" || kind === "wx") return 3;
  if (kind === "zee" || kind === "sci") return 2;
  if (kind === "amp" || kind === "climo") return 1;
  return 0;
}

/** ≥ 2 : tout de suite. Score 1 : quand la somme des non-montrés atteint 3. */
export function shouldShowFilmEvent(score, pendingScores = []) {
  const s = Number(score) || 0;
  if (s >= BUBBLE_SCORE_SHOW) return true;
  const sum = pendingScores.reduce((n, x) => n + (Number(x) || 0), 0) + s;
  return sum >= BUBBLE_SCORE_SUM;
}

export function filmEventCard(ev) {
  if (!ev) return null;
  const card = ev.card && typeof ev.card === "object" ? ev.card : {};
  const title = card.title || ev.title || ev.kind || "";
  const text = card.text || ev.fact || "";
  return {
    ...card,
    id: card.id || ev.id,
    key: card.key || ev.id || card.key,
    kind: card.kind || ev.kind,
    title,
    text,
    score: ev.score ?? card.score,
    lane: card.lane || "now",
  };
}

export function applyBubbleClose(currentCard) {
  return { card: null, closedId: bubbleId(currentCard) || true };
}

export function isBubbleSuppressed(closedId, nextCard) {
  return Boolean(closedId && nextCard && bubbleId(nextCard) === closedId);
}

/**
 * Une seule candidature à la fois : score ≥ 2, ou somme des scores
 * non montrés depuis 20 s ≥ 3.
 */
export class FilmEventScoreGate {
  constructor({ now = () => Date.now() } = {}) {
    this.now = now;
    this.pending = [];
    this.accepted = new Set();
  }

  reset() {
    this.pending = [];
    this.accepted = new Set();
  }

  accept(ev) {
    if (!ev) return null;
    const id = ev.id || bubbleId(ev.card) || bubbleId(ev);
    if (id && this.accepted.has(id)) return ev;
    const t = this.now();
    this.pending = this.pending.filter((p) => t - p.t <= BUBBLE_SCORE_WINDOW_MS);
    const score = bubbleScore(ev);
    const pendingScores = this.pending.map((p) => p.score);
    if (!shouldShowFilmEvent(score, pendingScores)) {
      if (score > 0 && id && !this.pending.some((p) => p.id === id)) {
        this.pending.push({ id, score, t });
      }
      return null;
    }
    if (id) this.accepted.add(id);
    this.pending = [];
    return ev;
  }
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
