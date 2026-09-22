import { memo, useEffect, useState } from "react";
import { CheckCircle, ChevronLeft, ChevronRight, Pencil, Trash2 } from "lucide-react";
import { useLang } from "../i18n/LangContext.jsx";
import { SimulationPanel } from "./SimulationPanel";
import { JournalPanel } from "./JournalPanel.jsx";
import { IciMaintenant } from "./IciMaintenant.jsx";
import { LogbookChat } from "./LogbookChat.jsx";
import { VIEW_SIMULATION, VIEW_SUIVRE } from "../constants/viewMode.js";
import { canFocus, entityLinks } from "../engine/briefingLinks.js";

const API_URL = import.meta.env?.VITE_API_URL ?? "";

const STORY_SOURCE_I18N = Object.freeze({
  "nemotron-lightning": "storySourceLightning",
  "nemotron-super": "storySourceSuper",
  "nemotron-ultra": "storySourceUltra",
  openrouter: "storySourceOpenrouter",
  claude: "storySourceClaude",
  rules: "storySourceRules",
  budget: "storySourceBudget",
  cache: "storySourceCache",
});

function storySourceLabel(source, t) {
  return t(STORY_SOURCE_I18N[source] || "storySourceRules");
}

const NAVIGUIDE_LOGO = "/logo-naviguide.png";
const BERRY_LOGO = "/logo-berry-mappemonde.png";

