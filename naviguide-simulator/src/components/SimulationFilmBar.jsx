import { memo } from "react";
import { ChevronRight, Clapperboard, Pause, Play } from "lucide-react";
import { useLang } from "../i18n/LangContext.jsx";
import { filmBarInsets } from "../utils/filmBarLayout.js";
import { VIEW_SIMULATION, VIEW_SUIVRE } from "../constants/viewMode.js";
import { ListenButton } from "./ListenButton.jsx";

const PROFILES = [
  { id: "real", labelKey: "speedReal" },
  { id: "read", labelKey: "speedRead" },
  { id: "normal", labelKey: "speedNormal" },
  { id: "fast", labelKey: "speedFast" },
];

export const SimulationFilmBar = memo(function SimulationFilmBar({
  fromName,
  toName,
  finished,
  nm,
  totalNm,
  playhead,
  playheadTotal,
  remainingNm,
  etaHours,
  boatKnots,
  profile,
  onProfile,
  playing,
  onTogglePlay,
  marks,
  onSeekNm,
  onNext,
  canNext,
  showPlaybackControls = true,
  cinema,
  onCinema,
  hideBar = false,
  replay = null,
  onHideBar,
  liveSpeed,
  windKind,
  boatName,
  phase,
  vehicle,
  windSeries,
  windLoading,
  holding,
  clockLine = "",
  atQuay = false,
  quayDays = 0,
  twa = null,
  liveStatus = null,
  weatherLine = "",
  showSpeeds = false,
  showWindProfile = false,
  stopAuto = false,
  onStopAuto,
  showStopAuto = false,
  sidebarOpen = true,
  toolsOpen = true,
  gribLine = "",
  clock = null,
  clockCurrent = null,
  disclaimer = "",
  eventMarks = [],
  onEventClick,
  storiesPending = 0,
  speechText = null,
  view = null,
  onView,
}) {
  const { t, lang } = useLang();
  const insets = filmBarInsets({ sidebarOpen, toolsOpen });
  const barTotal = playheadTotal ?? totalNm;
  const barNm = playhead ?? nm;
  const pct = barTotal > 0 ? Math.min(100, (barNm / barTotal) * 100) : 0;
  const phaseLabel = phase === "air-out" || phase === "air"
    ? t("filmPhaseAir")
    : phase === "air-return"
      ? t("filmPhaseAirReturn")
      : phase === "side-sail"
        ? t("filmPhaseSide")
        : "";
  const onBarClick = (e) => {
    if (!showPlaybackControls) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const t0 = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    onSeekNm(t0 * barTotal);
  };

  if (hideBar) {
    return (
      <div
        className="absolute bottom-5 z-[2020] pointer-events-auto"
        style={{ left: insets.left, right: insets.right }}
      >
        <button
          type="button"
          onClick={() => onHideBar?.(false)}
          className="mx-auto block px-2 py-1 rounded-md text-[10px] font-semibold bg-slate-950/80 border border-white/15 text-white/80"
        >
          {t("showFilmBar")}
        </button>
      </div>
    );
  }

  return (
    <div
      data-testid="film-bar"
      className="absolute bottom-5 z-[2020] pointer-events-auto"
      style={{ left: insets.left, right: insets.right }}
    >
      <div className="naviguide-film-bar rounded-xl border border-white/15 bg-slate-950/92 shadow-2xl px-2.5 pt-1.5 pb-1.5 text-white backdrop-blur-sm">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0 text-[12px] font-semibold leading-tight truncate">
            {finished
              ? t("filmArrived", { name: fromName || "—" })
              : (
                <>
                  <span className="text-blue-200">{fromName || "—"}</span>
                  <span className="text-white/35 mx-1">→</span>
                  <span className="text-cyan-200">{toName || "—"}</span>
                </>
              )}
            {phaseLabel ? <span className="text-[10px] font-normal text-cyan-300/80 ml-2">{phaseLabel}</span> : null}
          </div>
          <div className="flex flex-shrink-0 items-center gap-1">
            {disclaimer ? (
              <span data-testid="nav-disclaimer" className="text-[9px] text-amber-100/80 leading-tight max-w-[9rem] text-right">
                {disclaimer}
              </span>
            ) : null}
            {speechText ? (
              <ListenButton text={speechText} t={t} lang={lang} className="px-2 py-0.5 !rounded-md" />
            ) : null}
            {cinema && onHideBar ? (
              <button
                type="button"
                onClick={() => onHideBar(true)}
                className="px-2 py-0.5 rounded-md text-[10px] font-semibold border bg-white/5 border-white/10 hover:bg-white/10"
              >
                {t("hideFilmBar")}
              </button>
            ) : null}
            <button
              type="button"
              onClick={onCinema}
              className={`flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold border ${
                cinema ? "bg-cyan-700/70 border-cyan-400/50" : "bg-white/5 border-white/10 hover:bg-white/10"
              }`}
              title={t("cinemaTooltip")}
            >
              <Clapperboard size={11} />
              {t("cinema")}
            </button>
          </div>
        </div>

        <div data-testid="film-clock-line" className="text-[11px] text-white/75 tabular-nums leading-tight mt-0.5 truncate">
          {clockLine || `${Math.round(nm).toLocaleString()} nm`}
          {remainingNm > 0.5 && !finished && vehicle !== "plane"
            ? ` · ${t("nmRemaining")} ${Math.round(remainingNm).toLocaleString()} nm`
            : ""}
          {etaHours != null && etaHours > 0 && !finished && vehicle !== "plane" ? ` · ${t("eta")} ${formatEta(etaHours)}` : ""}
          {vehicle === "plane" ? ` · ${t("filmAirVehicle")}` : ` · ${Number(boatKnots || 0).toFixed(1)} kt`}
          {twa != null && vehicle !== "plane" ? ` · ${t("voyageTwa", { deg: Math.round(twa) })}` : ""}
          {boatName && vehicle !== "plane" ? ` · ${boatName}` : ""}
          {liveStatus ? ` · ${liveStatus}` : ""}
          {atQuay && quayDays > 0 ? ` · ${t("voyageAtQuay", { days: quayDays })}` : (holding ? ` · ${t("filmArrivalHold")}` : "")}
          {weatherLine ? <span data-testid="weather-line" className="text-cyan-200/85"> · {weatherLine}</span> : null}
        </div>
        {gribLine ? (
          <div data-testid="grib-warning" className="text-[10px] text-amber-200/90 leading-tight">
            {gribLine}
          </div>
        ) : null}

        <div className="relative w-full h-2 rounded-full bg-white/10 mt-1">
          <button
            type="button"
            onClick={onBarClick}
            disabled={!showPlaybackControls}
            className="absolute inset-0 w-full h-full rounded-full"
            title={showPlaybackControls ? t("filmScrub") : undefined}
          >
            <span className="absolute inset-y-0 left-0 rounded-full bg-cyan-400/80" style={{ width: `${pct}%` }} />
          </button>
          {(marks || []).map((m) => (
            <span
              key={`${m.name}-${m.nm}`}
              className="absolute top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-white pointer-events-none"
              style={{ left: `${barTotal > 0 ? ((m.filmNm ?? m.nm) / barTotal) * 100 : 0}%` }}
              title={m.name}
            />
          ))}
          {(eventMarks || []).map((ev) => {
            const full = ev.judge === "now" || ev.story?.status === "ready";
            const left = barTotal > 0 ? ((ev.filmCum ?? 0) / barTotal) * 100 : 0;
            return (
              <button
                key={ev.id || ev.stableKey}
                type="button"
                data-testid={`event-pill-${ev.type}`}
                data-judge={ev.judge || ""}
                className={`absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full border z-10 ${
                  full
                    ? "bg-cyan-300 border-cyan-50"
                    : "bg-transparent border-cyan-200"
                }`}
                style={{ left: `${left}%` }}
                title={ev.phrase || ev.type}
                onClick={(e) => {
                  e.stopPropagation();
                  onEventClick?.(ev);
                }}
              />
            );
          })}
        </div>
        {storiesPending > 0 ? (
          <div data-testid="stories-pending" className="text-[10px] text-white/55 leading-tight mt-0.5">
            {t("storiesPending", { n: storiesPending })}
          </div>
        ) : null}

        {(showPlaybackControls || showStopAuto || showSpeeds || onView || replay) ? (
          <div className="flex items-center gap-1.5 mt-1">
            {showPlaybackControls ? (
              <>
                <button
                  type="button"
                  onClick={onTogglePlay}
                  className="w-9 h-7 rounded-md bg-cyan-600 hover:bg-cyan-500 flex items-center justify-center"
                  title={playing ? t("pause") : t("play")}
                >
                  {playing ? <Pause size={14} /> : <Play size={14} className="ml-0.5" />}
                </button>
                <button
                  type="button"
                  onClick={onNext}
                  disabled={!canNext}
                  className="h-7 px-2 rounded-md bg-white/10 disabled:opacity-30 flex items-center gap-1 text-[10px] font-semibold"
                  title={t("goToNextStop")}
                >
                  <ChevronRight size={14} />
                  {t("goToNextStop")}
                </button>
              </>
            ) : null}
          {showStopAuto ? (
            <button
              type="button"
              data-testid="stop-auto"
              role="switch"
              aria-checked={stopAuto}
              onClick={() => onStopAuto?.(!stopAuto)}
              className={`h-7 px-2 rounded-md text-[10px] font-semibold border ${
                stopAuto
                  ? "bg-amber-600/80 border-amber-300/50"
                  : "bg-white/5 border-white/10 text-white/70"
              }`}
              title={stopAuto ? t("stopAutoOn") : t("stopAutoOff")}
            >
              {t("stopAuto")}
            </button>
          ) : null}

          {showSpeeds ? (
            <div className="flex flex-wrap gap-1 ml-1">
              {PROFILES.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => onProfile(p.id)}
                  className={`px-2 py-0.5 rounded-md text-[10px] font-semibold border ${
                    profile === p.id
                      ? "bg-white text-slate-900 border-white"
                      : "bg-white/5 border-white/10 text-white/70 hover:text-white"
                  }`}
                  title={t(`${p.labelKey}Title`)}
                >
                  {t(p.labelKey)}
                </button>
              ))}
            </div>
          ) : null}
          {replay ? (
            <div className="flex items-center gap-1 ml-1" data-testid="replay-controls">
              {replay.active ? (
                <>
                  <button
                    type="button"
                    onClick={replay.onStop}
                    data-testid="replay-stop"
                    className="h-7 px-2 rounded-md text-[10px] font-semibold border bg-rose-700/70 border-rose-300/40 hover:bg-rose-600/70 whitespace-nowrap"
                    title={t("replayStopTitle")}
                  >
                    ■ {t("replayStop")}
                  </button>
                  <div className="w-20 h-1.5 rounded-full bg-white/10 overflow-hidden" title={t("replayProgress", { pct: Math.round((replay.progress || 0) * 100) })}>
                    <div className="h-full bg-sky-400" style={{ width: `${Math.round((replay.progress || 0) * 100)}%` }} />
                  </div>
                </>
              ) : (
                <button
                  type="button"
                  onClick={replay.onStart}
                  data-testid="replay-start"
                  className="h-7 px-2 rounded-md text-[10px] font-semibold border bg-sky-700/60 border-sky-300/40 hover:bg-sky-600/70 whitespace-nowrap"
                  title={t("replayStartTitle")}
                >
                  ↺ {t("replayStart")}
                </button>
              )}
              <button
                type="button"
                role="switch"
                aria-checked={Boolean(replay.voice)}
                onClick={() => replay.onVoice?.(!replay.voice)}
                data-testid="replay-voice"
                className={`h-7 px-2 rounded-md text-[10px] font-semibold border ${replay.voice ? "bg-sky-600/40 border-sky-400/40 text-sky-100" : "bg-white/5 border-white/10 text-white/70"}`}
                title={replay.voice ? t("replayVoiceOn") : t("replayVoiceOff")}
              >
                🔊
              </button>
            </div>
          ) : null}
          {onView ? (
            <div
              role="radiogroup"
              aria-label={t("viewModeGroup")}
              data-testid="film-view-switch"
              className="ml-auto flex bg-white/5 border border-white/10 rounded-md p-0.5 gap-0.5 flex-shrink-0"
            >
              {[[VIEW_SUIVRE, t("followExpeditionButton"), "view-suivre"], [VIEW_SIMULATION, t("simulationButton"), "view-simulation"]].map(([id, label, testId]) => (
                <button
                  key={id}
                  type="button"
                  role="radio"
                  aria-checked={view === id}
                  data-testid={testId}
                  onClick={() => onView(id)}
                  className={`px-2 py-0.5 rounded text-[10px] font-semibold whitespace-nowrap ${
                    view === id ? "bg-cyan-700/70 text-cyan-50 border border-cyan-400/50" : "text-white/70 hover:text-white border border-transparent"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
});

function formatEta(hours) {
  if (hours == null || Number.isNaN(hours)) return "—";
  if (hours < 1 / 60) return "0 min";
  if (hours < 1) return `${Math.round(hours * 60)} min`;
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (hours >= 48) return `${Math.round(hours / 24)} j`;
  if (m === 0) return `${h} h`;
  return `${h} h ${String(m).padStart(2, "0")}`;
}
