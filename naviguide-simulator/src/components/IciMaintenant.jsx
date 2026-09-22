import { useState } from "react";
import { useLang } from "../i18n/LangContext.jsx";
import {
  ICI_TABS,
  dismissAlert,
  formatLegLine,
  regimeColor,
  visibleAlerts,
} from "./iciMaintenant.js";

function Section({ testId, label, children }) {
  return (
    <section data-testid={testId} className="ici-maintenant-section min-w-0">
      <div className="text-[10px] font-semibold text-slate-400 leading-snug">{label}</div>
      <div className="mt-0.5 min-w-0">{children}</div>
    </section>
  );
}

export function IciMaintenant({
  moment,
  view: viewProp,
  onViewChange,
  story = null,
  journal = null,
}) {
  const { t, lang } = useLang();
  const [localView, setLocalView] = useState("now");
  const [dismissed, setDismissed] = useState(() => new Set());
  const view = viewProp || localView;
  const setView = (id) => {
    if (typeof onViewChange === "function") onViewChange(id);
    else setLocalView(id);
  };
  const alerts = visibleAlerts(moment?.alerts, dismissed);
  const tint = regimeColor(moment?.leg?.regime);

  return (
    <div
      data-testid="ici-maintenant"
      className="ici-maintenant flex flex-col flex-1 min-h-0 overflow-auto rounded-lg border border-slate-700/50 bg-slate-800/50 px-2 py-1.5"
    >
      <div
        role="tablist"
        data-testid="ici-tabs"
        className="ici-maintenant-tabs flex items-center gap-2 shrink-0"
      >
        {ICI_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            data-testid={tab.testId}
            aria-selected={view === tab.id}
            onClick={() => setView(tab.id)}
            className={`text-[10px] leading-none px-0 py-0.5 bg-transparent border-0 cursor-pointer ${
              view === tab.id ? "text-slate-100" : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      {view === "now" ? (
        <div className="flex flex-col gap-2 mt-1.5 min-h-0">
          <Section testId="ici-section-leg" label={t("iciSectionLeg")}>
            <p
              data-testid="ici-leg-line"
              className="text-[11px] leading-snug text-slate-200 break-words [overflow-wrap:anywhere]"
              style={tint ? { color: tint } : undefined}
            >
              {formatLegLine(moment?.leg, t, lang)}
            </p>
          </Section>

          <Section testId="ici-section-alerts" label={t("iciSectionAlerts")}>
            <div className="flex flex-wrap gap-1">
              {alerts.map((alert) => {
                const danger = alert.severity === "alert";
                return (
                  <span
                    key={alert.id}
                    data-testid="ici-alert"
                    data-alert-id={alert.id}
                    className={`inline-flex items-center gap-1 max-w-full rounded-full border px-1.5 py-0.5 text-[10px] leading-snug ${
                      danger
                        ? "border-rose-400/50 bg-rose-950/40 text-rose-100"
                        : "border-amber-400/50 bg-amber-950/40 text-amber-100"
                    }`}
                  >
                    <span className="truncate">{alert.title}</span>
                    {alert.fact ? <span className="truncate text-white/70">· {alert.fact}</span> : null}
                    <button
                      type="button"
                      data-testid="ici-alert-close"
                      data-alert-id={alert.id}
                      aria-label={t("momentClose")}
                      onClick={() => setDismissed((prev) => dismissAlert(prev, alert.id))}
                      className="w-4 h-4 flex items-center justify-center rounded-full text-white/60 hover:text-white hover:bg-white/10 border-0 bg-transparent p-0 shrink-0"
                    >
                      ×
                    </button>
                  </span>
                );
              })}
            </div>
          </Section>

          <Section testId="ici-section-here" label={t("iciSectionHere")}>
            <div className="flex flex-col gap-0.5">
              {(moment?.here?.sentences || []).map((sentence) => (
                <p
                  key={sentence}
                  className="text-[11px] leading-snug text-slate-200 break-words [overflow-wrap:anywhere]"
                >
                  {sentence}
                </p>
              ))}
              {(moment?.here?.links || []).length ? (
                <div className="flex flex-wrap gap-1.5 mt-0.5">
                  {moment.here.links.map((link) => (
                    <a
                      key={link.url}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      data-testid="ici-source-link"
                      className="text-[10px] text-sky-300 hover:text-sky-100 no-underline"
                    >
                      {link.label}
                    </a>
                  ))}
                </div>
              ) : null}
            </div>
          </Section>

          <Section testId="ici-section-around" label={t("iciSectionAround")}>
            <div className="flex flex-col gap-0.5">
              {(moment?.around || []).map((item, i) => (
                <details
                  key={`${item.kind || "around"}-${item.title || i}`}
                  data-testid="ici-around"
                  data-kind={item.kind}
                  className="text-[11px] leading-snug text-slate-200"
                >
                  <summary className="cursor-pointer list-inside">
                    {item.title}
                    {item.fact ? <span className="text-slate-400"> · {item.fact}</span> : null}
                  </summary>
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      data-testid="ici-around-link"
                      className="ml-3 text-[10px] text-sky-300 hover:text-sky-100 no-underline"
                    >
                      {item.url}
                    </a>
                  ) : null}
                </details>
              ))}
            </div>
          </Section>

          <Section testId="ici-section-sources" label={t("iciSectionSources")}>
            <p data-testid="ici-sources-line" className="text-[10px] leading-snug text-slate-400">
              {(moment?.sources || []).filter(Boolean).join(" · ")}
            </p>
          </Section>
        </div>
      ) : null}

      {view === "story" ? (
        <div data-testid="ici-story-slot" className="mt-1.5 min-h-0 flex-1">
          {story}
        </div>
      ) : null}

      {view === "journal" ? (
        <div data-testid="ici-journal-slot" className="mt-1.5 min-h-0 flex-1">
          {journal}
        </div>
      ) : null}
    </div>
  );
}
