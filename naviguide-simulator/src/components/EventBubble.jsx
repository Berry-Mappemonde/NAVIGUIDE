import { useMemo } from "react";
import { createRoot } from "react-dom/client";
import { LocateFixed } from "lucide-react";
import { canFocus, entityLinks } from "../engine/briefingLinks.js";
import { LangProvider, useLang } from "../i18n/LangContext.jsx";
import {
  EVENT_BUBBLE_FADE_MS,
  bubbleChips,
  bubbleFacts,
  bubbleId,
  bubbleKindIcon,
  bubbleTitle,
  createEventPopupOptions,
  ensureEventPopup,
  followPopupToMarker,
} from "./eventBubble.js";

export {
  EVENT_BUBBLE_FADE_MS,
  EVENT_BUBBLE_MIN_MS,
  EVENT_BUBBLE_TITLE_MAX,
  EVENT_BUBBLE_WIDTH,
  EventBubbleGate,
  bubbleChips,
  bubbleFacts,
  bubbleId,
  bubbleKindIcon,
  bubbleTitle,
  createEventPopupOptions,
  ensureEventPopup,
  followPopupToMarker,
  isNowAlertOrDecision,
  pickFilmEvent,
  publishEventBubble,
} from "./eventBubble.js";

function CardLinks({ entity, t }) {
  if (!entity) return null;
  const links = entityLinks(entity);
  const focusable = canFocus(entity);
  if (!links.length && !focusable) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
      {focusable ? (
        <button
          type="button"
          onClick={() => {
            try {
              window.__naviguideScene?.callbacks?.onBriefingFocus?.(entity);
            } catch { /* recette / tests */ }
          }}
          data-testid="event-bubble-focus"
          title={t("briefingSeeOnMap")}
          className="flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold border border-sky-400/40 bg-sky-600/20 text-sky-100 hover:bg-sky-600/40"
        >
          <LocateFixed size={11} />
          {t("momentSeeOnMap")}
        </button>
      ) : null}
      {links.map((l) => (
        <a
          key={l.kind}
          href={l.href}
          target="_blank"
          rel="noopener noreferrer"
          data-testid={`event-bubble-link-${l.kind}`}
          title={l.kind === "site" ? `${t("briefingOfficialSheet")} — ${l.host || ""}` : t("briefingGoogleMaps")}
          className="px-1.5 py-0.5 rounded-md text-[10px] border border-white/10 bg-white/5 text-sky-200 hover:text-white hover:bg-white/10 no-underline"
        >
          {l.kind === "site" ? `↗ ${l.host || t("briefingOfficialSheet")}` : `◎ ${t("briefingGoogleMaps")}`}
        </a>
      ))}
    </div>
  );
}

export function EventBubble({ card }) {
  const { t } = useLang();
  const title = useMemo(() => bubbleTitle(card), [card]);
  const facts = useMemo(() => bubbleFacts(card), [card]);
  const chips = useMemo(() => bubbleChips(card), [card]);
  if (!card) return null;
  return (
    <div
      data-testid="event-bubble"
      data-kind={card.kind || ""}
      data-type={card.type || ""}
      className="event-bubble-card"
    >
      <div className="flex items-start gap-2 min-w-0">
        <span className="text-[16px] leading-none flex-shrink-0" aria-hidden="true">{bubbleKindIcon(card)}</span>
        <div className="min-w-0 flex-1">
          {title ? <div className="text-[12px] font-semibold text-sky-100 leading-snug">{title}</div> : null}
          {facts ? (
            <p className="event-bubble-facts mt-0.5 text-[11px] leading-snug text-slate-100 break-words [overflow-wrap:anywhere]">
              {facts}
            </p>
          ) : null}
        </div>
      </div>
      {chips.length ? (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {chips.map((c) => (
            <span
              key={c.id}
              data-testid={`event-bubble-chip-${c.id}`}
              className="px-1.5 py-0.5 rounded-md text-[10px] font-semibold bg-white/10 text-white/85 border border-white/10"
            >
              {c.id === "wind" ? `${t("eventBubbleChipWind")} ${c.kn} kn`
                : c.id === "hs" ? `${t("eventBubbleChipHs")} ${Number(c.m).toFixed(1)} m`
                  : t("eventBubbleChipQuay", { n: c.n })}
            </span>
          ))}
        </div>
      ) : null}
      <CardLinks entity={card.entity} t={t} />
    </div>
  );
}

