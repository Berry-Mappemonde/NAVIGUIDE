// Visite guidée des juges : étapes et textes via t() (clés demo* dans i18n/en.js et fr.js).
// `custom` = une route terminée de l'utilisateur est la source (carte, briefing, film) :
// le texte ne parle alors ni de « film officiel » ni de la route Berry-Mappemonde.

export const DEMO_STEP_IDS = ["welcome", "models", "live", "briefing", "layers", "replay", "trace", "return"];

/** Côté du panneau sur grand écran : à l'opposé du panneau que l'étape ouvre. */
export const DEMO_PANEL_SIDE = {
  welcome: "right",
  models: "right",
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
    models: t("demoModelsBody"),
    live: t(custom ? "demoLiveBodyCustom" : "demoLiveBody"),
    briefing: t("demoBriefingBody"),
    layers: t("demoLayersBody"),
    replay: replayBody,
    trace: t(custom ? "demoTraceBodyFinished" : "demoTraceBody"),
    return: t(custom ? "demoReturnBodyCustom" : "demoReturnBody"),
  };
  const title = {
    welcome: t("demoWelcomeTitle"),
    models: t("demoModelsTitle"),
    live: t("demoLiveTitle"),
    briefing: t("demoBriefingTitle"),
    layers: t("demoLayersTitle"),
    replay: t("replayStart"),
    trace: t("demoTraceTitle"),
    return: t("demoReturnTitle"),
  };
  return DEMO_STEP_IDS.map((id) => ({ id, action: id, title: title[id], body: body[id], side: DEMO_PANEL_SIDE[id] }));
}

// Étape « Qui fait quoi » : modèles Nemotron (Nebius Token Factory) par palier, lus en direct
// dans /ici/warm/status (`llm.configuredModels`). Sans réponse, on montre les défauts du code,
// signalés comme tels. Miroir de server/llm_budget.py DEFAULT_MODELS (un test pytest compare).
export const TOUR_DEFAULT_MODELS = {
  nano: "nvidia/Nemotron-3_5-Lightning",
  fast: "nvidia/Nemotron-3_5-Lightning",
  write: "nvidia/Nemotron-3.5-Super-VL",
  deep: "nvidia/Nemotron-3-Ultra-550b-a55b",
  judge: "nvidia/Nemotron-3-Ultra-550b-a55b",
};

const MODEL_NAMES = {
  "nvidia/nemotron-3_5-lightning": "Nemotron 3.5 Lightning",
  "nvidia/nemotron-3.5-super-vl": "Nemotron 3.5 Super VL",
  "nvidia/nemotron-3-ultra-550b-a55b": "Nemotron 3 Ultra",
  "nvidia/nemotron-3-super-120b-a12b": "Nemotron 3 Super 120B",
  "nvidia/nemotron-3-nano-30b-a3b": "Nemotron 3 Nano 30B",
  "nvidia/nvidia-nemotron-3-nano-30b-a3b": "Nemotron 3 Nano 30B",
};

/** Nom lisible d'un id Token Factory ; un id inconnu reste tel quel (rien d'inventé). */
export function modelDisplayName(id) {
  const raw = typeof id === "string" ? id.trim() : "";
  if (!raw) return "";
  return MODEL_NAMES[raw.toLowerCase()] || raw;
}

// Rôle → paliers de llm_budget.TIERS qui le servent (voir les appels cascade(tier=…)).
export const TOUR_MODEL_ROLES = [
  { id: "quick", tiers: ["nano", "fast"], key: "demoModelsQuick" },
  { id: "write", tiers: ["write"], key: "demoModelsWrite" },
  { id: "deep", tiers: ["deep", "judge"], key: "demoModelsDeep" },
];

/**
 * Lignes de l'étape « Qui fait quoi ».
 * @param {any} llm  bloc `llm` de /ici/warm/status (ou null si indisponible)
 * @param {(key: string, vars?: object) => string} t
 * @returns {{ live: boolean, rows: {id: string, text: string}[], today: string | null }}
 */
export function describeModelRoles(llm, t) {
  const cm = llm && typeof llm === "object" && llm.configuredModels && typeof llm.configuredModels === "object"
    ? llm.configuredModels
    : null;
  const live = Boolean(cm);
  const models = { ...TOUR_DEFAULT_MODELS, ...(cm || {}) };
  const rows = TOUR_MODEL_ROLES.map(({ id, tiers, key }) => {
    const names = [...new Set(tiers.map((tier) => modelDisplayName(models[tier])).filter(Boolean))];
    return { id, text: t(key, { models: names.join(" + ") }) };
  });
  rows.push({ id: "tavily", text: t("demoModelsTavily") });
  let today = null;
  if (llm && typeof llm === "object") {
    const calls = ["nano", "fast", "write", "deep", "judge"]
      .reduce((n, tier) => n + (Number(llm?.[tier]?.calls) || 0), 0);
    const tavily = Number(llm?.tavily?.calls) || 0;
    today = t("demoModelsToday", { calls: String(calls), tavily: String(tavily) });
  }
  return { live, rows, today };
}

/** `?tour=1` (ou true / yes / on) ouvre la visite au chargement. */
export function wantsTourFromUrl(search) {
  try {
    const v = new URLSearchParams(search || "").get("tour");
    return typeof v === "string" && ["1", "true", "yes", "on"].includes(v.trim().toLowerCase());
  } catch {
    return false;
  }
}
