import { memo } from "react";
import { ChevronRight, Clapperboard, Maximize2, Minimize2, Pause, Play } from "lucide-react";
import { useLang } from "../i18n/LangContext.jsx";
import { filmBarInsets } from "../utils/filmBarLayout.js";
import { VIEW_SIMULATION, VIEW_SUIVRE } from "../constants/viewMode.js";
import { REGIME_COLORS } from "../layers/regimeRoute.js";
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
  drawing = null,
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
  filmFullscreen = false,
  onFilmFullscreen,
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

  // Lot I — while drawing, the bar speaks of the drawn route (not the official leg);
  // no playback, no speeds, no Suivre / Simulation switch: drawing is its own mode.
  if (drawing) {
    return (
      <div
        data-testid="film-bar"
        data-drawing="1"
        className="absolute bottom-5 z-[2020] pointer-events-auto"
        style={{ left: insets.left, right: insets.right }}
      >
        <div className="naviguide-film-bar rounded-xl border border-emerald-400/30 bg-slate-950/92 shadow-2xl px-2.5 pt-1.5 pb-1.5 text-white backdrop-blur-sm">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0 text-[12px] font-semibold leading-tight truncate">
              <span className="text-emerald-200">{t("drawingInProgress")}</span>
              <span className="text-white/60 font-normal ml-2">{drawing.message}</span>
            </div>
            {disclaimer ? (
              <span data-testid="nav-disclaimer" className="text-[9px] text-amber-100/80 leading-tight max-w-[9rem] text-right">{disclaimer}</span>
            ) : null}
          </div>
          <div data-testid="film-clock-line" className="text-[11px] text-white/75 tabular-nums leading-tight mt-0.5 truncate">
            {drawing.points.length} {t("drawingPoints")} · {Number(drawing.distanceNm || 0).toLocaleString()} nm
            {drawing.failed ? ` · ${drawing.failed} ${t("drawingFailedSegments")}` : ""}
            {drawing.loading ? ` · ${t("drawingRouting")}` : ""}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="film-bar"
      className="absolute bottom-5 z-[2020] pointer-events-auto"
      style={{ left: insets.left, right: insets.right }}
    >
      <div className="naviguide-film-bar rounded-xl border border-white/15 bg-slate-950/92 shadow-2xl px-2.5 pt-1 pb-1 text-white backdrop-blur-sm">
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
          {disclaimer ? (
            <span data-testid="nav-disclaimer" className="text-[9px] text-amber-100/80 leading-tight max-w-[9rem] text-right flex-shrink-0">
              {disclaimer}
            </span>
          ) : null}
        </div>

        <div data-testid="film-clock-line" className="text-[11px] text-white/75 tabular-nums leading-tight mt-0.5 truncate">
          <span data-testid="clock-line">
            {clockLine || `${Math.round(nm).toLocaleString()} nm`}
            {remainingNm > 0.5 && !finished && vehicle !== "plane"
              ? ` · ${t("nmRemaining")} ${Math.round(remainingNm).toLocaleString()} nm`
              : ""}
            {etaHours != null && etaHours > 0 && !finished && vehicle !== "plane" ? ` · ${t("eta")} ${formatEta(etaHours)}` : ""}
            {vehicle === "plane"
              ? ` · ${t("filmAirVehicle")}`
              : atQuay
                ? ` · ${quayDays > 0 ? t("voyageAtQuay", { days: quayDays }) : t("filmAtQuay")}`
                : ` · ${Number(boatKnots || 0).toFixed(1)} kt`}
            {twa != null && vehicle !== "plane" ? ` · ${t("voyageTwa", { deg: Math.round(twa) })}` : ""}
            {boatName && vehicle !== "plane" ? ` · ${boatName}` : ""}
            {liveStatus ? ` · ${liveStatus}` : ""}
            {atQuay && quayDays > 0 ? "" : (holding ? ` · ${t("filmArrivalHold")}` : "")}
          </span>
          {clockRegimeText({
            regime: clockCurrent?.regime || clockCurrent?.kind,
            sources: clockCurrent?.sources,
            spread: clockCurrent?.spread,
            t,
            lang,
          }) ? (
            <span data-testid="clock-regime">
              {" · "}
              {clockRegimeText({
                regime: clockCurrent?.regime || clockCurrent?.kind,
                sources: clockCurrent?.sources,
                spread: clockCurrent?.spread,
                t,
                lang,
              })}
            </span>
          ) : null}
          {weatherLine ? <span data-testid="weather-line" className="text-cyan-200/85"> · {weatherLine}</span> : null}
        </div>
        <div
          data-testid="regime-legend"
          aria-label={t("regimeLegend")}
          className="flex items-center gap-2.5 text-[9px] text-white/65 mt-0.5 leading-tight"
        >
          {[["hindcast", "clockRegimeHindcast"], ["forecast", "clockRegimeForecast"], ["climatology", "clockRegimeClimatology"]].map(([id, key]) => (
            <span key={id} className="inline-flex items-center gap-1">
              <span
                className="inline-block w-2 h-2 rounded-[2px]"
                style={{ background: REGIME_COLORS[id] }}
                aria-hidden="true"
              />
              {t(key)}
            </span>
          ))}
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
        {replay?.active ? (
          <div data-testid="film-subtitle" className="text-[10px] text-sky-100/90 leading-tight mt-0.5 truncate">
            {replay.subtitle || ""}
          </div>
        ) : null}
        {storiesPending > 0 ? (
          <div data-testid="stories-pending" className="text-[10px] text-white/55 leading-tight mt-0.5">
            {t("storiesPending", { n: storiesPending })}
          </div>
        ) : null}

        <div data-testid="film-commands" className="flex items-center gap-1 mt-1 overflow-x-auto flex-nowrap">
          <div className="flex items-center gap-1 flex-nowrap shrink-0">
            {cinema && onHideBar ? (
              <button
                type="button"
                onClick={() => onHideBar(true)}
                className="h-6 px-1.5 rounded-md text-[9px] font-semibold border bg-white/5 border-white/10 hover:bg-white/10 whitespace-nowrap"
              >
                {t("hideFilmBar")}
              </button>
            ) : null}
            {onCinema ? (
              <button
                type="button"
                onClick={onCinema}
                className={`flex items-center gap-1 h-6 px-1.5 rounded-md text-[9px] font-semibold border whitespace-nowrap ${
                  cinema ? "bg-cyan-700/70 border-cyan-400/50" : "bg-white/5 border-white/10 hover:bg-white/10"
                }`}
                title={t("cinemaTooltip")}
              >
                <Clapperboard size={11} />
                {t("cinema")}
              </button>
            ) : null}
            {onFilmFullscreen ? (
              <button
                type="button"
                data-testid="film-fullscreen"
                onClick={() => onFilmFullscreen(!filmFullscreen)}
                aria-pressed={filmFullscreen}
                aria-label={filmFullscreen ? t("filmFullscreenExit") : t("filmFullscreen")}
                className={`flex items-center justify-center w-6 h-6 rounded-md border ${
                  filmFullscreen
                    ? "bg-sky-700/70 border-sky-300/40"
                    : "bg-white/5 border-white/10 hover:bg-white/10"
                }`}
                title={t("filmFullscreenTitle")}
              >
                {filmFullscreen ? <Minimize2 size={11} /> : <Maximize2 size={11} />}
              </button>
            ) : null}
            <ListenButton
              text={speechText}
              t={t}
              lang={lang}
              compact
              testId="listen"
              showWhenEmpty
              listening={replay ? Boolean(replay.voice) : undefined}
              onListening={replay?.onVoice}
              deferSpeak={Boolean(replay?.active)}
              className="!rounded-md whitespace-nowrap"
            />
            {replay ? (
              <>
                <span data-testid="film-source" className="text-[9px] text-white/60 leading-tight truncate max-w-[7rem]">
                  {t("filmStorySource", { source: filmSourceLabel(replay.source, t) })}
                </span>
                <div data-testid="film-style" className="flex bg-white/5 border border-white/10 rounded-md p-0.5 gap-0.5 flex-shrink-0">
                  {[["raw", "filmStoryRaw"], ["written", "filmStoryWritten"]].map(([id, key]) => (
                    <button
                      key={id}
                      type="button"
                      data-testid={`film-style-${id}`}
                      aria-pressed={(replay.style || "raw") === id}
                      disabled={Boolean(replay.active)}
                      onClick={() => replay.onStyle?.(id)}
                      className={`px-1 py-0.5 rounded text-[9px] font-semibold whitespace-nowrap ${
                        (replay.style || "raw") === id
                          ? "bg-sky-700/70 text-sky-50 border border-sky-300/40"
                          : "text-white/70 hover:text-white border border-transparent"
                      }`}
                    >
                      {t(key)}
                    </button>
                  ))}
                </div>
              </>
            ) : null}
            {onView ? (
              <div
                role="radiogroup"
                aria-label={t("viewModeGroup")}
                data-testid="film-view-switch"
                className="flex bg-white/5 border border-white/10 rounded-md p-0.5 gap-0.5 flex-shrink-0"
              >
                {[[VIEW_SUIVRE, t("followExpeditionButton"), "view-suivre", "mode-follow"], [VIEW_SIMULATION, t("simulationButton"), "view-simulation", "mode-sim"]].map(([id, label, testId, alias]) => (
                  <button
                    key={id}
                    type="button"
                    role="radio"
                    aria-checked={view === id}
                    data-testid={testId}
                    data-mode={alias}
                    onClick={() => onView(id)}
                    className={`px-1.5 py-0.5 rounded text-[9px] font-semibold whitespace-nowrap ${
                      view === id ? "bg-cyan-700/70 text-cyan-50 border border-cyan-400/50" : "text-white/70 hover:text-white border border-transparent"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            ) : null}
            {replay ? (
              <div className="flex items-center gap-1" data-testid="replay-controls">
                {replay.active ? (
                  <>
                    <button
                      type="button"
                      onClick={replay.onStop}
                      data-testid="replay-stop"
                      className="h-6 px-1.5 rounded-md text-[9px] font-semibold border bg-rose-700/70 border-rose-300/40 hover:bg-rose-600/70 whitespace-nowrap"
                      title={t("replayStopTitle")}
                    >
                      ■ {t("replayStop")}
                    </button>
                    <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden" title={t("replayProgress", { pct: Math.round((replay.progress || 0) * 100) })}>
                      <div className="h-full bg-sky-400" style={{ width: `${Math.round((replay.progress || 0) * 100)}%` }} />
                    </div>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={replay.onStart}
                    data-testid="replay-start"
                    className="h-6 px-1.5 rounded-md text-[9px] font-semibold border bg-sky-700/60 border-sky-300/40 hover:bg-sky-600/70 whitespace-nowrap"
                    title={t("replayStartTitle")}
                  >
                    ↺ {t("replayStart")}
                  </button>
                )}
                <div
                  data-testid="film-duration"
                  className="flex bg-white/5 border border-white/10 rounded-md p-0.5 gap-0.5"
                  title={t("filmDuration")}
                >
                  {[[150, "filmDuration150"], [180, "filmDuration180"]].map(([sec, key]) => (
                    <button
                      key={sec}
                      type="button"
                      data-seconds={sec}
                      aria-pressed={Number(replay.targetSeconds) === sec}
                      disabled={Boolean(replay.active)}
                      onClick={() => replay.onDuration?.(sec)}
                      className={`px-1 py-0.5 rounded text-[9px] font-semibold whitespace-nowrap ${
                        Number(replay.targetSeconds) === sec
                          ? "bg-sky-700/70 text-sky-50 border border-sky-300/40"
                          : "text-white/70 hover:text-white border border-transparent"
                      }`}
                    >
                      {t(key)}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
          <div className="flex items-center gap-1 ml-auto flex-nowrap shrink-0">
            {showPlaybackControls ? (
              <>
                <button
                  type="button"
                  onClick={onTogglePlay}
                  className="w-7 h-6 rounded-md bg-cyan-600 hover:bg-cyan-500 flex items-center justify-center"
                  title={playing ? t("pause") : t("play")}
                >
                  {playing ? <Pause size={12} /> : <Play size={12} className="ml-0.5" />}
                </button>
                <button
                  type="button"
                  onClick={onNext}
                  disabled={!canNext}
                  className="h-6 px-1.5 rounded-md bg-white/10 disabled:opacity-30 flex items-center gap-0.5 text-[9px] font-semibold whitespace-nowrap"
                  title={t("goToNextStop")}
                >
                  <ChevronRight size={12} />
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
                className={`h-6 px-1.5 rounded-md text-[9px] font-semibold border whitespace-nowrap ${
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
              <div className="flex flex-nowrap gap-0.5">
                {PROFILES.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => onProfile(p.id)}
                    className={`px-1.5 py-0.5 rounded-md text-[9px] font-semibold border whitespace-nowrap ${
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
          </div>
        </div>
      </div>
    </div>
  );
});

const FILM_SOURCE_I18N = Object.freeze({
  "nemotron-lightning": "storySourceLightning",
  "nemotron-super": "storySourceSuper",
  "nemotron-ultra": "storySourceUltra",
  nemotron: "storySourceSuper",
  openrouter: "storySourceOpenrouter",
  claude: "storySourceClaude",
  rules: "storySourceRules",
  budget: "storySourceBudget",
  cache: "storySourceCache",
});

function filmSourceLabel(source, t) {
  return t(FILM_SOURCE_I18N[source] || "storySourceRules");
}

function clockRegimeText({ regime, sources, spread, t, lang = "fr" }) {
  const name = regime === "hindcast"
    ? t("clockRegimeHindcast")
    : regime === "forecast"
      ? t("clockRegimeForecast")
      : regime === "climatology"
        ? t("clockRegimeClimatology")
        : "";
  if (!name) return "";
  const n = Array.isArray(sources) ? sources.length : 0;
  const loc = lang === "en" ? "en-US" : "fr-FR";
  if (n > 0 && Number.isFinite(Number(spread))) {
    const sp = Number(spread).toLocaleString(loc, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    return `${name} · ${t("clockRegimeSources", { n, spread: sp })}`;
  }
  if (n > 0) return `${name} · ${t("clockRegimeSourcesPlain", { n })}`;
  return name;
}

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
