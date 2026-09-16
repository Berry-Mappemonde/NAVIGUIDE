import { memo } from "react";
import { useLang } from "../i18n/LangContext.jsx";
import { PROFILES, exampleLine } from "../engine/skipperOrders.js";

const PROFILE_KEY = {
  coastal: "skipperProfileCoastal",
  cruise: "skipperProfileCruise",
  ocean: "skipperProfileOcean",
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

/**
 * "Ordres du skipper" — three pills + boat read from the polar + phrases.
 * v1: no L / draft fields, no S6 knobs, no S7 drawer. Sits under the polar block.
 */
export const SkipperOrdersPanel = memo(function SkipperOrdersPanel({
  orders,
  profile,
  onProfile,
  onReset,
  sample = null,
  suggest = null,
  onAcceptSuggest,
  onDismissSuggest,
}) {
  const { lang, t } = useLang();
  if (!orders) return null;
  const en = lang === "en";
  const T = orders.values;
  const boat = orders.boat;
  const isSuivre = orders.mode === "suivre";
  const phrase = en ? orders.phrase.en : orders.phrase.fr;

  return (
    <div className="px-4 py-3 border-t border-slate-700/60" data-testid="skipper-orders">
      <div className="text-xs font-semibold text-slate-200 mb-2">{t("skipperOrdersTitle")}</div>

      <div role="group" aria-label={t("skipperOrdersTitle")} className="flex bg-slate-800 rounded-full p-0.5 gap-0.5">
        {PROFILES.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onProfile?.(p)}
            aria-pressed={profile === p}
            data-testid={`skipper-profile-${p}`}
            className={`flex-1 px-2 py-1 rounded-full text-xs font-bold transition-colors ${
              profile === p ? "bg-sky-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            {t(PROFILE_KEY[p])}
          </button>
        ))}
      </div>

      <p className="mt-2 text-xs text-sky-200 italic leading-snug" data-testid="skipper-phrase">{phrase}</p>
      <p className="mt-1 text-[10px] text-slate-400 leading-snug">{t("skipperSharedClock")}</p>
      <p className="mt-2 text-[11px] text-slate-300 leading-snug" data-testid="skipper-example">
        {exampleLine(orders, sample || {}, lang)}
      </p>

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
        <Row
          label={t("skipperHorizon")}
          value={isSuivre
            ? `${orders.budget.hours} h · ${num(orders.budget.maxNm, lang)} nm`
            : t("skipperHorizonLeg")}
          muted={!isSuivre}
        />
        <Row label={t("skipperGale")} value={`${T.galeKt} / ${T.galeHoldKt} kn · Beaufort 8 / 7`} muted />
      </div>

      <div
        data-testid="skipper-rain"
        className={`mt-2 text-[10px] rounded-md px-2 py-1 border leading-snug ${
          orders.rainEnabled ? "border-white/10 text-slate-300" : "border-white/5 text-slate-500"
        }`}
      >
        {orders.rainEnabled
          ? t("skipperRainSuivre", { mmh: num(T.rainMmH, lang), mm3h: num(T.rain3hMm, lang), nm: num(T.marinaRefugeNm, lang) })
          : t("skipperRainSimulation")}
      </div>

      {suggest && (
        <div className="mt-2 text-[10px] rounded-md px-2 py-1 border border-amber-500/30 text-amber-200 leading-snug" data-testid="skipper-suggest">
          <span>{t("skipperSuggestCoastal", { loa: num(boat.loaM, lang), draft: num(boat.draftM, lang, 1) })}</span>
          <span className="ml-2 inline-flex gap-1">
            <button type="button" onClick={onAcceptSuggest} className="px-1.5 rounded bg-amber-500/20 hover:bg-amber-500/40 text-amber-100">{t("skipperSuggestYes")}</button>
            <button type="button" onClick={onDismissSuggest} className="px-1.5 rounded hover:bg-white/10 text-amber-200/80">{t("skipperSuggestNo")}</button>
          </span>
        </div>
      )}

      {profile !== "cruise" && (
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