function BerryCard({
  onCustomRoute, onRouteSwitchToBerry, isDrawing,
  onDrawStart, onDrawContinue, onDrawFinish, onDrawCancel, onCustomDelete, canContinueDraw,
  canFinishDraw = true,
}) {
  const { t } = useLang();
  const [cardMode, setCardMode] = useState("berry-active");
  const [drawnRoute, setDrawnRoute] = useState(null);
  const [drawnName, setDrawnName] = useState(null);
  const hasCustom = Boolean(drawnRoute);
  const customOn = cardMode === "file-active";

  useEffect(() => {
    if (!isDrawing && cardMode === "draw-mode") {
      setCardMode(hasCustom ? "berry-active-file-loaded" : "berry-active");
    }
  }, [isDrawing, cardMode, hasCustom]);

  const activateBerry = () => {
    setCardMode(hasCustom ? "berry-active-file-loaded" : "berry-active");
    onRouteSwitchToBerry();
  };

  const activateCustom = () => {
    if (!drawnRoute) return;
    setCardMode("file-active");
    onCustomRoute(drawnRoute);
  };

  const handleFinishDrawing = () => {
    const geojson = onDrawFinish();
    if (geojson?.features?.length > 0) {
      setDrawnRoute(geojson);
      setDrawnName(t("customRoute"));
      setCardMode("file-active");
      onCustomRoute(geojson);
    } else {
      setCardMode(hasCustom ? "berry-active-file-loaded" : "berry-active");
    }
  };

  const handleDelete = (e) => {
    e.stopPropagation();
    setDrawnRoute(null);
    setDrawnName(null);
    setCardMode("berry-active");
    onCustomDelete?.();
    onRouteSwitchToBerry();
  };

  const pillOn = "flex-1 min-w-0 px-2 py-1.5 rounded-lg text-[10px] font-semibold leading-tight border border-blue-400/60 bg-blue-600/30 text-blue-100";
  const pillOff = "flex-1 min-w-0 px-2 py-1.5 rounded-lg text-[10px] font-semibold leading-tight border border-slate-600/50 bg-slate-800/50 text-slate-400 hover:text-white hover:border-slate-500";

  const switcher = hasCustom ? (
    <div className="flex gap-1 mb-1.5">
      <button type="button" onClick={activateBerry} className={customOn ? pillOff : pillOn} title={t("backToBerry")}>
        {t("berryMappemonde")} {/* pragma: allowlist secret */}
      </button>
      <button type="button" onClick={activateCustom} className={customOn ? pillOn : pillOff} title={t("showRoute", { name: drawnName })}>
        {drawnName || t("customRoute")}
      </button>
    </div>
  ) : null;

  if (cardMode === "draw-mode" || isDrawing) {
    return (
      <div className="rounded-lg px-2 py-1.5 border border-slate-700/50 bg-slate-800/60">
        {switcher}
        {isDrawing ? (
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => {
                setCardMode(hasCustom ? "berry-active-file-loaded" : "berry-active");
                onDrawCancel?.();
              }}
              className="flex-1 flex items-center justify-center gap-1.5 bg-slate-700/40 hover:bg-slate-700/70
                border border-slate-500/50 rounded-lg px-2 py-1.5 text-[10px] text-slate-200 font-semibold"
            >
              {t("cancel")}
            </button>
            <button
              type="button"
              onClick={handleFinishDrawing}
              disabled={!canFinishDraw}
              className="flex-1 flex items-center justify-center gap-1.5 bg-green-600/30 hover:bg-green-600/50
                border border-green-500/50 rounded-lg px-2 py-1.5 text-[10px] text-green-300 font-semibold
                disabled:opacity-40 disabled:pointer-events-none"
            >
              <CheckCircle size={11} /> {t("finish")}
            </button>
          </div>
        ) : (
          <button
            onClick={() => { setCardMode("draw-mode"); onDrawStart(); }}
            className="w-full flex items-center justify-center gap-1.5 bg-violet-600/20 hover:bg-violet-600/40
              border border-violet-500/40 rounded-lg px-2 py-1.5 text-[10px] text-violet-300 font-medium"
          >
            <Pencil size={11} /> {t("drawOwnRoute")}
          </button>
        )}
      </div>
    );
  }

  if (cardMode === "file-active") {
    return (
      <div className="rounded-lg px-2 py-1.5 border border-blue-500/70 bg-blue-950/30">
        {switcher}
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => { setCardMode("draw-mode"); (canContinueDraw ? onDrawContinue : onDrawStart)?.(); }}
            className="flex-1 flex items-center justify-center gap-1 px-1.5 py-1 rounded-lg text-[10px]
              font-medium border border-violet-500/40 text-violet-300 hover:bg-violet-600/20"
          >
            <Pencil size={10} /> {canContinueDraw ? t("continueDrawing") : t("drawOwnRoute")}
          </button>
          <button
            type="button"
            onClick={handleDelete}
            title={t("deleteCustomRoute")}
            className="flex items-center justify-center px-2 py-1 rounded-lg text-[10px]
              border border-red-500/40 text-red-300 hover:bg-red-600/20"
          >
            <Trash2 size={10} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg px-2 py-1.5 border border-blue-500/70 bg-blue-950/30">
      {switcher}
      <button
        onClick={() => { setCardMode("draw-mode"); onDrawStart(); }}
        title={t("drawOwnRoute")}
        className="w-full flex items-center gap-2 rounded-lg px-1.5 py-1 hover:bg-blue-900/30 cursor-pointer"
      >
        <img src={BERRY_LOGO} alt="Berry-Mappemonde" className="h-7 w-auto object-contain rounded flex-shrink-0" style={{ maxWidth: 48 }} /> {/* pragma: allowlist secret */}
        <div className="text-left">
          <div className="text-white font-bold text-[11px] leading-tight tracking-wide">{t("berryMappemonde")}</div> {/* pragma: allowlist secret */}
          <div className="text-[10px] text-violet-300">{t("drawOwnRoute")}</div>
        </div>
      </button>
    </div>
  );
}

/**
 * Briefing with links. Each place the bag named:
 *   - the name → "voir sur la carte" (layer on + fit boat & place), when it has coordinates
 *   - ↗ → official sheet (Sextant, douane, marina site…) when the bag has a URL
 *   - ◎ → Google Maps sheet, for real places (marinas, ports, anchorages, AtoN, PoE)
 * Plain text is untouched: segments joined === narrateIci().
 */
