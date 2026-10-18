import { memo } from "react";
import { useLang } from "../i18n/LangContext.jsx";
import { LLM_BRAND_LOGOS, isAiGeneratedSource, llmSourceLabel, llmSourceShowsBrands } from "../utils/llmSourceLabel.js";

/**
 * Source under generated text — actual cascade source, with optional
 * « Built with » brand marks (not a partnership claim).
 */
export const LlmSourceBadge = memo(function LlmSourceBadge({
  source,
  reviewedBy = null,
  label = null,
  testId = "llm-source",
  className = "",
  textOnly = false,
  hidden = false,
}) {
  const { t } = useLang();
  // `label` lets a caller name the model with its own mapping (film sources).
  const model = label || llmSourceLabel(source, t, reviewedBy);
  const aiGenerated = isAiGeneratedSource(source);
  const showBrands = llmSourceShowsBrands(source);
  const line = aiGenerated ? t("aiActGeneratedLabel", { model }) : model;

  return (
    <div
      data-testid={testId}
      data-ai-generated={aiGenerated ? "true" : "false"}
      data-llm-source={source || ""}
      hidden={hidden || undefined}
      className={`flex flex-col gap-0.5 min-w-0 ${className}`.trim()}
    >
      <span className="text-xs text-white leading-snug">{line}</span>
      {showBrands && textOnly ? (
        <span className="text-xs text-white leading-snug">{t("ed2BrandLine")}</span>
      ) : null}
      {showBrands && !textOnly ? (
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-white leading-snug">
          <span className="uppercase tracking-wide">{t("llmBuiltWith")}</span>
          <img src={LLM_BRAND_LOGOS.nvidia.src} alt={LLM_BRAND_LOGOS.nvidia.alt} className="h-3 w-auto object-contain" />
          <img src={LLM_BRAND_LOGOS.nebius.src} alt={LLM_BRAND_LOGOS.nebius.alt} className="h-2.5 w-auto object-contain" />
          <img src={LLM_BRAND_LOGOS.tokenFactory.src} alt={LLM_BRAND_LOGOS.tokenFactory.alt} className="h-2.5 w-auto object-contain" />
        </div>
      ) : null}
    </div>
  );
});
