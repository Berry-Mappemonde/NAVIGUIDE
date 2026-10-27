import { useState } from "react";
import { ArrowLeft, ArrowRight, Compass, Play, X } from "lucide-react";
import { getDemoSteps } from "./demoWalkthrough.js";

export { getDemoSteps } from "./demoWalkthrough.js";

export function DemoWalkthrough({
  lang = "en",
  replayReady = false,
  replayActive = false,
  onStepChange,
  onPlayReplay,
  onClose,
}) {
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const fr = lang === "fr";
  const steps = getDemoSteps(lang, replayReady);
  const step = steps[index];

  const start = () => {
    setIndex(0);
    setOpen(true);
    onStepChange?.(steps[0].action);
  };
  const close = () => {
    setOpen(false);
    onClose?.();
  };
  const goTo = (nextIndex) => {
    const next = Math.max(0, Math.min(steps.length - 1, nextIndex));
    setIndex(next);
    onStepChange?.(steps[next].action);
  };

  const primaryButton = "inline-flex items-center justify-center gap-1.5 rounded-lg border border-cyan-300/40 bg-cyan-300/15 px-3 py-2 text-xs font-semibold text-cyan-50 hover:bg-cyan-300/25 disabled:cursor-not-allowed disabled:opacity-45";
  const secondaryButton = "inline-flex items-center justify-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-xs font-semibold text-white/85 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <>
      {!open ? (
        <button
          type="button"
          data-testid="demo-walkthrough-launch"
          onClick={start}
          className="fixed right-3 top-14 z-[2300] inline-flex items-center gap-2 rounded-full border border-cyan-200/35 bg-slate-950/95 px-3 py-2 text-xs font-semibold text-white shadow-xl backdrop-blur-sm hover:bg-slate-900"
          title={fr ? "Ouvrir la visite guidée pour les juges" : "Open the judges’ guided walkthrough"}
        >
          <Compass size={15} aria-hidden="true" />
          {fr ? "Visite guidée" : "Guided demo"}
        </button>
      ) : (
        <aside
          role="region"
          aria-label={fr ? "Visite guidée de NAVIGUIDE" : "NAVIGUIDE guided walkthrough"}
          aria-live="polite"
          data-testid="demo-walkthrough-panel"
          className="fixed right-3 top-14 z-[2300] flex max-h-[calc(100dvh-5rem)] w-[min(23rem,calc(100vw-1.5rem))] flex-col overflow-y-auto rounded-2xl border border-white/15 bg-slate-950/96 p-4 text-white shadow-2xl backdrop-blur-md"
        >
          <div className="mb-3 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-cyan-100/80">
              <Compass size={14} aria-hidden="true" />
              {fr ? "NAVIGUIDE · VISITE GUIDÉE" : "NAVIGUIDE · GUIDED DEMO"}
            </div>
            <button
              type="button"
              onClick={close}
              aria-label={fr ? "Fermer la visite guidée" : "Close guided demo"}
              className="rounded-md p-1 text-white/65 hover:bg-white/10 hover:text-white"
            >
              <X size={17} aria-hidden="true" />
            </button>
          </div>

          <div
            role="progressbar"
            aria-label={fr ? "Progression de la visite" : "Walkthrough progress"}
            aria-valuemin={1}
            aria-valuemax={steps.length}
            aria-valuenow={index + 1}
            className="mb-4 h-1.5 overflow-hidden rounded-full bg-white/10"
          >
            <div className="h-full rounded-full bg-cyan-300/80 transition-[width]" style={{ width: `${((index + 1) / steps.length) * 100}%` }} />
          </div>

          <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-white/45">
            {fr ? `Étape ${index + 1} sur ${steps.length}` : `Step ${index + 1} of ${steps.length}`}
          </p>
          <h2 className="text-base font-semibold leading-snug text-white">{step.title}</h2>
          <p className="mt-2 text-sm leading-relaxed text-white/75">{step.body}</p>

          {step.id === "replay" ? (
            <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3">
              {replayActive ? (
                <p className="text-xs font-medium text-emerald-100">
                  {fr ? "Le film est en cours de lecture." : "The film is currently playing."}
                </p>
              ) : (
                <button type="button" onClick={onPlayReplay} disabled={!replayReady} className={primaryButton}>
                  <Play size={14} aria-hidden="true" />
                  {fr ? "Lancer le film officiel" : "Start official film"}
                </button>
              )}
              {!replayReady && !replayActive ? (
                <p className="mt-2 text-xs leading-relaxed text-white/55">
                  {fr ? "Aucune donnée de film n’est simulée ou injectée." : "No simulated or injected film data is used."}
                </p>
              ) : null}
            </div>
          ) : null}

          <div className="mt-5 flex items-center justify-between gap-2 border-t border-white/10 pt-3">
            <button type="button" onClick={() => goTo(index - 1)} disabled={index === 0} className={secondaryButton}>
              <ArrowLeft size={14} aria-hidden="true" />
              {fr ? "Précédent" : "Previous"}
            </button>
            {index < steps.length - 1 ? (
              <button type="button" onClick={() => goTo(index + 1)} className={primaryButton}>
                {fr ? "Suivant" : "Next"}
                <ArrowRight size={14} aria-hidden="true" />
              </button>
            ) : (
              <button type="button" onClick={close} className={primaryButton}>
                {fr ? "Terminer" : "Finish walkthrough"}
              </button>
            )}
          </div>
          <button
            type="button"
            onClick={close}
            className="mt-2 self-start rounded-md px-1 py-1 text-xs text-white/50 underline decoration-white/25 underline-offset-2 hover:text-white/80"
          >
            {fr ? "Quitter la visite" : "Exit walkthrough"}
          </button>
        </aside>
      )}
    </>
  );
}
