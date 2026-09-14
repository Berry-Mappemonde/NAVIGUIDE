import { useLang } from "../i18n/LangContext.jsx";

export function FollowToggle({ follow, onFollow, disabled }) {
  const { t } = useLang();
  return (
    <label className={`flex items-center justify-between rounded-xl border px-2.5 py-2 text-[10px] ${
      follow ? "border-emerald-500/40 bg-emerald-950/30 text-emerald-100" : "border-white/10 bg-slate-800/50 text-slate-300"
    } ${disabled ? "opacity-40 pointer-events-none" : ""}`}
    >
      <span className="font-semibold">{t("followModeLabel")}</span>
      <button
        type="button"
        role="switch"
        aria-checked={follow}
        disabled={disabled}
        onClick={() => onFollow(!follow)}
        className={`w-10 h-5 rounded-full relative transition-colors ${follow ? "bg-emerald-500" : "bg-slate-600"}`}
      >
        <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${follow ? "left-5" : "left-0.5"}`} />
      </button>
    </label>
  );
}
