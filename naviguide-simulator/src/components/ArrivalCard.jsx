import { useLang } from "../i18n/LangContext.jsx";

export function ArrivalCard({
  name,
  sailNm,
  seaTime,
  nextName,
  holding = false,
}) {
  const { t } = useLang();
  if (!name) return null;
  return (
    <div className="absolute top-16 left-1/2 -translate-x-1/2 z-[2030] pointer-events-none">
      <div className="bg-slate-950/94 border border-cyan-400/45 text-white px-5 py-3 rounded-2xl shadow-2xl text-center max-w-[min(440px,92vw)]">
        <div className="text-base font-semibold leading-snug">
          {t("filmArrived", { name })}
        </div>
        <div className="mt-1 text-[11px] text-white/70">
          {Number.isFinite(Number(sailNm))
            ? t("filmArrivalNm", { nm: Math.round(Number(sailNm)).toLocaleString() })
            : ""}
          {seaTime ? ` · ${t("filmArrivalSea", { time: seaTime })}` : ""}
        </div>
        {nextName ? (
          <div className="mt-0.5 text-[11px] text-cyan-200/85">
            {t("filmArrivalNext", { name: nextName })}
          </div>
        ) : null}
        {holding ? (
          <div className="mt-1.5 text-[10px] font-semibold tracking-wide text-amber-200/90 uppercase">
            {t("filmArrivalHold")}
          </div>
        ) : null}
      </div>
    </div>
  );
}
