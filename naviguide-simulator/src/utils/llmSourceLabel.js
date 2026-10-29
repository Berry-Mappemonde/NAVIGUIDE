/** Legacy film and story ids, including nemotron-super-token-factory. */
export function isLlmWrittenSource(source) {
  const s = String(source || "").toLowerCase();
  if (!s || s.endsWith("+local")) return false;
  if (s === "nemotron-super-token-factory" || s === "nemotron-super" || s === "nemotron") return true;
  if (s.endsWith("-lightning") || s.endsWith("-super") || s.endsWith("-ultra")) return true;
  if (s.includes("nemotron")) return true;
  return false;
}

/** True when the visible text was drafted by a language model. */
export function isAiGeneratedSource(source) {
  const s = String(source || "").trim().toLowerCase();
  if (!s || s.endsWith("+local") || s === "rules" || s === "budget") return false;
  if (s === "cache" || s === "openrouter" || s === "claude") return true;
  if (/gpt-oss|nvidia-gpt|\bnim\b|\bgpt-4o\b|\bgpt-4\b/i.test(s)) return true;
  return isLlmWrittenSource(source);
}

/** Map cascade `source` or an exact model id to an i18n key. `reviewedBy` names Ultra when it edited.
 * Token Factory labels are only the three Nemotron tiers; a fallback never receives one. */
export function llmSourceI18nKey(source, reviewedBy) {
  const s = String(source || "");
  const lower = s.toLowerCase();
  const reviewed = String(reviewedBy || "").toLowerCase();
  const ultraReviewed = reviewed.includes("ultra") && (lower.includes("nemotron") || lower.includes("super") || isLlmWrittenSource(s)) && (lower === "nemotron" || lower.includes("super"));
  if ((lower.includes("reviewed") && lower.includes("ultra")) || ultraReviewed) return "storySourceSuperReviewed";
  if (s === "openrouter" || lower.startsWith("openrouter")) return "storySourceOpenrouter";
  if (s === "claude" || lower.startsWith("claude")) return "storySourceClaude";
  if (s === "rules") return "storySourceRules";
  if (s === "budget") return "storySourceBudget";
  if (s === "cache") return "storySourceCache";
  if (/gpt-oss|nvidia-gpt|\bnim\b/i.test(s) || lower.startsWith("nvidia-")) return "storySourceNim";
  if (/\bgpt-4o\b|\bgpt-4\b/i.test(lower)) return "storySourceOpenrouter";
  if (lower.endsWith("-nano") || lower.includes("-nano")) return "storySourceNano";
  if (s.endsWith("-lightning") || lower.includes("lightning")) return "storySourceLightning";
  if (s.endsWith("-super-vl") || lower.includes("super-vl")) return "storySourceSuperVl";
  if (s.endsWith("-super")) return "storySourceSuper";
  if (s.endsWith("-ultra") || (lower.includes("ultra") && lower.includes("nemotron"))) return "storySourceUltra";
  if (lower.includes("nemotron-3-super") || lower.includes("nemotron-super")) return "storySourceSuper";
  if (isLlmWrittenSource(s)) return "storySourceSuper";
  return "storySourceRules";
}

export function llmSourceLabel(source, t, reviewedBy) {
  return t(llmSourceI18nKey(source, reviewedBy));
}

const TOKEN_FACTORY_LABELS = new Set([
  "storySourceNano",
  "storySourceLightning",
  "storySourceSuper",
  "storySourceSuperVl",
  "storySourceSuperReviewed",
  "storySourceUltra",
]);

/** Nemotron on Token Factory — text names only, never a third-party logo. */
export function llmSourceShowsBrands(source) {
  return TOKEN_FACTORY_LABELS.has(llmSourceI18nKey(source));
}
