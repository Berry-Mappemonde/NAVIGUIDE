import { useLang } from "../i18n/LangContext.jsx";
import { VIEW_SIMULATION, VIEW_SUIVRE } from "../constants/viewMode.js";

export function ViewModeSwitch({ view, onView, disabled = false }) {
  const { t } = useLang();
  const pill = (id, label, title, testId) => {
    const on = view === id;
    return (
      <button
        type="button"
        role="radio"
        aria-checked={on}
        data-testid={testId}
        disabled={disabled}
        onClick={() => onView(id)}
        title={title}
        className={[
          "min-w-0 w-full px-2 py-1.5 rounded-lg text-[10px] font-semibold leading-tight border text-center",
          on
            ? "border-cyan-400/70 bg-cyan-700/40 text-cyan-50"
            : "border-white/10 bg-slate-800/50 text-slate-300 hover:text-white hover:border-white/20",
          disabled ? "opacity-40 pointer-events-none" : "",
        ].join(" ")}
      >
        {label}
      </button>
    );
  };

  return (
    <div
      role="radiogroup"
      aria-label={t("viewModeGroup")}
      className="grid grid-cols-2 gap-1 mt-1.5"
    >
      {pill(VIEW_SUIVRE, t("followExpeditionButton"), t("followExpeditionTitle"), "view-suivre")}
      {pill(VIEW_SIMULATION, t("simulationButton"), t("simulationModeTooltip"), "view-simulation")}
    </div>
  );
}
