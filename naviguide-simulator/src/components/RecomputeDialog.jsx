import { useLang } from "../i18n/LangContext.jsx";

function hoursLabel(h) {
  if (h == null || Number.isNaN(h)) return "—";
  if (h >= 48) return `${Math.round(h / 24)} j`;
  return `${Math.round(h * 10) / 10} h`;
}

export function RecomputeDialog({ draft, busy, onAccept, onReject }) {
  const { t } = useLang();
  if (!draft) return null;
  const vs = draft.versus_searoute || {};
  return (
    <div className="fixed inset-0 z-[2400] flex items-center justify-center bg-slate-950/70 px-4">
      <div className="w-full max-w-md rounded-2xl border border-white/15 bg-slate-900 p-4 text-white shadow-2xl">
        <div className="text-sm font-semibold mb-1">{t("recomputeTitle")}</div>
        <p className="text-[11px] text-white/60 mb-3">
          {t("recomputeTo", { name: draft.to_name || "—" })} · {draft.status}
        </p>
        <div className="grid grid-cols-2 gap-2 text-[11px] mb-3">
          <div className="rounded-lg bg-slate-800/80 p-2">
            <div className="text-white/40 uppercase text-[9px]">{t("recomputeSearoute")}</div>
            <div>{vs.distance_nm ?? "—"} nm</div>
            <div>{hoursLabel(vs.hours)}</div>
          </div>
          <div className="rounded-lg bg-cyan-950/50 p-2 border border-cyan-500/30">
            <div className="text-cyan-300/70 uppercase text-[9px]">{t("recomputeProposed")}</div>
            <div>{draft.distance_nm ?? "—"} nm</div>
            <div>{hoursLabel(draft.hours)}</div>
          </div>
        </div>
        <p className="text-[10px] text-white/45 mb-3">{t("recomputeHint")}</p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onReject}
            disabled={busy}
            className="flex-1 rounded-lg border border-white/15 py-1.5 text-[11px] font-semibold hover:bg-white/5"
          >
            {t("recomputeKeep")}
          </button>
          <button
            type="button"
            onClick={onAccept}
            disabled={busy || draft.status === "failed"}
            className="flex-1 rounded-lg bg-cyan-600 py-1.5 text-[11px] font-semibold hover:bg-cyan-500 disabled:opacity-40"
          >
            {t("recomputeAccept")}
          </button>
        </div>
      </div>
    </div>
  );
}
