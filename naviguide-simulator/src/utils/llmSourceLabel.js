import nvidiaLogo from "../assets/brand/nvidia-logo-horz.svg";
import nebiusLogo from "../assets/brand/nebius-logo.svg";
import tokenFactoryLogo from "../assets/brand/tokenfactory-logo.svg";

/** Map cascade `source` to i18n key (lot L1). */
export function llmSourceI18nKey(source) {
  const s = String(source || "");
  if (s === "openrouter") return "storySourceOpenrouter";
  if (s === "claude") return "storySourceClaude";
  if (s === "rules") return "storySourceRules";
  if (s === "budget") return "storySourceBudget";
  if (s === "cache") return "storySourceCache";
  if (s.endsWith("-lightning")) return "storySourceLightning";
  if (s.endsWith("-super")) return "storySourceSuper";
  if (s.endsWith("-ultra")) return "storySourceUltra";
  if (/gpt-oss|nvidia-gpt|\bnim\b/i.test(s)) return "storySourceNim";
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
