import { memo, useMemo } from "react";
import { useLang } from "../i18n/LangContext.jsx";
import { formatCivilDate } from "../engine/voyageClock.js";
import { formatEtaRange, formatEtaRangeTitle, nextStopFromMarks, nextStopRowIndex, useOfficialEta } from "../hooks/usePlanReview.js";

function markAt(m) {
  return Number(m.filmNm ?? m.nm) || 0;
}

/**
 * One escale row. Memoised: the HUD publishes `filmNm` up to 4×/s, and only the
 * `active` flag of two rows changes then — not the 18 formatted labels
 * (profile 18 sept. 2026: this list was 12 % of main-thread self time).
 */
function EscaleRowBody({ name, nmLabel, dateLabel, quayLabel, etaLabel, etaTitle }) {
  return (
    <>
      <span className="font-medium leading-tight block truncate">{name}</span>
      <span className="text-[9px] text-white/40">
        {nmLabel}
        {dateLabel}
        {quayLabel}
      </span>
      {etaLabel ? (
        <span className="text-[9px] text-white/40 block leading-tight" data-testid="eta-range" title={etaTitle || undefined}>{etaLabel}</span>
      ) : null}
    </>
  );
}

const EscaleRow = memo(function EscaleRow({ name, nmLabel, dateLabel, quayLabel, etaLabel, etaTitle, active }) {
  const idle = active ? "bg-cyan-700/40 text-white" : "text-white/70";
  return (
    <li
      data-testid="escale-legend-row"
      data-escale={name}
      data-interactive="false"
      className={`flex items-stretch border-t border-white/5 ${idle}`}
    >
      <div className="flex-1 min-w-0 text-left px-2 py-1 text-[11px] cursor-default">
        <EscaleRowBody
          name={name}
          nmLabel={nmLabel}
          dateLabel={dateLabel}
          quayLabel={quayLabel}
          etaLabel={etaLabel}
          etaTitle={etaTitle}
        />
      </div>
    </li>
  );
});

export const EscaleLegend = memo(function EscaleLegend({ marks, filmNm, frozen = false }) {
  const { t, lang } = useLang();

  // Labels depend on marks + language only: built once per route / language.
  const rows = useMemo(() => (marks || [])
    .filter((m) => m?.name)
    .map((m) => {
      const at = markAt(m);
      return {
        key: `${m.name}-${at}`,
        name: m.name,
        at,
        mark: m,
        nmLabel: `${Math.round(Number(m.nm) || 0).toLocaleString()} nm`,
        dateLabel: m.iso ? ` · ${formatCivilDate(m.iso, lang)}` : "",
        quayLabel: m.holdHours > 0 ? ` · ${t("escalesQuay", { days: Math.round(m.holdHours / 24) })}` : "",
      };
    }), [marks, lang, t]);

  const x = Number(filmNm) || 0;
  let current = 0;
  for (let i = 0; i < rows.length; i++) {
    if (rows[i].at <= x + 0.4) current = i;
  }
  const nowMs = Date.now();
  const nextName = nextStopFromMarks(marks, nowMs);
  const nextIndex = nextStopRowIndex(rows, marks, nowMs);
  const eta = useOfficialEta(nextName, { enabled: Boolean(nextName), frozen });
  const etaLabel = formatEtaRange(eta, t, lang);
  const etaTitle = formatEtaRangeTitle(eta, t);

  if (!rows.length) return null;

  return (
    <div className="rounded-lg border border-white/10 bg-slate-800/50 overflow-hidden" data-testid="escale-legend">
      <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-200">
        {t("escalesList")}
      </div>
      <ul className="max-h-36 overflow-y-auto sidebar-scroll">
        {rows.map((r, i) => (
          <EscaleRow
            key={r.key}
            name={r.name}
            nmLabel={r.nmLabel}
            dateLabel={r.dateLabel}
            quayLabel={r.quayLabel}
            etaLabel={etaLabel && i === nextIndex ? etaLabel : ""}
            etaTitle={etaLabel && i === nextIndex ? etaTitle : ""}
            active={i === current}
          />
        ))}
      </ul>
    </div>
  );
});
