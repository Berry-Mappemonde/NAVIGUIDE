import { memo } from "react";
import { useLang } from "../i18n/LangContext.jsx";
import { formatEtaRange } from "../hooks/usePlanReview.js";

const LEVEL_DOT = {
  ok: "bg-emerald-400",
  info: "bg-slate-400",
  watch: "bg-amber-400",
  alert: "bg-rose-400",
  muted: "bg-slate-600",
};

const BADGE = {
  ok: "border-emerald-500/40 text-emerald-200",
  info: "border-white/10 text-white/70",
  watch: "border-amber-400/50 text-amber-200",
  alert: "border-rose-400/60 text-rose-200",
  muted: "border-white/10 text-white/40",
};

/** Libellé de source (clés i18n L1). Pas de nom de modèle en dur. */
function llmSourceLabel(source, t) {
  const s = String(source || "");
  if (s === "openrouter") return t("storySourceOpenrouter");
  if (s === "claude") return t("storySourceClaude");
  if (s === "rules") return t("storySourceRules");
  if (s === "budget") return t("storySourceBudget");
  if (s === "cache") return t("storySourceCache");
  if (s.endsWith("-lightning")) return t("storySourceLightning");
  if (s.endsWith("-super")) return t("storySourceSuper");
  if (s.endsWith("-ultra")) return t("storySourceUltra");
  return s || t("storySourceRules");
}

/**
 * « Revue du plan » (lot K): one row per leg — dates, badges (sea days, rest,
 * EEZ / Gold, MPA, gale season, cyclones), notes. Collapsed by default under
 * the Expedition box; every figure comes from the server review or the atlas.
 */
export const PlanReview = memo(function PlanReview({
  legs = [], loading = false, error = null, summary = null,
  comment = null, commentSource = null,
}) {
  const { t, lang } = useLang();
  const alerts = legs.filter((l) => l.level === "alert").length;
  const watches = legs.filter((l) => l.level === "watch").length;
  const source = commentSource || "rules";
  const sourceLabel = llmSourceLabel(source, t);
  return (
    <details className="rounded-lg border border-white/10 bg-slate-800/50 overflow-hidden group" data-testid="plan-review">
      <summary className="cursor-pointer select-none list-none px-2 py-1 flex items-center gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-200">{t("planReviewTitle")}</span>
        <span className="ml-auto text-[9px] text-white/50">
          {loading ? t("planReviewLoading") : error ? t("planReviewError") : (
            alerts ? `${alerts} ${t("planReviewAlerts")}` : watches ? `${watches} ${t("planReviewWatch")}` : t("planReviewOk")
          )}
        </span>
        <span className="text-white/40 text-[10px] transition-transform group-open:rotate-90">›</span>
      </summary>
      <div className="border-t border-white/5">
        {summary ? (
          <p className="px-2 pt-1 text-[9px] text-white/45 leading-snug">{summary}</p>
        ) : null}
        <ul className="max-h-64 overflow-y-auto sidebar-scroll">
          {legs.map((leg) => {
            const etaLabel = formatEtaRange(leg.etaRange, t, lang);
            return (
            <li key={leg.key} className="px-2 py-1.5 border-t border-white/5 first:border-t-0" data-level={leg.level} data-testid="plan-review-leg">
              <div className="flex items-baseline gap-1.5 min-w-0">
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${LEVEL_DOT[leg.level] || LEVEL_DOT.info}`} />
                <span className="text-[11px] font-medium text-white leading-tight truncate">{leg.title}</span>
                <span className="ml-auto text-[9px] text-white/40 shrink-0 tabular-nums" data-testid="plan-review-leg-dates">{leg.dates}</span>
              </div>
              {etaLabel ? (
                <p className="text-[9px] text-white/40 mt-0.5 pl-3" data-testid="plan-review-eta-range">{etaLabel}</p>
              ) : null}
              <div className="flex flex-wrap gap-1 mt-1">
                {leg.badges.map((b, i) => (
                  <span key={`${b.kind}-${i}`} className={`px-1.5 py-0.5 rounded-md border text-[9px] leading-tight ${BADGE[b.level] || BADGE.info}`}>{b.text}</span>
                ))}
              </div>
              {leg.notes.map((n, i) => (
                <p key={i} className="text-[10px] text-amber-100/80 leading-snug mt-1 break-words [overflow-wrap:anywhere]">{n}</p>
              ))}
            </li>
            );
          })}
          {!legs.length && !loading ? <li className="px-2 py-1.5 text-[10px] text-white/50">{t("planReviewEmpty")}</li> : null}
        </ul>
        <div
          data-testid="plan-review-comment"
          data-source={source}
          className="px-2 py-1.5 border-t border-white/10"
        >
          <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-300">{t("planReviewCommentTitle")}</p>
          {comment ? (
            <p className="text-[10px] text-white/80 leading-snug mt-1 break-words [overflow-wrap:anywhere]">{comment}</p>
          ) : null}
          <p className="text-[9px] text-white/40 mt-1">{sourceLabel}</p>
        </div>
      </div>
    </details>
  );
});
