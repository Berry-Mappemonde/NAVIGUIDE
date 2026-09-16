import { useLang } from "../i18n/LangContext.jsx";
import { parseDepartureUtc, splitDepartureUtc } from "../engine/voyageClock.js";

export function DepartureField({ t0, onT0 }) {
  const { t, lang } = useLang();
  const { date, time } = splitDepartureUtc(t0);

  const setDate = (nextDate) => onT0?.(parseDepartureUtc(nextDate, time));
  const setTime = (nextTime) => onT0?.(parseDepartureUtc(date, nextTime));

  return (
    <div className="rounded-lg border border-white/10 bg-slate-800/50 px-2 py-1">
      <div className="text-[9px] font-semibold uppercase tracking-wider text-slate-400">
        {t("departureTitle")}
      </div>
      <div className="grid grid-cols-2 gap-1 mt-0.5">
        <label className="block">
          <span className="text-[8px] text-slate-500">{t("departureDate")}</span>
          <input
            type="date"
            lang={lang}
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="mt-0.5 w-full bg-slate-900/80 border border-white/10 rounded px-1.5 py-0.5 text-[10px] text-white"
          />
        </label>
        <label className="block">
          <span className="text-[8px] text-slate-500">{t("departureTimeUtc")}</span>
          <input
            type="time"
            lang={lang}
            value={time}
            onChange={(e) => setTime(e.target.value)}
            className="mt-0.5 w-full bg-slate-900/80 border border-white/10 rounded px-1.5 py-0.5 text-[10px] text-white"
          />
        </label>
      </div>
    </div>
  );
}
