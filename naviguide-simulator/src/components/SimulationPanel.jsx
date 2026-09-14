/**
 * SimulationPanel — Affiche les métriques de progression du catamaran
 *
 * Calcul purement géométrique depuis useLegContext.
 * Aucun appel API — données disponibles instantanément au drag.
 *
 * Props:
 *   legContext   — objet LegContext depuis useLegContext hook
 *   onClose      — callback pour désactiver le mode simulation
 *   onAdvance    — callback pour avancer au milieu du prochain segment
 *   canAdvance   — boolean, désactive le bouton si fin de route atteinte
 */

import { Navigation, Clock, Compass, Map as MapIcon, X, ChevronLeft, ChevronRight } from "lucide-react";
import { useLang } from "../i18n/LangContext.jsx";

// ── Formatage ────────────────────────────────────────────────────────────────

function formatEta(hours) {
  if (hours == null || Number.isNaN(hours)) return "—";
  if (hours < 1 / 60) return "0 min";
  if (hours < 1) return `${Math.round(hours * 60)} min`;
  if (hours >= 48) return `${Math.round(hours / 24)} j`;
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (m === 0) return `${h} h`;
  return `${h} h ${String(m).padStart(2, "0")}`;
}

function formatNm(nm) {
  if (nm == null) return "—";
  return `${nm.toLocaleString()} nm`;
}

function formatBearing(deg) {
  if (deg == null) return "—";
  const dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSO","SO","OSO","O","ONO","NO","NNO"];
  const idx = Math.round(deg / 22.5) % 16;
  return `${Math.round(deg)}° ${dirs[idx]}`;
}

// ── Boutons Précédent / Suivant ──────────────────────────────────────────────

function PrevNextButtons({ onPrev, canPrev, onNext, canNext }) {
  const { t } = useLang();
  const btnBase = "flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-semibold transition-all duration-150 select-none border";
  const btnActive = "text-white cursor-pointer";
  const btnDisabled = "bg-slate-700/30 text-white/25 border-white/5 cursor-not-allowed";
  return (
    <div className="px-2 pb-2 pt-1 flex gap-1.5">
      <button
        onClick={onPrev}
        disabled={!canPrev}
        className={[btnBase, canPrev ? `${btnActive} bg-slate-700/60 border-slate-500/50 hover:bg-slate-600/70` : btnDisabled].join(" ")}
        title={t("previousEscale")}
      >
        <ChevronLeft size={10} />
        <span>{t("previous")}</span>
      </button>
      <button
        onClick={onNext}
        disabled={!canNext}
        className={[btnBase, canNext ? `${btnActive} bg-cyan-700/60 border-cyan-500/50 hover:bg-cyan-600/70` : btnDisabled].join(" ")}
        title={t("nextEscale")}
      >
        <span>{t("next")}</span>
        <ChevronRight size={10} />
      </button>
    </div>
  );
}

// ── Composant principal ──────────────────────────────────────────────────────

