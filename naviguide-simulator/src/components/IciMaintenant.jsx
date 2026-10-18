import { useEffect, useMemo, useState } from "react";
import { useLang } from "../i18n/LangContext.jsx";
import { canFocus, entityLinks } from "../engine/briefingLinks.js";
import { EscaleSheet } from "./EscaleSheet.jsx";
import { PlanReview } from "./PlanReview.jsx";
import { sortJournalEntries } from "../hooks/useMomentJournal.js";
import {
  visibleIciTabs,
  hiddenIciTabs,
  defaultIciTab,
  servesNowContent,
  isTracerIciMode,
  dismissAlert,
  formatJournalLine,
  formatLegLine,
  regimeColor,
  seekJournalEntry,
  visibleAlerts,
  displayIciFrame,
  withNowLeg,
  localizeStoredTitle,
} from "./iciMaintenant.js";

const API = import.meta.env?.VITE_API_URL ?? "";

function Section({ testId, label, children }) {
  return (
    <section data-testid={testId} className="ici-maintenant-section min-w-0">
      <div className="text-[10px] font-semibold text-slate-400 leading-snug">{label}</div>
      <div className="mt-0.5 min-w-0">{children}</div>
    </section>
  );
}

function CardAlias({ card, testId, lang = "fr", onDismiss, onNext, onFocus }) {
  const { t } = useLang();
  if (!card) return null;
  const title = localizeStoredTitle(card.title, lang);
  const links = entityLinks(card.entity);
  const focusable = canFocus(card.entity) && typeof onFocus === "function";
  return (
    <div
      data-testid={testId}
      data-type={card.type}
      data-kind={card.kind}
      data-inline="1"
      className="text-[11px] leading-snug text-slate-200 break-words [overflow-wrap:anywhere]"
    >
      {title ? <div className="text-[10px] font-semibold text-sky-200">{title}</div> : null}
      {card.text ? <p>{card.text}</p> : null}
      {testId === "moment-now" && typeof onDismiss === "function" ? (
        <button
          type="button"
          data-testid="moment-dismiss"
          onClick={onDismiss}
          className="mt-0.5 text-[10px] text-slate-300 bg-transparent border-0 cursor-pointer px-0"
        >
          {t("momentClose")}
        </button>
      ) : null}
      {testId === "moment-free" && typeof onNext === "function" ? (
        <button
          type="button"
          data-testid="moment-next"
          onClick={onNext}
          className="mt-0.5 text-[10px] text-slate-300 bg-transparent border-0 cursor-pointer px-0"
        >
          {t("momentNext")}
        </button>
      ) : null}
      {focusable ? (
        <button
          type="button"
          data-testid="moment-focus"
          onClick={() => onFocus(card.entity)}
          className="mt-0.5 ml-2 text-[10px] text-sky-300 bg-transparent border-0 cursor-pointer px-0"
        >
          {t("momentSeeOnMap")}
        </button>
      ) : null}
      {links.map((link) => (
        <a
          key={`${link.kind}-${link.href}`}
          href={link.href}
          target="_blank"
          rel="noopener noreferrer"
          data-testid={`moment-link-${link.kind}`}
          className="ml-2 text-[10px] text-sky-300 hover:text-sky-100 no-underline"
        >
          {link.host || "↗"}
        </a>
      ))}
    </div>
  );
}

function asJournalRow(entry) {
  if (!entry || entry.signature) return entry;
  const lat = entry.lat;
  const lon = entry.lon;
  const title = entry.name || entry.title || "";
  return {
    ...entry,
    signature: entry.id || entry.t,
    pos: entry.pos || (lat != null && lon != null ? { lat, lon } : null),
    changes: entry.changes || (title ? [{ title, fact: entry.kind || "" }] : []),
  };
}

