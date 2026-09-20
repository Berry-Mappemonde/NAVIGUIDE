import { memo } from "react";
import { ChevronRight, LocateFixed, X } from "lucide-react";
import { useLang } from "../i18n/LangContext.jsx";
import { canFocus, entityLinks } from "../engine/briefingLinks.js";
import { cardSpeech } from "../engine/momentCard.js";
import { ListenButton } from "./ListenButton.jsx";

function CardLinks({ entity, onFocus, t }) {
  if (!entity) return null;
  const links = entityLinks(entity);
  const focusable = canFocus(entity) && typeof onFocus === "function";
  if (!links.length && !focusable) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
      {focusable ? (
        <button
          type="button"
          onClick={() => onFocus(entity)}
          data-testid="moment-focus"
          title={t("briefingSeeOnMap")}
          className="flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold border border-sky-400/40 bg-sky-600/20 text-sky-100 hover:bg-sky-600/40"
        >
          <LocateFixed size={11} />
          {t("momentSeeOnMap")}
        </button>
      ) : null}
      {links.map((l) => (
        <a
          key={l.kind}
          href={l.href}
          target="_blank"
          rel="noopener noreferrer"
          data-testid={`moment-link-${l.kind}`}
          title={l.kind === "site" ? `${t("briefingOfficialSheet")} — ${l.host || ""}` : t("briefingGoogleMaps")}
          className="px-1.5 py-0.5 rounded-md text-[10px] border border-white/10 bg-white/5 text-sky-200 hover:text-white hover:bg-white/10 no-underline"
        >
          {l.kind === "site" ? `↗ ${l.host || t("briefingOfficialSheet")}` : `◎ ${t("briefingGoogleMaps")}`}
        </a>
      ))}
    </div>
  );
}

/**
 * NOW — sécurité / décision. Une seule carte, remplacée par la suivante,
 * fermable. Rouge ambré pour une alerte, cyan pour une décision.
 * `inline` : bloc du produit « ici » de la sidebar gauche ; sinon posée en
 * haut de la carte (Cinéma, sidebar rangée).
 */
export const MomentNowCard = memo(function MomentNowCard({ card, left = 0, onDismiss, onFocus, inline = false }) {
  const { t } = useLang();
  if (!card) return null;
  const alert = card.severity === "alert";
  const ahead = Number.isFinite(card.whenNm) && card.whenNm >= 1
    ? t("momentAhead", { nm: Math.round(card.whenNm) })
    : "";
  const border = alert ? "rgba(251, 191, 36, 0.7)" : "rgba(34, 211, 238, 0.55)";
  const frame = inline
    ? "sim-box-now rounded-lg border bg-slate-900/70 text-white px-2 py-1.5 min-w-0"
    : "naviguide-floating-card absolute left-1/2 -translate-x-1/2 z-[2050] w-[380px] max-w-[calc(100vw-2rem)] rounded-xl border bg-slate-950/94 text-white shadow-2xl px-3 py-2.5 backdrop-blur-sm";
  const style = inline
    ? { borderColor: border }
    : {
      top: 72,
      borderColor: border,
      boxShadow: alert
        ? "0 0 0 1px rgba(251,191,36,0.25), 0 18px 40px rgba(0,0,0,0.45)"
        : "0 0 0 1px rgba(34,211,238,0.18), 0 18px 40px rgba(0,0,0,0.45)",
    };
  return (
    <div data-testid="moment-now" data-type={card.type} data-inline={inline ? "1" : "0"} className={frame} style={style}>
      <div className="flex items-center gap-2 min-w-0">
        <span className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${alert ? "bg-amber-400 animate-pulse" : "bg-cyan-300"}`} />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-white/70 min-w-0 truncate">
          {t("momentNowTitle")}
          <span className={`ml-1.5 ${alert ? "text-amber-300" : "text-cyan-200"}`}>
            · {alert ? t("momentNowAlert") : t("momentNowDecision")}
          </span>
          {ahead ? <span className="ml-1.5 text-white/50 normal-case tracking-normal">· {ahead}</span> : null}
        </span>
        <div className="ml-auto flex items-center gap-1 flex-shrink-0">
          {left > 0 ? <span className="text-[9px] text-white/45">{t("momentLeft", { n: left })}</span> : null}
          {/* Pas de bouton « Écouter » ici (revue du 20 sept.) : la carte NOW se lit d'un coup d'œil, la voix est celle du récit. */}
          <button
            type="button"
            onClick={onDismiss}
            data-testid="moment-dismiss"
            title={t("momentClose")}
            className="w-6 h-6 flex items-center justify-center rounded-md text-white/60 hover:text-white hover:bg-white/10"
          >
            <X size={13} />
          </button>
        </div>
      </div>
      {card.title ? <div className="mt-1 text-[10px] font-semibold text-sky-200">{card.title}</div> : null}
      <p className={`mt-1 leading-snug text-slate-100 break-words [overflow-wrap:anywhere] ${inline ? "text-[11px]" : "text-[12px]"}`}>
        {card.text}
        {card.storyStatus === "pending" ? (
          <span className="ml-1 text-[10px] text-white/45">{t("momentStoryPending")}</span>
        ) : null}
      </p>
      <CardLinks entity={card.entity} onFocus={onFocus} t={t} />
    </div>
  );
});

/**
 * FREE — « pendant ce temps, autour du bateau ». Tourne sur l’information
 * quand aucune carte NOW n’est posée. `inline` dans la sidebar gauche ;
 * sinon petit bloc en bas à droite de la carte visible.
 */
export const FreeMomentBlock = memo(function FreeMomentBlock({ card, left = 0, onNext, onFocus, inline = false }) {
  const { t, lang } = useLang();
  if (!card) return null;
  const frame = inline
    ? "rounded-lg border border-white/10 bg-slate-800/50 text-white px-2 py-1.5 min-w-0"
    : "naviguide-floating-card absolute z-[2040] w-[300px] max-w-[calc(100vw-2rem)] rounded-xl border border-white/12 bg-slate-950/88 text-white shadow-xl px-3 py-2 backdrop-blur-sm";
  const style = inline
    ? undefined
    : {
      right: "calc(var(--sim-inset-right, 0px) + 12px)",
      bottom: "calc(var(--sim-inset-bottom, 0px) + 30px)",
    };
  return (
    <div data-testid="moment-free" data-kind={card.kind} data-inline={inline ? "1" : "0"} className={frame} style={style}>
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-[9px] font-semibold uppercase tracking-wider text-white/55 min-w-0 truncate">
          {t("momentFreeTitle")}
        </span>
        <div className="ml-auto flex items-center gap-1 flex-shrink-0">
          <ListenButton text={cardSpeech(card)} t={t} lang={lang} testId="moment-free-listen" />
          <button
            type="button"
            onClick={onNext}
            data-testid="moment-next"
            title={t("momentNext")}
            className="flex items-center gap-0.5 px-1.5 h-6 rounded-md text-[10px] text-white/70 hover:text-white hover:bg-white/10"
          >
            {left > 0 ? <span className="text-[9px] text-white/45">{left}</span> : null}
            <ChevronRight size={12} />
          </button>
        </div>
      </div>
      {card.title ? <div className="mt-1 text-[10px] font-semibold text-sky-200">{card.title}</div> : null}
      <p className="mt-0.5 text-[11px] leading-snug text-slate-200 break-words [overflow-wrap:anywhere]">
        {card.text}
      </p>
      <CardLinks entity={card.entity} onFocus={onFocus} t={t} />
    </div>
  );
});
