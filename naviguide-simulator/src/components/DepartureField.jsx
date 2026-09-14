import { useLang } from "../i18n/LangContext.jsx";
import { parseDepartureUtc, splitDepartureUtc } from "../engine/voyageClock.js";

export function DepartureField({ t0, startAt, onT0, onStartAt, virtualBoat, onVirtualBoat }) {
  const { t, lang } = useLang();
  const { date, time } = splitDepartureUtc(t0);

  const setDate = (nextDate) => onT0?.(parseDepartureUtc(nextDate, time));
  const setTime = (nextTime) => onT0?.(parseDepartureUtc(date, nextTime));

  return (
    <div className="rounded-xl border border-white/10 bg-slate-800/50 px-3 py-2 space-y-2">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
        {t("departureTitle")}
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        <label className="block">
          <span className="text-[9px] text-slate-500">{t("departureDate")}</span>
          <input
            type="date"
            lang={lang}
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="mt-0.5 w-full bg-slate-900/80 border border-white/10 rounded-lg px-2 py-1 text-[11px] text-white"
          />
        </label>
        <label className="block">
          <span className="text-[9px] text-slate-500">{t("departureTimeUtc")}</span>
          <input
            type="time"
            lang={lang}
            value={time}
            onChange={(e) => setTime(e.target.value)}
            className="mt-0.5 w-full bg-slate-900/80 border border-white/10 rounded-lg px-2 py-1 text-[11px] text-white"
          />
        </label>
      </div>
      <fieldset className="space-y-1">
        <legend className="text-[9px] text-slate-500">{t("departureStartAt")}</legend>
        <label className="flex items-center gap-1.5 text-[11px] text-white/80">
          <input
            type="radio"
            name="voyage-start-at"
            checked={startAt === "la-rochelle"}
            onChange={() => onStartAt?.("la-rochelle")}
          />
          {t("departureLaRochelle")}
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-white/80">
          <input
            type="radio"
            name="voyage-start-at"
            checked={startAt === "saint-maur"}
            onChange={() => onStartAt?.("saint-maur")}
          />
          {t("departureSaintMaur")}
        </label>
      </fieldset>
      <label className="flex items-center gap-2 text-[11px] text-slate-200">
        <input
          type="checkbox"
          checked={Boolean(virtualBoat)}
          onChange={(e) => onVirtualBoat?.(e.target.checked)}
        />
        {t("virtualBoatLabel")}
      </label>
    </div>
  );
}