function BriefingText({ segments, onFocus, t }) {
  return segments.map((seg, i) => {
    if (!seg.entity) return <span key={i}>{seg.text}</span>;
    const e = seg.entity;
    if (e.kind === "source" && e.url) {
      return (
        <a
          key={i}
          href={e.url}
          target="_blank"
          rel="noopener noreferrer"
          title={t("briefingSourceLink")}
          data-testid="briefing-source-link"
          data-kind="source"
          className="text-sky-200 underline decoration-sky-400/70 underline-offset-2 hover:text-white"
        >
          {seg.text}
        </a>
      );
    }
    const links = entityLinks(e);
    const focusable = canFocus(e) && typeof onFocus === "function";
    return (
      <span key={i} className="inline whitespace-nowrap" data-testid="briefing-entity" data-kind={e.kind}>
        {focusable ? (
          <button
            type="button"
            onClick={() => onFocus(e)}
            title={t("briefingSeeOnMap")}
            className="inline text-sky-200 underline decoration-dotted decoration-sky-400/70 underline-offset-2 hover:text-white whitespace-normal text-left"
          >
            {seg.text}
          </button>
        ) : (
          <span className="text-slate-200">{seg.text}</span>
        )}
        {links.map((l) => (
          <a
            key={l.kind}
            href={l.href}
            target="_blank"
            rel="noopener noreferrer"
            title={l.kind === "site" ? `${t("briefingOfficialSheet")} — ${l.host || ""}` : t("briefingGoogleMaps")}
            aria-label={l.kind === "site" ? t("briefingOfficialSheet") : t("briefingGoogleMaps")}
            data-testid={`briefing-link-${l.kind}`}
            className="ml-0.5 text-[10px] text-sky-300/80 hover:text-white align-baseline no-underline"
          >
            {l.kind === "site" ? "↗" : "◎"}
          </a>
        ))}
      </span>
    );
  });
}

