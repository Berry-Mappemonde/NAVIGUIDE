import { memo } from "react";
import { useLang } from "../i18n/LangContext.jsx";
import { ALL_LAYER_CONFIG } from "../constants/layers.js";

/**
 * The map layer pills (GRIB2, ZEE, ports, BI layers, science, seabed,
 * climatology). Since 19 Sept. 2026 they live folded in the tools sidebar:
 * « on n'a pas besoin de les voir, on a besoin de pouvoir les voir ».
 */
export const LayerToggles = memo(function LayerToggles({ maritimeLayers }) {
  const { t } = useLang();
  if (!maritimeLayers) return null;
  return (
    <div className="flex flex-wrap gap-1" data-testid="layer-toggles">
      {ALL_LAYER_CONFIG.map(({ key, labelKey, titleKey, color, showKey, toggleKey, loadingKey, errorKey }) => {
        const active = maritimeLayers[showKey];
        const loading = maritimeLayers[loadingKey];
        const error = maritimeLayers[errorKey];
        return (
          <button
            key={key}
            onClick={() => maritimeLayers[toggleKey]((v) => !v)}
            title={error ? `${t(titleKey)} : ${error}` : t(titleKey)}
            data-testid={`layer-${key}`}
            aria-pressed={active}
            className={[
              "flex items-center justify-center gap-1 px-1.5 py-0.5 rounded-full",
              "text-[9px] font-semibold transition-all duration-150 select-none",
              active
                ? "bg-slate-700/80 text-white border border-white/10"
                : "bg-slate-800/30 text-white/40 border border-white/5 hover:text-white/70",
            ].join(" ")}
          >
            {loading
              ? <div className="w-1.5 h-1.5 rounded-full border border-white/30 border-t-white animate-spin flex-shrink-0" />
              : <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: active ? color : "transparent", border: `1.5px solid ${error ? "#ef4444" : color}` }} />}
            {t(labelKey)}
          </button>
        );
      })}
    </div>
  );
});

/** How many layers are on — shown next to the folded title. */
export function activeLayerCount(maritimeLayers) {
  if (!maritimeLayers) return 0;
  return ALL_LAYER_CONFIG.filter(({ showKey }) => maritimeLayers[showKey]).length;
}
