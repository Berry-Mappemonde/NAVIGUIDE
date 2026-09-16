import { useEffect, useState } from "react";
import { useLang } from "../i18n/LangContext.jsx";
import {
  formatDepartureDate,
  normalizeUtcTime,
  parseDepartureUtc,
  parseFrenchDepartureDate,
  splitDepartureUtc,
} from "../engine/voyageClock.js";

export function DepartureField({ t0, onT0 }) {
  const { t } = useLang();
  const { date, time } = splitDepartureUtc(t0);
  const [dateValue, setDateValue] = useState(() => formatDepartureDate(date));
  const [timeValue, setTimeValue] = useState(time);

  useEffect(() => {
    setDateValue(formatDepartureDate(date));
    setTimeValue(time);
  }, [date, time]);

  const setDate = (nextDate) => {
    setDateValue(nextDate);
    const parsedDate = parseFrenchDepartureDate(nextDate);
    if (parsedDate) onT0?.(parseDepartureUtc(parsedDate, normalizeUtcTime(timeValue) || time));
  };
  const setTime = (nextTime) => {
    setTimeValue(nextTime);
    const parsedTime = normalizeUtcTime(nextTime);
    if (parsedTime) onT0?.(parseDepartureUtc(parseFrenchDepartureDate(dateValue) || date, parsedTime));
  };

  return (
    <div data-testid="departure-field" className="naviguide-departure-field h-[46px] rounded-lg border border-white/10 bg-slate-800/50 px-2 py-1">
      <div className="text-[9px] font-semibold uppercase tracking-wider text-slate-400">
        {t("departureTitle")}
      </div>
      <div className="grid grid-cols-[1.35fr_0.85fr] gap-1 mt-0.5">
        <label className="flex items-center gap-1 min-w-0">
          <span className="text-[8px] text-slate-500 whitespace-nowrap">{t("departureDate")}</span>
          <input
            type="text"
            inputMode="numeric"
            autoComplete="off"
            placeholder={t("departureDateFormat")}
            value={dateValue}
            onChange={(e) => setDate(e.target.value)}
            aria-invalid={dateValue !== "" && !parseFrenchDepartureDate(dateValue)}
            className="h-5 min-w-0 w-full bg-slate-900/80 border border-white/10 rounded px-1 text-[10px] text-white tabular-nums"
          />
        </label>
        <label className="flex items-center gap-1 min-w-0">
          <span className="text-[8px] text-slate-500 whitespace-nowrap">{t("departureTimeUtc")}</span>
          <input
            type="text"
            inputMode="numeric"
            autoComplete="off"
            placeholder="HH:MM"
            value={timeValue}
            onChange={(e) => setTime(e.target.value)}
            aria-invalid={timeValue !== "" && !normalizeUtcTime(timeValue)}
            className="h-5 min-w-0 w-full bg-slate-900/80 border border-white/10 rounded px-1 text-[10px] text-white tabular-nums"
          />
        </label>
      </div>
    </div>
  );
}
