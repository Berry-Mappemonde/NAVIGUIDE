import { useLang } from "../i18n/LangContext.jsx";

function splitUtc(iso) {
  const d = iso ? new Date(iso) : new Date();
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return { date: `${y}-${m}-${day}`, time: `${hh}:${mm}` };
}

function joinUtc(date, time) {
  return `${date}T${time}:00Z`;
}

export function defaultVirtualT0() {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + 1);
  d.setUTCHours(8, 0, 0, 0);
  return d.toISOString().replace(/\.000Z$/, "Z");
}

export function DepartureField({
  t0,
  onT0,
  startAt,
  onStartAt,
  virtualBoat,
  onVirtualBoat,
}) {
  const { t } = useLang();
  const { date, time } = splitUtc(t0);

  return (
    <div className="rounded-xl border border-cyan-700/30 bg-slate-800/50 p-2.5 space-y-2">
      <div className="text-[10px] font-semibold text-cyan-300/90 uppercase tracking-wider">
        {t("departureTitle")}
      </div>
      <div className="flex gap-1.5">
        <input
          type="date"
          value={date}
          onChange={(e) => onT0(joinUtc(e.target.value, time))}
          className="flex-1 bg-slate-900/80 border border-white/10 rounded-lg px-2 py-1 text-[11px] text-white"
        />
        <input
          type="time"
          value={time}
          onChange={(e) => onT0(joinUtc(date, e.target.value))}
          className="w-[88px] bg-slate-900/80 border border-white/10 rounded-lg px-2 py-1 text-[11px] text-white"
        />
        <span className="self-center text-[10px] text-white/45">UTC</span>
      </div>
      <label className="flex items-center justify-between text-[10px] text-slate-300">
        <span>{t("startAtLabel")}</span>
        <select
          value={startAt}
          onChange={(e) => onStartAt(e.target.value)}
          className="bg-slate-900/80 border border-white/10 rounded-md px-1.5 py-0.5 text-[10px] text-white"
        >
          <option value="la-rochelle">{t("startLaRochelle")}</option>
          <option value="saint-maur">{t("startSaintMaur")}</option>
        </select>
      </label>
      <label className="flex items-center gap-2 text-[10px] text-slate-200">
        <input
          type="checkbox"
          checked={virtualBoat}
          onChange={(e) => onVirtualBoat(e.target.checked)}
        />
        {t("virtualBoatLabel")}
      </label>
    </div>
  );
}