function renderBubble(root, host, card) {
  if (!host || !root) return;
  root.render(card ? (
    <LangProvider>
      <EventBubble card={card} />
    </LangProvider>
  ) : null);
}

/**
 * Un seul `L.popup` ancré au marqueur principal. `setLatLng` à chaque
 * déplacement. Échap ferme la bulle, pas le film.
 */
export function attachEventBubble(scene, L) {
  const popup = ensureEventPopup(null, L);
  // Ne pas laisser popupFit déporter la bulle : la flèche reste sur le bateau.
  popup._biFitting = true;
  const canDom = typeof document !== "undefined";
  const host = canDom ? document.createElement("div") : { nodeType: 1 };
  let root = null;
  if (canDom) {
    try { root = createRoot(host); } catch { root = null; }
  }
  let open = false;
  let hideTimer = 0;
  let visibleTimer = 0;
  let currentCard = null;
  let closedByEsc = false;

  const win = typeof window !== "undefined" ? window : null;

  function markerOf() {
    return typeof scene.mainBoatMarker === "function" ? scene.mainBoatMarker() : null;
  }

  function follow() {
    return followPopupToMarker(popup, markerOf());
  }

  function setVisible(on) {
    const el = popup._container;
    if (!el) return;
    el.classList.toggle("event-bubble--visible", Boolean(on));
  }

  function hide({ immediate = false } = {}) {
    if (!open && !popup._map) return;
    if (hideTimer) clearTimeout(hideTimer);
    if (visibleTimer) clearTimeout(visibleTimer);
    setVisible(false);
    const close = () => {
      try { popup.remove(); } catch { /* déjà retiré */ }
      open = false;
      renderBubble(root, host, null);
    };
    if (immediate || !canDom) close();
    else hideTimer = setTimeout(close, EVENT_BUBBLE_FADE_MS);
  }

  function show(card) {
    currentCard = card || null;
    if (!card) {
      hide();
      return;
    }
    const marker = markerOf();
    if (!marker) return;
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = 0;
    }
    renderBubble(root, host, card);
    popup.setContent(host);
    popup.setLatLng(marker.getLatLng());
    if (!open) {
      try { popup.openOn(scene.map); } catch { /* carte absente (tests) */ }
      open = true;
    }
    follow();
    if (visibleTimer) clearTimeout(visibleTimer);
    visibleTimer = setTimeout(() => setVisible(true), 16);
  }

  function setCard(card) {
    currentCard = card || null;
    if (!card) {
      hide();
      return;
    }
    if (closedByEsc && bubbleId(card) === closedByEsc) return;
    closedByEsc = false;
    show(card);
  }

  function onEsc(event) {
    if (event.key !== "Escape" && event.key !== "Esc") return;
    if (!open) return;
    event.stopPropagation();
    closedByEsc = bubbleId(currentCard) || true;
    currentCard = null;
    hide();
  }

  win?.addEventListener("keydown", onEsc);

  const api = {
    popup,
    follow,
    sync() {
      follow();
      if (closedByEsc) return;
      const pending = currentCard || win?.__naviguideEventBubble || null;
      if (pending && !open && markerOf()) show(pending);
    },
    setCard,
    hide,
    dispose() {
      win?.removeEventListener("keydown", onEsc);
      if (hideTimer) clearTimeout(hideTimer);
      if (visibleTimer) clearTimeout(visibleTimer);
      hide({ immediate: true });
      try { root?.unmount(); } catch { /* tests */ }
    },
  };
  scene.eventBubble = api;
  if (win?.__naviguideEventBubble) api.setCard(win.__naviguideEventBubble);
  return api;
}
