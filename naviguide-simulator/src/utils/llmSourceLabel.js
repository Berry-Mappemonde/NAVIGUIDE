import nvidiaLogo from "../assets/brand/nvidia-logo-horz.svg";
import nebiusLogo from "../assets/brand/nebius-logo.svg";
import tokenFactoryLogo from "../assets/brand/tokenfactory-logo.svg";

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
  if (/gpt-oss|nvidia-gpt|\bnim\b/i.test(s)) return true;
  return isLlmWrittenSource(source);
}

/** Map cascade `source` to i18n key. */
export function llmSourceI18nKey(source) {
  const s = String(source || "");
  const lower = s.toLowerCase();
  if (lower.includes("reviewed") && lower.includes("ultra")) return "storySourceSuperReviewed";
  if (s === "openrouter") return "storySourceOpenrouter";
  if (s === "claude") return "storySourceClaude";
  if (s === "rules") return "storySourceRules";
  if (s === "budget") return "storySourceBudget";
  if (s === "cache") return "storySourceCache";
  if (s.endsWith("-lightning")) return "storySourceLightning";
  if (s.endsWith("-super")) return "storySourceSuper";
  if (s.endsWith("-ultra")) return "storySourceUltra";
  if (/gpt-oss|nvidia-gpt|\bnim\b/i.test(s)) return "storySourceNim";
  if (isLlmWrittenSource(s)) return "storySourceSuper";
  return "storySourceRules";
}

export function llmSourceLabel(source, t) {
  return t(llmSourceI18nKey(source));
}

/** Nemotron on Token Factory — show Built with + official marks (hackathon / Devpost). */
export function llmSourceShowsBrands(source) {
  const s = String(source || "");
  return s.endsWith("-lightning") || s.endsWith("-super") || s.endsWith("-ultra");
}

export const LLM_BRAND_LOGOS = Object.freeze({
  nvidia: { src: nvidiaLogo, alt: "NVIDIA" },
  nebius: { src: nebiusLogo, alt: "Nebius" },
  tokenFactory: { src: tokenFactoryLogo, alt: "Nebius Token Factory" },
});
