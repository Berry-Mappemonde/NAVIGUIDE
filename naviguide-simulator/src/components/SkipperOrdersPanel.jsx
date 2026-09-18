import { memo } from "react";
import { useLang } from "../i18n/LangContext.jsx";
import {
  COMFORTS,
  COMFORT_DEFAULT,
  EXPERT_FIELDS,
  EXPERT_IDS,
  HORIZONS_H,
  PROFILES,
} from "../engine/skipperOrders.js";

const PROFILE_KEY = {
  coastal: "skipperProfileCoastal",
  cruise: "skipperProfileCruise",
  ocean: "skipperProfileOcean",
};

const COMFORT_KEY = {
  soft: "skipperComfortSoft",
  normal: "skipperComfortNormal",
  hard: "skipperComfortHard",
};

/** i18n label per Expert id (S7). Units come from the resolved thresholds. */
const EXPERT_KEY = {
  galePct: "skipperExpertGalePct",
  windShiftResetKt: "skipperExpertWindResetKt",
  windShiftResetDeg: "skipperExpertWindResetDeg",
  currentIgnoreKn: "skipperExpertCurrentIgnore",
  currentInvertDeg: "skipperExpertCurrentInvert",
  rainMmH: "skipperExpertRainMmH",
  rain3hMm: "skipperExpertRain3h",
  marinaRefugeNm: "skipperExpertMarinaNm",
  marinaRefugeCooldownMin: "skipperExpertMarinaCooldown",
  iciRadiusNm: "skipperExpertIciRadius",
  alongAmpNm: "skipperExpertAlongAmp",
  ampAheadMinNm: "skipperExpertAmpAhead",
};

function num(n, lang, digits = null) {
  if (!Number.isFinite(n)) return "—";
  const s = digits == null ? String(n) : n.toFixed(digits);
  return lang === "en" ? s : s.replace(".", ",");
}

function Row({ label, value, muted = false }) {
  return (
    <div className="flex items-center justify-between gap-2 py-1.5 border-b border-slate-700/40 last:border-0">
      <span className="text-[11px] text-slate-400">{label}</span>
      <span className={`text-[11px] font-semibold text-right ${muted ? "text-slate-400" : "text-white"}`}>{value}</span>
    </div>
  );
}

/** Small pill group shared by character (v1), comfort and horizon (S6). */
function Pills({ items, value, onPick, label, disabled = false, testPrefix, render }) {
  return (
    <div
      role="group"
      aria-label={label}
      className={`flex bg-slate-800 rounded-full p-0.5 gap-0.5 ${disabled ? "opacity-50" : ""}`}
    >
      {items.map((it) => (
        <button
          key={String(it)}
          type="button"
          disabled={disabled}
          onClick={() => onPick?.(it)}
          aria-pressed={value === it}
          data-testid={`${testPrefix}-${it}`}
          className={`flex-1 px-2 py-1 rounded-full text-xs font-bold transition-colors ${
            value === it ? "bg-sky-600 text-white" : "text-slate-400 hover:text-white"
          } ${disabled ? "cursor-not-allowed hover:text-slate-400" : ""}`}
        >
          {render(it)}
        </button>
      ))}
    </div>
  );
}

/**
 * "Ordres du skipper" — three pills + boat read from the polar + phrases (v1),
 * Comfort + horizon pills (S6), folded Expert drawer "Chiffres" (S7).
 * Sits under the polar block. Cinema hides the sidebar: orders stay active.
 */
