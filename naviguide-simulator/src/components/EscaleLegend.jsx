import { memo, useMemo } from "react";
import { useLang } from "../i18n/LangContext.jsx";
import { formatCivilDate } from "../engine/voyageClock.js";

function markAt(m) {
  return Number(m.filmNm ?? m.nm) || 0;
}

/**
 * One escale row. Memoised: the HUD publishes `filmNm` up to 4×/s, and only the
 * `active` flag of two rows changes then — not the 18 formatted labels
 * (profile 18 sept. 2026: this list was 12 % of main-thread self time).
 */
const EscaleRow = memo(function EscaleRow({ name, at, nmLabel, dateLabel, quayLabel, title, sheetTitle, active, onSeek, onSheet }) {
  return (
    <li className={`flex items-stretch border-t border-white/5 ${active ? "bg-cyan-700/40 text-white" : "text-white/70 hover:bg-white/5 hover:text-white"}`}>
      <button
        type="button"
        onClick={() => onSeek?.(at, { jump: true })}
        title={title}
        className="flex-1 min-w-0 text-left px-2 py-1 text-[11px]"
      >
        <span className="font-medium leading-tight block truncate">{name}</span>
        <span className="text-[9px] text-white/40">
          {nmLabel}
          {dateLabel}
          {quayLabel}
        </span>
      </button>
      {onSheet ? (
        <button
          type="button"
          onClick={onSheet}
          title={sheetTitle}
          data-testid="escale-sheet-open"
          className="px-1.5 text-[10px] text-emerald-200/80 hover:text-emerald-100 hover:bg-emerald-900/40"
        >
          ▤
        </button>
      ) : null}
    </li>
  );
});

export const EscaleLegend = memo(function EscaleLegend({ marks, filmNm, onSeek, onSheet }) {
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
        title: t("escalesJump", { name: m.name }),
        sheetTitle: t("escaleSheetOpen", { name: m.name }),
        nmLabel: `${Math.round(Number(m.nm) || 0).toLocaleString()} nm`,
        dateLabel: m.iso ? ` · ${formatCivilDate(m.iso, lang)}` : "",
        quayLabel: m.holdHours > 0 ? ` · ${t("escalesQuay", { days: Math.round(m.holdHours / 24) })}` : "",
      };
    }), [marks, lang, t]);

  if (!rows.length) return null;
  const x = Number(filmNm) || 0;
  let current = 0;
  for (let i = 0; i < rows.length; i++) {
    if (rows[i].at <= x + 0.4) current = i;
  }

  return (
    <div className="rounded-lg border border-white/10 bg-slate-800/50 overflow-hidden">
      <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-200">
        {t("escalesList")}
      </div>
      <ul className="max-h-36 overflow-y-auto sidebar-scroll">
        {rows.map((r, i) => (
          <EscaleRow
            key={r.key}
            name={r.name}
            at={r.at}
            nmLabel={r.nmLabel}
            dateLabel={r.dateLabel}
            quayLabel={r.quayLabel}
            title={r.title}
            sheetTitle={r.sheetTitle}
            active={i === current}
            onSeek={onSeek}
            onSheet={onSheet && Number.isFinite(r.mark?.lat) && Number.isFinite(r.mark?.lon)
              ? () => onSheet({ name: r.name, lat: r.mark.lat, lon: r.mark.lon })
              : null}
          />
        ))}
      </ul>
    </div>
  );
});