function JournalList({ entries, onSeek, lang, days = null }) {
  const rows = sortJournalEntries(entries);
  const orderedDays = useMemo(() => {
    const names = (Array.isArray(days) ? days : [])
      .map((day) => (typeof day === "string" ? day : day?.day))
      .filter(Boolean);
    return [...new Set(names)].sort();
  }, [days]);
  const [openDay, setOpenDay] = useState(null);
  const [dayRows, setDayRows] = useState([]);

  async function selectDay(day) {
    if (typeof onSeek === "function") onSeek(`${day}T12:00:00Z`);
    setOpenDay(day);
    try {
      const res = await fetch(`${API}/voyage/official/journal/${encodeURIComponent(day)}`);
      if (res.ok) {
        const data = await res.json();
        const list = Array.isArray(data) ? data : (data.entries || []);
        setDayRows(Array.isArray(list) ? list.map(asJournalRow) : []);
        return;
      }
    } catch {
      /* the day list still moved the cursor */
    }
    setDayRows(rows.filter((entry) => String(entry.t || "").startsWith(day)));
  }

  const shown = (openDay ? dayRows : (orderedDays.length ? [] : rows)).map(asJournalRow).filter(Boolean);
  return (
    <ul data-testid="ici-journal-list" className="flex flex-col gap-0.5 m-0 p-0 list-none">
      {orderedDays.map((day) => (
        <li key={day}>
          <button
            type="button"
            data-testid="journal-day"
            data-day={day}
            onClick={() => selectDay(day)}
            className="w-full text-left text-[11px] leading-snug px-0.5 py-0.5 bg-transparent border-0 cursor-pointer hover:bg-white/5 text-slate-200"
          >
            {day}
          </button>
        </li>
      ))}
      {shown.map((entry) => (
        <li key={entry.signature || `${entry.seq}-${entry.t}`}>
          <button
            type="button"
            data-testid="ici-journal-entry"
            data-t={entry.t}
            onClick={() => seekJournalEntry(onSeek, entry)}
            className="ici-journal-entry w-full text-left text-[11px] leading-snug px-0.5 py-0.5 bg-transparent border-0 cursor-pointer hover:bg-white/5 break-words [overflow-wrap:anywhere]"
          >
            {formatJournalLine(entry, lang)}
          </button>
        </li>
      ))}
    </ul>
  );
}