export const SkipperOrdersPanel = memo(function SkipperOrdersPanel({
  orders,
  profile,
  onProfile,
  onComfort,
  onHorizon,
  onExpert,
  onReset,
  suggest = null,
  onAcceptSuggest,
  onDismissSuggest,
}) {
  const { lang, t } = useLang();
  if (!orders) return null;
  const T = orders.values;
  const boat = orders.boat;
  const isSuivre = orders.mode === "suivre";
  const comfort = orders.comfort || COMFORT_DEFAULT;
  const comfortPhrase = orders.comfortPhrase ? (lang === "en" ? orders.comfortPhrase.en : orders.comfortPhrase.fr) : "";
  const horizonH = orders.knobs?.horizonH ?? T.suivreLookaheadH;
  const expert = orders.expert || {};
  const expertCount = Object.keys(expert).length;
  const unitOf = (id) => orders.thresholds.find((x) => x.id === id)?.unit || "";
  const touched = profile !== "cruise"
    || comfort !== COMFORT_DEFAULT
    || horizonH !== orders.knobs?.horizonDefaultH
    || expertCount > 0;

  return (
    <div className="px-4 py-3 border-t border-slate-700/60" data-testid="skipper-orders">
      <Pills
        items={PROFILES}
        value={profile}
        onPick={onProfile}
        label={t("skipperProfileAria")}
        testPrefix="skipper-profile"
        render={(p) => t(PROFILE_KEY[p])}
      />

      <div className="mt-2 bg-slate-800/60 rounded-xl px-3 py-0.5 border border-slate-700/40">
        <Row label={t("skipperBoat")} value={boat.name || t("skipperBoatUnknown")} />
        <Row
          label={t("skipperLoa")}
          value={`${num(boat.loaM, lang)} m${boat.source.loa === "default" ? ` · ${t("skipperBerryDefault")}` : ""}`}
          muted={boat.source.loa === "default"}
        />
        <Row
          label={t("skipperDraft")}
          value={`${num(boat.draftM, lang, 1)} m${boat.source.draft === "default" ? ` · ${t("skipperBerryDefault")}` : ""}`}
          muted={boat.source.draft === "default"}
        />
        <Row
          label={t("skipperPlanningKn")}
          value={`${num(T.planningKn, lang)} kn · ${boat.source.planningKn === "polar" ? t("skipperFromPolar") : t("skipperProfileDefault")}`}
        />
        {isSuivre && (
          <Row
            label={t("skipperSuivreWindow")}
            value={`${orders.budget.hours} h · ${num(orders.budget.maxNm, lang)} nm`}
          />
        )}
        <Row label={t("skipperGale")} value={`${T.galeKt} / ${T.galeHoldKt} kn · Beaufort 8 / 7`} muted />
      </div>

      {/* S6 — Comfort: soft / normal / hard. Moves the notable-wind step and one notch of Hs. */}
      <div className="mt-2" data-testid="skipper-comfort">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] uppercase tracking-wide text-slate-500">{t("skipperComfortTitle")}</span>
          <span className="text-[10px] text-slate-400" data-testid="skipper-comfort-effect">
            {`+${num(T.windShiftKt, lang)} kn / ${num(T.windShiftDeg, lang)}° · Hs ${num(T.hsAlertM, lang, 1)} m`}
          </span>
        </div>
        <Pills
          items={COMFORTS}
          value={comfort}
          onPick={onComfort}
          label={t("skipperComfortAria")}
          testPrefix="skipper-comfort"
          render={(c) => t(COMFORT_KEY[c])}
        />
        {comfortPhrase && (
          <p className="mt-1 text-[10px] text-sky-200 italic leading-snug" data-testid="skipper-comfort-phrase">{comfortPhrase}</p>
        )}
      </div>

      {/* S6 — horizon knob: honest by construction (budget = H × kn). Greyed in Simulation. */}
      <div className="mt-2" data-testid="skipper-horizon">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] uppercase tracking-wide text-slate-500">{t("skipperSuivreWindow")}</span>
          <span className="text-[10px] text-slate-400">
            {isSuivre
              ? `${num(orders.budget.maxNm, lang)} nm · ${orders.budget.maxPearls} ${t("skipperPearls")}`
              : t("skipperHorizonLeg")}
          </span>
        </div>
        <Pills
          items={HORIZONS_H}
          value={horizonH}
          onPick={onHorizon}
          label={t("skipperHorizonAria")}
          disabled={!isSuivre}
          testPrefix="skipper-horizon"
          render={(h) => `${h} h`}
        />
      </div>

      {/* S7 — Expert drawer "Chiffres", folded by default. Gale stays read-only. */}
      <details className="mt-2 group" data-testid="skipper-expert">
        <summary className="cursor-pointer select-none text-[10px] uppercase tracking-wide text-slate-500 hover:text-slate-300 list-none flex items-center justify-between">
          <span>{t("skipperExpertTitle")}{expertCount ? ` · ${expertCount}` : ""}</span>
          <span className="text-slate-600 group-open:rotate-90 transition-transform">›</span>
        </summary>
        <p className="mt-1 text-[10px] text-slate-500 leading-snug">{t("skipperExpertHint")}</p>
        <div className="mt-1 bg-slate-800/60 rounded-xl px-3 py-0.5 border border-slate-700/40">
          {EXPERT_IDS.map((id) => {
            const f = EXPERT_FIELDS[id];
            const forced = id in expert;
            return (
              <div key={id} className="flex items-center justify-between gap-2 py-1 border-b border-slate-700/40 last:border-0">
                <label htmlFor={`skipper-expert-${id}`} className={`text-[11px] ${forced ? "text-amber-200" : "text-slate-400"}`}>
                  {t(EXPERT_KEY[id])}
                </label>
                <span className="flex items-center gap-1">
                  <input
                    id={`skipper-expert-${id}`}
                    type="number"
                    inputMode="decimal"
                    min={f.min}
                    max={f.max}
                    step={f.step}
                    value={T[id]}
                    onChange={(e) => onExpert?.(id, e.target.value)}
                    data-testid={`skipper-expert-${id}`}
                    className={`w-16 bg-slate-900 border rounded px-1 py-0.5 text-[11px] text-right text-white ${
                      forced ? "border-amber-500/60" : "border-slate-700"
                    }`}
                  />
                  <span className="text-[10px] text-slate-500 w-10">{unitOf(id)}</span>
                  <button
                    type="button"
                    onClick={() => onExpert?.(id, null)}
                    disabled={!forced}
                    aria-label={t("skipperExpertReset")}
                    title={t("skipperExpertReset")}
                    className={`text-[11px] px-1 rounded ${forced ? "text-amber-200 hover:bg-white/10" : "text-slate-700 cursor-default"}`}
                  >
                    ↺
                  </button>
                </span>
              </div>
            );
          })}
          <div className="flex items-center justify-between gap-2 py-1">
            <span className="text-[11px] text-slate-500">{t("skipperGale")}</span>
            <span className="text-[11px] text-slate-500">{`${T.galeKt} / ${T.galeHoldKt} kn · ${t("skipperExpertLocked")}`}</span>
          </div>
        </div>
      </details>

      {suggest && (
        <div className="mt-2 text-[10px] rounded-md px-2 py-1 border border-amber-500/30 text-amber-200 leading-snug" data-testid="skipper-suggest">
          <span>{t("skipperSuggestCoastal", { loa: num(boat.loaM, lang), draft: num(boat.draftM, lang, 1) })}</span>
          <span className="ml-2 inline-flex gap-1">
            <button type="button" onClick={onAcceptSuggest} className="px-1.5 rounded bg-amber-500/20 hover:bg-amber-500/40 text-amber-100">{t("skipperSuggestYes")}</button>
            <button type="button" onClick={onDismissSuggest} className="px-1.5 rounded hover:bg-white/10 text-amber-200/80">{t("skipperSuggestNo")}</button>
          </span>
        </div>
      )}

      {touched && (
        <button
          type="button"
          onClick={onReset}
          data-testid="skipper-reset"
          className="mt-2 text-[10px] text-slate-500 underline underline-offset-2 hover:text-slate-300"
        >
          {t("skipperResetBerry")}
        </button>
      )}
    </div>
  );
});
