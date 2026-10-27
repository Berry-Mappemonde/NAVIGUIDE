import { memo, useEffect, useState } from "react";
import { useLang } from "../i18n/LangContext.jsx";
import { filmWritingElapsedSeconds } from "../hooks/useReplay.js";

/**
 * Ligne courte posée AU-DESSUS de la barre film, en position absolue : la
 * barre garde sa hauteur (une rangée). Pendant la rédaction, les secondes
 * écoulées depuis le clic (horloge du navigateur). Après un clic Rédigé
 * resté brut, une issue neutre : le client ne connaît pas la raison.
 * Une seule ligne, levée au-dessus de la rangée des crédits de carte pour ne
 * jamais les couvrir sur téléphone ; les lecteurs d'écran entendent un message
 * stable, pas chaque seconde.
 */
export const FilmWriteStatus = memo(function FilmWriteStatus({ writing = false, since = 0, notice = "" }) {
  const { t } = useLang();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!writing) return undefined;
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [writing, since]);
  const text = writing
    ? t("filmWritingElapsed", { n: filmWritingElapsedSeconds(since, now) })
    : (notice === "not-written" ? t("filmWriteNotWritten") : "");
  const spoken = writing ? t("filmWritingAnnounce") : text;
  return (
    <div
      data-testid="film-write-status"
      data-state={writing ? "writing" : (notice || "idle")}
      role="status"
      className="absolute bottom-full left-0 mb-[26px] max-[599px]:mb-[48px] max-w-[60%] pointer-events-none"
    >
      {text ? (
        <span aria-hidden="true" className="naviguide-floating-card inline-block max-w-full truncate whitespace-nowrap align-bottom rounded-md border border-white/15 bg-slate-950/90 px-1.5 py-0.5 text-[10px] leading-tight text-white/85 tabular-nums shadow-lg">
          {text}
        </span>
      ) : null}
      {spoken ? <span className="sr-only">{spoken}</span> : null}
    </div>
  );
});