export function IciMaintenant({
  moment,
  view: viewProp,
  onViewChange,
  story = null,
  journal = null,
  journalEntries = null,
  onSeek = null,
  mode = "follow",
  routeSource = "berry",
  planReview = null,
  simulation = null,
  hereBody = null,
  escale = null,
  momentNow = null,
  momentFree = null,
  onMomentDismiss = null,
  onMomentNext = null,
  onMomentFocus = null,
  nowLeg = null,
  journalDays = null,
  todayPosition = false,
}) {
  const { t, lang } = useLang();
  const [localView, setLocalView] = useState(() => defaultIciTab(mode, { routeSource }));
  const [dismissed, setDismissed] = useState(() => new Set());
  const view = viewProp || localView;
  const setView = (id) => {
    if (typeof onViewChange === "function") onViewChange(id);
    else setLocalView(id);
  };
  const frame = displayIciFrame(moment, journalEntries, mode);
  const shown = withNowLeg(frame.shown, nowLeg);
  const here = frame.here;
  const alerts = visibleAlerts(frame.alerts, dismissed);
  const tint = regimeColor(shown?.leg?.regime);
  const tabs = visibleIciTabs(mode, { routeSource });
  const extraTabs = hiddenIciTabs(mode, { routeSource });
  const showNowServing = servesNowContent(view, mode, { routeSource });
  const tracer = isTracerIciMode(mode);

  useEffect(() => {
    if (!escale?.stop) return;
    // Visible ou hidden (Tracer / DM9) : la fiche d'escale sélectionne Maintenant
    // (RC2 lit aria-selected sur le testid, même si l'onglet n'est pas montré).
    const hasNowTab = tabs.some((tab) => tab.id === "now")
      || extraTabs.some((tab) => tab.id === "now");
    const nowVisible = tabs.some((tab) => tab.id === "now");
    if (nowVisible) {
      if (typeof onViewChange === "function") onViewChange("now");
      else setLocalView("now");
      return;
    }
    if (hasNowTab && tracer) {
      if (typeof onViewChange === "function") onViewChange("now");
      else setLocalView("now");
      return;
    }
    if (tracer && view !== "review") setView("review");
  }, [escale?.stop?.name, escale?.stop?.lat, escale?.stop?.lon, onViewChange, mode, routeSource]);

  useEffect(() => {
    if (tabs.some((tab) => tab.id === view)) return;
    setView(defaultIciTab(mode, { routeSource }));
  }, [mode, routeSource]);

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
        {tabs.map((tab) => (
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
        {extraTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            hidden
            tabIndex={-1}
            aria-hidden="true"
            data-testid={tab.testId}
            aria-selected={view === tab.id}
            onClick={() => setView(tab.id)}
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      {showNowServing ? (
        <div className="flex flex-col gap-2 mt-1 min-h-0">
          <Section testId="ici-section-leg" label={t("iciSectionLeg")}>
            <p
              data-testid="ici-leg-line"
              className="text-[11px] leading-snug text-slate-200 break-words [overflow-wrap:anywhere]"
              style={tint ? { color: tint } : undefined}
            >
              {formatLegLine(shown?.leg, t, lang)}
            </p>
            {simulation}
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
                    <span className="truncate">{localizeStoredTitle(alert.title, lang)}</span>
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
            <CardAlias
              card={momentNow}
              testId="moment-now"
              lang={lang}
              onDismiss={onMomentDismiss}
              onFocus={onMomentFocus}
            />
          </Section>

          <Section testId="ici-section-here" label={t("iciSectionHere")}>
            <div className="flex flex-col gap-0.5">
              {escale?.stop ? (
                <EscaleSheet
                  stop={escale.stop}
                  fiche={escale.fiche}
                  loading={escale.loading}
                  error={escale.error}
                  onClose={escale.onClose}
                  onFocus={escale.onFocus}
                />
              ) : null}
              {todayPosition ? (
                <p
                  data-testid="ici-today-position"
                  className="text-[11px] leading-snug text-amber-200 break-words [overflow-wrap:anywhere]"
                >
                  {t("iciTodayPosition")}
                </p>
              ) : (
                <>
                  {hereBody}
                  {(here?.sentences || []).map((sentence) => (
                    <p
                      key={sentence}
                      data-testid="ici-here-sentence"
                      className="text-[11px] leading-snug text-slate-200 break-words [overflow-wrap:anywhere]"
                    >
                      {sentence}
                    </p>
                  ))}
                  {(here?.links || []).length ? (
                    <div className="flex flex-wrap gap-1.5 mt-0.5">
                      {here.links.map((link) => (
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
                </>
              )}
            </div>
          </Section>

          <Section testId="ici-section-around" label={t("iciSectionAround")}>
            <div className="flex flex-col gap-0.5">
              <CardAlias
                card={momentFree}
                testId="moment-free"
                lang={lang}
                onNext={onMomentNext}
                onFocus={onMomentFocus}
              />
              {(frame.around || []).map((item, i) => (
                <details
                  key={`${item.kind || "around"}-${item.title || i}`}
                  data-testid="ici-around"
                  data-kind={item.kind}
                  className="text-[11px] leading-snug text-slate-200"
                >
                  <summary className="cursor-pointer list-inside">
                    {localizeStoredTitle(item.title, lang)}
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
              {(frame.sources || []).filter(Boolean).join(" · ")}
            </p>
          </Section>
        </div>
      ) : null}

      {view === "story" ? (
        <div data-testid="ici-story-slot" className="mt-1 min-h-0">
          <CardAlias
            card={momentNow}
            testId="moment-now"
            lang={lang}
            onDismiss={onMomentDismiss}
            onFocus={onMomentFocus}
          />
          <CardAlias
            card={momentFree}
            testId="moment-free"
            lang={lang}
            onNext={onMomentNext}
            onFocus={onMomentFocus}
          />
          {story}
        </div>
      ) : null}

      {/* Liste toujours au DOM (hidden hors onglet) : RC2 peut voler
          Maintenant sans démonter les lignes — R9b compte ici-journal-entry. */}
      <div
        data-testid="ici-journal-slot"
        hidden={view !== "journal"}
        className="mt-1 min-h-0 overflow-auto"
      >
        {Array.isArray(journalEntries) ? (
          <JournalList entries={journalEntries} onSeek={onSeek} lang={lang} days={journalDays} />
        ) : journal}
      </div>

      {view === "review" ? (
        <div data-testid="ici-review-slot" className="mt-1 min-h-0 overflow-auto">
          {planReview ? (
            <PlanReview
              legs={planReview.legs}
              loading={planReview.loading}
              error={planReview.error}
              summary={planReview.summary}
              comment={planReview.comment}
              commentSource={planReview.commentSource}
              advice={planReview.advice}
              onApply={planReview.onApply}
              startOpen
            />
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
