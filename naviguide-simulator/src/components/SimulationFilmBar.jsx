import { ChevronLeft, ChevronRight, Clapperboard, Pause, Play } from "lucide-react";
import { useLang } from "../i18n/LangContext.jsx";
import { clockTickLabels, formatSeaClock } from "../engine/seaTime.js";
import { FilmSpeedProfile } from "./FilmSpeedProfile.jsx";

const PROFILES = [
  { id: "real", labelKey: "speedReal" },
  { id: "read", labelKey: "speedRead" },
  { id: "normal", labelKey: "speedNormal" },
  { id: "fast", labelKey: "speedFast" },
];

export function SimulationFilmBar({
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
  onPrev,
  onNext,
  canPrev,
  canNext,
  cinema,
  onCinema,
  liveSpeed,
  windKind,
  boatName,
  phase,
  vehicle,
  clockScale = "nm",
  onClockScale,
  windSeries,
  windLoading,
  holding,
  clockLine = "",
  kindLabel = "",
  atQuay = false,
  quayDays = 0,
  twa = null,
  disclaimer = "",
  liveBadge = null,
  windModel = null,
}) {
  const { t } = useLang();
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
  const ticks = clockTickLabels({
    playheadTotal: barTotal,
    sailTotalNm: totalNm,
    knots: boatKnots,
    scale: clockScale,
  });

  const onBarClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const t0 = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    onSeekNm(t0 * barTotal);
  };

  const progressLabel = clockScale === "days"
    ? `${formatSeaClock(nm, boatKnots)} / ${formatSeaClock(totalNm, boatKnots)}`
    : `${Math.round(nm).toLocaleString()} / ${Math.round(totalNm).toLocaleString()} nm`;
  const remainLabel = remainingNm > 0.5 && !finished && vehicle !== "plane"
    ? (clockScale === "days"
      ? ` · ${t("nmRemaining")} ${formatSeaClock(remainingNm, boatKnots)}`
      : ` · ${t("nmRemaining")} ${Math.round(remainingNm).toLocaleString()} nm`)
    : "";

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-[2020] w-[min(920px,calc(100vw-24px))] pointer-events-auto">
      <div className="rounded-2xl border border-white/15 bg-slate-950/92 shadow-2xl px-3 pt-2 pb-2.5 text-white backdrop-blur-sm">
        <div className="flex items-start justify-between gap-3 mb-1.5">
          <div className="min-w-0">
            <div className="text-[13px] font-semibold leading-tight truncate">
              {finished
                ? t("filmArrived", { name: fromName || "—" })
                : (
                  <>
                    <span className="text-blue-200">{fromName || "—"}</span>
                    <span className="text-white/35 mx-1.5">→</span>
                    <span className="text-cyan-200">{toName || "—"}</span>
                  </>
                )}
            </div>
            {phaseLabel ? (
              <div className="text-[10px] text-cyan-300/80 mt-0.5 truncate">{phaseLabel}</div>
            ) : null}
            {disclaimer ? (
              <div className="text-[10px] text-amber-200/85 mt-0.5">{disclaimer}</div>
            ) : null}
            <div className="text-[10px] text-white/55 mt-0.5">
              {clockLine || progressLabel}
              {remainLabel}
              {etaHours != null && etaHours > 0 && !finished && vehicle !== "plane" ? ` · ${t("eta")} ${formatEta(etaHours)}` : ""}
              {vehicle === "plane"
                ? ` · ${t("filmAirVehicle")}`
                : ` · ${Number(boatKnots || 0).toFixed(1)} kt`}
              {twa != null && vehicle !== "plane" ? ` · ${t("voyageTwa", { deg: Math.round(twa) })}` : ""}
              {boatName && vehicle !== "plane" ? ` · ${boatName}` : ""}
              {profile === "real" && vehicle !== "plane" ? ` · ${t("speedRealHint")}` : ""}
              {kindLabel && vehicle !== "plane" ? ` · ${kindLabel}` : ""}
              {windKind === "forecast" && vehicle !== "plane" ? ` · ${t("filmWindForecast")}` : ""}
              {windModel && windKind === "forecast" ? ` · ${windModel}` : ""}
              {windKind === "analyse" && vehicle !== "plane" ? ` · ${t("filmWindAnalyse")}` : ""}
              {liveBadge ? ` · ${liveBadge}` : ""}
              {atQuay && quayDays > 0 ? ` · ${t("voyageAtQuay", { days: quayDays })}` : (holding ? ` · ${t("filmArrivalHold")}` : "")}
            </div>
          </div>
          <div className="flex flex-shrink-0 items-center gap-1">
            {onClockScale ? (
              <button
                type="button"
                onClick={() => onClockScale(clockScale === "nm" ? "days" : "nm")}
                className="px-2 py-1 rounded-lg text-[10px] font-semibold border bg-white/5 border-white/10 hover:bg-white/10"
                title={t("filmClockToggle")}
              >
                {clockScale === "days" ? t("filmClockDays") : t("filmClockNm")}
              </button>
            ) : null}
            <button
              type="button"
              onClick={onCinema}
              className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-semibold border ${
                cinema ? "bg-cyan-700/70 border-cyan-400/50" : "bg-white/5 border-white/10 hover:bg-white/10"
              }`}
              title={t("cinemaTooltip")}
            >
              <Clapperboard size={12} />
              {t("cinema")}
            </button>
          </div>
        </div>

        <button
          type="button"
          onClick={onBarClick}
          className="relative w-full h-3 rounded-full bg-white/10 block"
          title={t("filmScrub")}
        >
          <span className="absolute inset-y-0 left-0 rounded-full bg-cyan-400/80" style={{ width: `${pct}%` }} />
          {(marks || []).map((m) => (
            <span
              key={`${m.name}-${m.nm}`}
              className="absolute top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-white"
              style={{ left: `${barTotal > 0 ? ((m.filmNm ?? m.nm) / barTotal) * 100 : 0}%` }}
              title={m.name}
            />
          ))}
        </button>
        <div className="relative h-3.5 mb-1 text-[9px] text-white/50">
          {ticks.map((tick, i) => {
            const align = i === 0
              ? "left-0"
              : i === ticks.length - 1
                ? "right-0"
                : "-translate-x-1/2";
            const left = i === ticks.length - 1
              ? undefined
              : `${barTotal > 0 ? (tick.filmNm / barTotal) * 100 : 0}%`;
            return (
              <span
                key={`${tick.filmNm}-${tick.label}`}
                className={`absolute top-0 whitespace-nowrap ${align}`}
                style={left != null ? { left } : undefined}
              >
                {tick.label}
              </span>
            );
          })}
        </div>

        <FilmSpeedProfile
          series={windSeries}
          filmNm={barNm}
          playheadTotal={barTotal}
          onSeek={onSeekNm}
          loading={windLoading}
        />

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onPrev}
            disabled={!canPrev}
            className="w-8 h-8 rounded-lg bg-white/10 disabled:opacity-30 flex items-center justify-center"
            title={t("previousEscale")}
          >
            <ChevronLeft size={16} />
          </button>
          <button
            type="button"
            onClick={onTogglePlay}
            className="w-10 h-8 rounded-lg bg-cyan-600 hover:bg-cyan-500 flex items-center justify-center"
            title={playing ? t("pause") : t("play")}
          >
            {playing ? <Pause size={16} /> : <Play size={16} className="ml-0.5" />}
          </button>
          <button
            type="button"
            onClick={onNext}
            disabled={!canNext}
            className="w-8 h-8 rounded-lg bg-white/10 disabled:opacity-30 flex items-center justify-center"
            title={t("nextEscale")}
          >
            <ChevronRight size={16} />
          </button>

          <div className="flex flex-wrap gap-1 ml-1">
            {PROFILES.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => onProfile(p.id)}
                className={`px-2 py-1 rounded-md text-[10px] font-semibold border ${
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
        </div>
      </div>
    </div>
  );
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
