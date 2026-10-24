/**
 * EtapePanel — leg metrics (nm, ETA, heading).
 *
 * Purely geometric calculation from useLegContext.
 * No API call — data available instantly on drag.
 *
 * Props:
 *   legContext   — LegContext object from the useLegContext hook
 *   onAdvance    — callback to advance to the midpoint of the next segment
 *   canAdvance   — boolean, disables the button at the end of the route
 */

import { Navigation, Clock, Compass, Map as MapIcon } from "lucide-react";
import { useLang } from "../i18n/LangContext.jsx";
import { getCardinalDirection, numberLocale } from "../utils/getCardinalDirection.js";
import { destinationPortLabel, displayStopName } from "../utils/stopLabels.js";

// ── Formatting ────────────────────────────────────────────────────────────────

function formatEta(hours, lang = "fr") {
  if (hours == null || Number.isNaN(hours)) return "—";
  if (hours < 1 / 60) return "0 min";
  if (hours < 1) return `${Math.round(hours * 60)} min`;
  if (hours >= 48) return `${Math.round(hours / 24)} ${lang === "en" ? "d" : "j"}`;
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (m === 0) return `${h} h`;
  return `${h} h ${String(m).padStart(2, "0")}`;
}

function formatNm(nm, lang = "fr") {
  if (nm == null) return "—";
  return `${nm.toLocaleString(numberLocale(lang))} nm`;
}

function formatBearing(deg, lang = "fr") {
  if (deg == null) return "—";
  return `${Math.round(deg)}° ${getCardinalDirection(deg, lang)}`;
}

// ── Main component ──────────────────────────────────────────────────────

export function EtapePanel({
  legContext,
  clockSample = null,
  kindLabel = "",
  atQuay = false,
  quayDays = 0,
  liveFollow = false,
  previewing = false,
  forecastStatus = null,
  onRecompute,
  canRecompute = false,
  showRecompute = false,
  recomputeBusy = false,
  onGoLive,
}) {
  const { t, lang } = useLang();

  if (!legContext) {
    return (
      <div className="bg-surface-raised/60 rounded-lg p-2 border border-line-hairline">
        <div className="text-[12px] text-text-muted text-center">
          {t("tracerDragPrompt")}
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

  const fromLabel = displayStopName(fromStop, lang, t);
  const toLabel = displayStopName(toStop, lang, t);

  return (
    <div className="bg-surface-raised/70 rounded-lg border border-line-hairline overflow-hidden">

      <div className="flex items-center justify-between px-2 py-1.5 border-b border-line-hairline/60">
        <div className="flex items-center gap-1 min-w-0 flex-wrap">
          <Navigation size={10} className="text-accent-text flex-shrink-0" />
          <span className="font-serif text-[15px] font-semibold text-text-primary leading-tight">
            {finished ? t("filmArrived", { name: fromLabel }) : fromLabel}
          </span>
          {!finished && (
            <>
              <span className="text-text-muted text-[13px]">→</span>
              <span className="font-serif text-[15px] font-semibold text-text-primary leading-tight">
                {toLabel}
              </span>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-px bg-line-hairline/60">

        <div className="bg-surface-raised/60 px-2 py-1 flex flex-col">
          <div className="flex items-center gap-1">
            <MapIcon size={9} className="text-text-muted" />
            <span className="text-[12px] text-text-muted">
              {t("nmRemaining")}
            </span>
          </div>
          <span data-testid="nm-to-destination-port" className="text-xs font-bold text-text-primary leading-tight">{destinationPortLabel(nmRemainingToStop, t, lang)}</span>
        </div>

        <div className="bg-surface-raised/60 px-2 py-1 flex flex-col">
          <div className="flex items-center gap-1">
            <Clock size={9} className="text-text-muted" />
            <span className="text-[12px] text-text-muted">
              {t("eta")}
            </span>
          </div>
          <span className="text-xs font-bold text-text-primary leading-tight">{formatEta(etaHours, lang)}</span>
          <span className="text-[12px] text-text-muted leading-tight">
            {clockSample?.vehicle === "plane"
              ? t("filmAirVehicle")
              : clockSample?.speedKnots != null
                ? t("voyageLocalKnots", { knots: Number(clockSample.speedKnots).toFixed(1) })
                : speedKnots != null
                  ? t("voyageLocalKnots", { knots: speedKnots })
                  : "—"}
          </span>
        </div>

        <div className="bg-surface-raised/60 px-2 py-1 flex flex-col">
          <div className="flex items-center gap-1">
            <Navigation size={9} className="text-text-muted" />
            <span className="text-[12px] text-text-muted">
              {t("nmCovered")}
            </span>
          </div>
          <span className="text-xs font-bold text-text-primary leading-tight">{formatNm(nmCovered, lang)}</span>
        </div>

        <div className="bg-surface-raised/60 px-2 py-1 flex flex-col">
          <div className="flex items-center gap-1">
            <Compass size={9} className="text-text-muted" />
            <span className="text-[12px] text-text-muted">
              {t("bearing")}
            </span>
          </div>
          <span className="text-xs font-bold text-text-primary leading-tight">{formatBearing(bearing, lang)}</span>
        </div>

      </div>

      {(kindLabel || clockSample?.twa != null || atQuay) && (
        <div className="px-2 py-1 text-[12px] text-text-primary/90 border-t border-line-hairline/60 space-y-0 leading-tight">
          <div className="flex flex-wrap gap-x-2 text-text-muted">
            {kindLabel ? <span>{kindLabel}</span> : null}
            {clockSample?.twa != null && clockSample?.vehicle !== "plane" ? (
              <span>{t("voyageTwa", { deg: Math.round(clockSample.twa) })}</span>
            ) : null}
          </div>
          {atQuay && quayDays > 0 ? (
            <div className="text-status-caution font-semibold">
              {t("voyageAtQuay", { days: quayDays })}
            </div>
          ) : null}
        </div>
      )}

      {liveFollow && (clockSample?.status === "waiting" || (previewing && onGoLive)) && (
        <div className="px-2 py-1 border-t border-line-hairline/60 flex items-center justify-between gap-2">
          {clockSample?.status === "waiting" && clockSample.countdownHours != null ? (
            <span className="text-[12px] text-status-caution">
              {t("departsIn", { hours: formatEta(clockSample.countdownHours, lang) })}
            </span>
          ) : null}
          {previewing && onGoLive ? (
            <button
              type="button"
              onClick={onGoLive}
              className="text-[12px] font-semibold text-accent-text hover:text-text-primary"
              title="L"
            >
              {t("returnToLive")}
            </button>
          ) : null}
        </div>
      )}

      {forecastStatus === "pending" && (
        <div className="px-2 py-1 text-[12px] text-accent-text bg-accent-soft/40">{t("forecastPending")}</div>
      )}
      {forecastStatus === "unavailable" && (
        <div className="px-2 py-1 text-[12px] text-status-caution bg-status-caution/5">{t("forecastUnavailable")}</div>
      )}

      {showRecompute && (
        <div className="px-1.5 pb-1.5">
          <button
            type="button"
            data-testid="ask-advice"
            disabled={!canRecompute || recomputeBusy || forecastStatus === "pending"}
            onClick={onRecompute}
            className="w-full rounded-md border border-accent-line/40 bg-accent-soft py-1 text-[12px] font-semibold text-accent-text hover:bg-accent-fill/20 disabled:opacity-40"
          >
            {recomputeBusy ? t("recomputeBusy") : t("recomputeButton")}
          </button>
        </div>
      )}

    </div>
  );
}