export const Sidebar = memo(function Sidebar({
  plan, open, onToggle, onCustomRoute, onRouteSwitchToBerry, isDrawing,
  onDrawStart, onDrawContinue, onDrawFinish, onDrawCancel, onCustomDelete, canContinueDraw,
  canFinishDraw, drawing = null, onDrawUndo,
  isCockpit, polarData, view = VIEW_SUIVRE,
  legContext, briefingLoading, officialFallback,
  iciBriefing = null,
  iciBriefingSegments = null, onBriefingFocus,
  skipperNotice = null,
  clockSample = null, atQuay = false, quayDays = 0,
  previewing = false, forecastStatus = null,
  onRecompute, canRecompute = false, recomputeBusy = false, onGoLive,
  journal = null, journalLoading = false, journalError = null,
  story = null, storyReplay = false,
  momentNow = null, momentNowLeft = 0, onMomentDismiss,
  momentFree = null, momentFreeLeft = 0, onMomentNext,
  chat = null, onChatAsk,
  moment = null,
  escaleStop = null,
  escaleFiche = null,
  escaleLoading = false,
  escaleError = null,
  onEscaleClose,
}) {
  const { t } = useLang();
  const [storySource, setStorySource] = useState("rules");
  const isSimulation = view === VIEW_SIMULATION;
  const isSuivre = view === VIEW_SUIVRE;
  const expeditionBriefing = plan?.executive_briefing || "";
  const briefing = iciBriefing || expeditionBriefing;
  const briefingTitle = !iciBriefing && typeof plan?.briefing_title === "string"
    ? plan.briefing_title.trim()
    : "";
  const showIciBriefing = !isDrawing && (isCockpit || briefing || briefingLoading || skipperNotice);

  useEffect(() => {
    if (!showIciBriefing) return undefined;
    let cancelled = false;
    const ctrl = new AbortController();
    fetch(`${API_URL}/ici/warm/status`, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        const src = data?.llm?.lastSource;
        if (!cancelled && typeof src === "string" && src.trim()) setStorySource(src.trim());
      })
      .catch(() => { /* sans API : on garde « règles » */ });
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, [showIciBriefing, briefing]);

  return (
    <>
      <button
        onClick={onToggle}
        className={`naviguide-sidebar-toggle naviguide-sidebar-toggle--left absolute z-30 bg-slate-900/95 text-white
          rounded-full flex items-center justify-center shadow-lg
          hover:bg-slate-800 transition-all duration-300
          w-9 h-9 border border-slate-700
          ${open ? "left-[322px] top-4" : "left-4 top-[92px]"}`}
        title={open ? t("hideSidebar") : t("showExpeditionPanel")}
      >
        {open ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
      </button>

      <div
        className={`naviguide-sidebar-panel absolute top-0 left-0 h-full z-20 flex flex-col bg-slate-900/97
          shadow-2xl transition-transform duration-300 border-r border-slate-700/60
          ${open ? "translate-x-0" : "-translate-x-full"}`}
        style={{ width: 320 }}
      >
        <div className="px-2.5 pt-1.5 pb-1.5 border-b border-slate-700/60 flex-shrink-0">
          <div className="flex items-center gap-2 mb-1">
            <img src={NAVIGUIDE_LOGO} alt={t("brandTitle")} className="h-9 w-9 object-contain drop-shadow" />
            <span className="text-white font-bold text-[11px] leading-tight tracking-wide">{t("brandTitle")}</span>
          </div>

          <BerryCard
            onCustomRoute={onCustomRoute}
            onRouteSwitchToBerry={onRouteSwitchToBerry}
            isDrawing={isDrawing}
            onDrawStart={onDrawStart}
            onDrawContinue={onDrawContinue}
            onDrawFinish={onDrawFinish}
            onDrawCancel={onDrawCancel}
            onCustomDelete={onCustomDelete}
            canContinueDraw={canContinueDraw}
            canFinishDraw={canFinishDraw}
          />

          {!isDrawing && chat ? (
            <div className="mt-1.5">
              <LogbookChat messages={chat.messages} pending={chat.pending} error={chat.error} onAsk={onChatAsk} />
            </div>
          ) : null}
        </div>

        <div className="flex-1 min-h-0 overflow-hidden flex flex-col px-2.5 py-1.5 gap-1.5">
          {!isCockpit && !plan && !briefingLoading && !isDrawing && (
            <div className="rounded-lg border border-blue-700/30 bg-blue-950/20 p-2 shrink-0">
              <div className="text-[10px] font-semibold text-blue-300 mb-1">{t("gettingStarted")}</div>
              <p className="text-[11px] text-slate-400 leading-snug">{t("gettingStartedText")}</p>
            </div>
          )}

          {isDrawing && (
            <div className="bg-slate-800/50 rounded-lg p-2 border border-slate-700/50 shrink-0">
              <p className="text-[11px] text-slate-300 leading-snug whitespace-pre-line">{t("briefingDrawHint")}</p>
            </div>
          )}
          {isDrawing && drawing ? (
            <div data-testid="drawing-points" className="rounded-lg border border-emerald-500/30 bg-emerald-950/30 p-2 min-w-0 shrink-0">
              <div className="flex items-center gap-2 mb-1">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-emerald-200 leading-snug flex-1">
                  {t("drawingInProgress")} · {drawing.points.length} {t("drawingPoints")} · {Number(drawing.distanceNm || 0).toLocaleString()} nm
                </div>
                {drawing.points.length && onDrawUndo ? (
                  <button type="button" onClick={onDrawUndo} className="text-[10px] px-1.5 py-0.5 rounded-md bg-white/5 border border-white/10 hover:bg-white/10 text-white/80" title={t("drawingUndoLast")}>
                    ↶ {t("drawingUndoLast")}
                  </button>
                ) : null}
              </div>
              {drawing.points.length ? (
                <ol className="space-y-0.5">
                  {drawing.points.map((p, i) => (
                    <li key={`${p.lat}-${p.lon}-${i}`} className="text-[11px] text-slate-100 leading-snug flex items-baseline gap-1">
                      <span className="text-[9px] text-emerald-300/80 w-4 shrink-0">{i + 1}</span>
                      <span className="truncate">{p.name}</span>
                      <span className="ml-auto text-[9px] text-slate-500 tabular-nums shrink-0">{p.lat.toFixed(2)}° · {p.lon.toFixed(2)}°</span>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-[10px] text-slate-400 leading-snug">{drawing.message}</p>
              )}
            </div>
          ) : null}

          {officialFallback && (
            <p className="text-[10px] text-amber-300/90 border border-amber-500/30 rounded-md px-2 py-1 shrink-0">
              {t("searouteUnavailable")}
            </p>
          )}

          <IciMaintenant
            moment={moment}
            momentNow={!isDrawing ? momentNow : null}
            momentFree={!isDrawing ? momentFree : null}
            simulation={!isDrawing ? (
              <SimulationPanel
                legContext={legContext}
                clockSample={clockSample}
                kindLabel=""
                atQuay={atQuay}
                quayDays={quayDays}
                liveFollow={isSuivre}
                previewing={previewing}
                forecastStatus={isSuivre ? forecastStatus : null}
                onRecompute={onRecompute}
                canRecompute={canRecompute}
                showRecompute={isSimulation}
                recomputeBusy={recomputeBusy}
                onGoLive={onGoLive}
              />
            ) : null}
            hereBody={!isDrawing ? (
              <div data-testid="here-product">
                <div data-testid="briefing" className="sim-box-ici min-w-0 overflow-x-hidden h-auto">
                  {briefingTitle ? (
                    <div className="text-[10px] font-semibold text-blue-200 mb-1 leading-snug break-words [overflow-wrap:anywhere]">
                      {briefingTitle}
                    </div>
                  ) : null}
                  {skipperNotice ? (
                    <p data-testid="skipper-notice" className="text-[10px] font-semibold text-cyan-300 mb-1 leading-snug break-words [overflow-wrap:anywhere]">
                      {skipperNotice}
                    </p>
                  ) : null}
                  <p
                    data-testid="ici-briefing"
                    className="text-[11px] text-slate-300 leading-snug whitespace-pre-line break-words [overflow-wrap:anywhere] max-w-full"
                  >
                    {briefingLoading || (!briefing && !iciBriefing)
                      ? t("iciBriefingLoading")
                      : (iciBriefing && iciBriefingSegments?.length
                        ? <BriefingText segments={iciBriefingSegments} onFocus={onBriefingFocus} t={t} />
                        : (briefing || t("iciBriefingFallback")))}
                  </p>
                  <p
                    data-testid="story-source"
                    className="text-[9px] text-slate-500 leading-snug mt-1"
                  >
                    {storySourceLabel(storySource, t)}
                  </p>
                </div>
              </div>
            ) : null}
            story={isSuivre && !isDrawing ? (
              <div data-testid="expedition-story" data-replay={storyReplay ? "1" : "0"} className={`sim-box-story h-auto rounded-lg border p-2 min-w-0 ${storyReplay ? "border-sky-400/60 bg-sky-900/40" : "border-sky-500/25 bg-sky-950/30"}`}>
                <div className="text-[10px] font-semibold text-sky-200 leading-snug">
                  {t("storyTitle")}{storyReplay ? <span className="ml-1 text-[9px] font-normal text-sky-100/80">· {t("replayBadge")}</span> : null}
                </div>
                {(Array.isArray(story) ? story : []).map((paragraph, i) => {
                  const current = storyReplay && i === (story?.length || 0) - 1;
                  return (
                    <p
                      key={i}
                      data-testid="story-paragraph"
                      data-current={current ? "1" : "0"}
                      className={`text-[11px] leading-snug break-words [overflow-wrap:anywhere] mt-1 ${current ? "text-white font-medium border-l-2 border-sky-300 pl-1.5" : "text-slate-200"}`}
                    >
                      {paragraph}
                    </p>
                  );
                })}
              </div>
            ) : null}
            journal={isSuivre && !isDrawing ? (
              <JournalPanel journal={journal} loading={journalLoading} error={journalError} />
            ) : null}
            escale={!isDrawing && escaleStop ? {
              stop: escaleStop,
              fiche: escaleFiche,
              loading: escaleLoading,
              error: escaleError,
              onClose: onEscaleClose,
              onFocus: onBriefingFocus,
            } : null}
          />
        </div>
      </div>
    </>
  );
});
