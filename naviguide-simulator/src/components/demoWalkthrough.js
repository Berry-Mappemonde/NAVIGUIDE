// Visite guidée des juges : étapes et textes via t() (clés demo* dans i18n/en.js et fr.js).
// `custom` = une route terminée de l'utilisateur est la source (carte, briefing, film) :
// le texte ne parle alors ni de « film officiel » ni de la route Berry-Mappemonde.

export const DEMO_STEP_IDS = ["welcome", "live", "briefing", "layers", "replay", "trace", "return"];

/** Côté du panneau sur grand écran : à l'opposé du panneau que l'étape ouvre. */
export const DEMO_PANEL_SIDE = {
  welcome: "right",
  live: "right",
  briefing: "right",
  layers: "left",
  replay: "right",
  trace: "left",
  return: "right",
};

/**
 * @param {(key: string, vars?: object) => string} t
 * @param {{ replayState?: "ready" | "playing" | "unavailable", custom?: boolean }} [opts]
 */
export function getDemoSteps(t, { replayState = "unavailable", custom = false } = {}) {
  const replayBody = replayState === "playing"
    ? t("demoPlaying")
    : replayState === "ready"
      ? t(custom ? "demoReplayReadyCustom" : "demoReplayReady")
      : t(custom ? "demoReplayUnavailableCustom" : "demoReplayUnavailable");
  const body = {
    welcome: t("demoWelcomeBody"),
    live: t(custom ? "demoLiveBodyCustom" : "demoLiveBody"),
    briefing: t("demoBriefingBody"),
    layers: t("demoLayersBody"),
    replay: replayBody,
    trace: t(custom ? "demoTraceBodyFinished" : "demoTraceBody"),
    return: t(custom ? "demoReturnBodyCustom" : "demoReturnBody"),
  };
  const title = {
    welcome: t("demoWelcomeTitle"),
    live: t("demoLiveTitle"),
    briefing: t("demoBriefingTitle"),
    layers: t("demoLayersTitle"),
    replay: t("replayStart"),
    trace: t("demoTraceTitle"),
    return: t("demoReturnTitle"),
  };
  return DEMO_STEP_IDS.map((id) => ({ id, action: id, title: title[id], body: body[id], side: DEMO_PANEL_SIDE[id] }));
}