export function SimulationPanel({
  legContext,
  onClose,
  onPrev,
  canPrev,
  onNext,
  canNext,
  clockSample = null,
  civilDate = "",
  kindLabel = "",
  atQuay = false,
  quayDays = 0,
  follow = false,
  previewing = false,
  forecastStatus = null,
  forecastModel = null,
  onRecompute,
  canRecompute = false,
  recomputeBusy = false,
  onGoLive,
  virtualBoat = false,
}) {
  const { t } = useLang();

  if (!legContext) {
    return (
      <div className="bg-slate-800/60 rounded-xl p-3 border border-blue-700/30">
        <div className="text-xs text-slate-400 text-center">
          {t("simulationDragPrompt")}
        </div>
        {/* Boutons nav visibles même sans legContext (départ de la route affichée) */}
        <div className="mt-2">
          <PrevNextButtons onPrev={onPrev} canPrev={canPrev} onNext={onNext} canNext={canNext} />
        </div>
      </div>
    );
  }

  const {
    fromStop, toStop,
    nmCovered, nmRemainingToStop,
    etaHours, bearing, speedKnots,
    finished,
  } = legContext;

  return (
    <div className="bg-slate-800/70 rounded-xl border border-blue-600/30 overflow-hidden">

      {/* Header tronçon actif */}
      <div className="flex items-center justify-between px-3 py-2 bg-blue-900/30 border-b border-blue-700/20">
        <div className="flex items-center gap-1.5 min-w-0 flex-wrap">
          <Navigation size={11} className="text-blue-400 flex-shrink-0" />
          <span className="text-[10px] font-semibold text-blue-300 leading-tight">
            {finished ? t("filmArrived", { name: fromStop }) : fromStop}
          </span>
          {!finished && (
            <>
              <span className="text-white/30 text-[10px]">→</span>
              <span className="text-[10px] font-semibold text-cyan-300 leading-tight">
                {toStop}
              </span>
            </>
          )}
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-white/30 hover:text-white/70 transition-colors flex-shrink-0 ml-1"
            title={t("exitSimulation")}
          >
            <X size={12} />
          </button>
        )}
      </div>

      {/* Grille métriques */}
      <div className="grid grid-cols-2 gap-px bg-slate-700/20 p-0.5">

        {/* NM restants */}
        <div className="bg-slate-800/60 rounded-lg p-2.5 flex flex-col gap-0.5">
          <div className="flex items-center gap-1">
            <MapIcon size={10} className="text-cyan-400" />
            <span className="text-[9px] text-slate-400 uppercase tracking-wider">
              {t("nmRemaining")}
            </span>
          </div>
          <span className="text-sm font-bold text-white">{formatNm(nmRemainingToStop)}</span>
        </div>

        {/* ETA */}
        <div className="bg-slate-800/60 rounded-lg p-2.5 flex flex-col gap-0.5">
          <div className="flex items-center gap-1">
            <Clock size={10} className="text-amber-400" />
            <span className="text-[9px] text-slate-400 uppercase tracking-wider">
              {t("eta")}
            </span>
          </div>
          <span className="text-sm font-bold text-white">{formatEta(etaHours)}</span>
          <span className="text-[9px] text-slate-500">
            {clockSample?.vehicle === "plane"
              ? t("filmAirVehicle")
              : clockSample?.speedKnots != null
                ? t("voyageLocalKnots", { knots: Number(clockSample.speedKnots).toFixed(1) })
                : speedKnots != null
                  ? t("voyageLocalKnots", { knots: speedKnots })
                  : "—"}
          </span>
        </div>

        {/* NM parcourus */}
        <div className="bg-slate-800/60 rounded-lg p-2.5 flex flex-col gap-0.5">
          <div className="flex items-center gap-1">
            <Navigation size={10} className="text-green-400" />
            <span className="text-[9px] text-slate-400 uppercase tracking-wider">
              {t("nmCovered")}
            </span>
          </div>
          <span className="text-sm font-bold text-white">{formatNm(nmCovered)}</span>
        </div>

        {/* Cap */}
        <div className="bg-slate-800/60 rounded-lg p-2.5 flex flex-col gap-0.5">
          <div className="flex items-center gap-1">
            <Compass size={10} className="text-purple-400" />
            <span className="text-[9px] text-slate-400 uppercase tracking-wider">
              {t("bearing")}
            </span>
          </div>
          <span className="text-sm font-bold text-white">{formatBearing(bearing)}</span>
        </div>

      </div>

      {(civilDate || kindLabel || clockSample?.twa != null || atQuay) && (
        <div className="px-3 py-1.5 text-[10px] text-sky-100/90 border-t border-white/5 space-y-0.5">
          {civilDate ? <div>{civilDate}</div> : null}
          <div className="flex flex-wrap gap-x-2 text-white/55">
            {kindLabel ? <span>{kindLabel}</span> : null}
            {clockSample?.twa != null && clockSample?.vehicle !== "plane" ? (
              <span>{t("voyageTwa", { deg: Math.round(clockSample.twa) })}</span>
            ) : null}
          </div>
          {atQuay && quayDays > 0 ? (
            <div className="text-amber-200 font-semibold uppercase tracking-wide">
              {t("voyageAtQuay", { days: quayDays })}
            </div>
          ) : null}
          {clockSample?.kind === "forecast" && (clockSample.model || forecastModel) ? (
            <div className="text-cyan-200/80">
              {clockSample.model || forecastModel}
              {clockSample.leadHours != null ? ` · +${Math.round(clockSample.leadHours)} h` : ""}
            </div>
          ) : null}
        </div>
      )}

      {follow && (
        <div className="px-3 py-1.5 border-t border-white/5 flex items-center justify-between gap-2">
          <span className={`text-[9px] font-bold tracking-wider px-1.5 py-0.5 rounded ${
            previewing ? "bg-slate-600/40 text-slate-300" : "bg-emerald-500/20 text-emerald-300"
          }`}
          >
            {previewing ? t("previewBadge") : "LIVE"}
          </span>
          {clockSample?.status === "waiting" && clockSample.countdownHours != null ? (
            <span className="text-[9px] text-amber-200/90">
              {t("departsIn", { hours: formatEta(clockSample.countdownHours) })}
            </span>
          ) : null}
          {previewing && onGoLive ? (
            <button
              type="button"
              onClick={onGoLive}
              className="text-[9px] font-semibold text-cyan-200 hover:text-cyan-100"
              title="L"
            >
              {t("returnToLive")}
            </button>
          ) : null}
        </div>
      )}

      {forecastStatus === "pending" && (
        <div className="px-3 py-1.5 text-[9px] text-sky-200/80 bg-sky-950/40">{t("forecastPending")}</div>
      )}
      {forecastStatus === "unavailable" && (
        <div className="px-3 py-1.5 text-[9px] text-amber-200/80 bg-amber-950/30">{t("forecastUnavailable")}</div>
      )}

      {canRecompute && (
        <div className="px-2 pb-2">
          <button
            type="button"
            disabled={recomputeBusy || forecastStatus === "pending"}
            onClick={onRecompute}
            className="w-full rounded-lg border border-cyan-500/40 bg-cyan-900/30 py-1.5 text-[10px] font-semibold text-cyan-100 hover:bg-cyan-800/40 disabled:opacity-40"
          >
            {recomputeBusy ? t("recomputeBusy") : t("recomputeButton")}
          </button>
        </div>
      )}

      {(virtualBoat || follow) && (
        <p className="px-3 pb-2 text-[9px] text-white/40 leading-snug">{t("voyageForecastDisclaimer")}</p>
      )}

      {/* Boutons Précédent / Suivant */}
      <PrevNextButtons onPrev={onPrev} canPrev={canPrev} onNext={onNext} canNext={canNext} />

    </div>
  );
}
