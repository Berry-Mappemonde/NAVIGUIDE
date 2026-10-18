import { memo } from "react";
import { useLang } from "../i18n/LangContext.jsx";
import { LLM_BRAND_LOGOS, isAiGeneratedSource, llmSourceLabel, llmSourceShowsBrands } from "../utils/llmSourceLabel.js";

/**
 * Source under generated text — actual cascade source, with optional
 * « Built with » brand marks (not a partnership claim).
 */
export const LlmSourceBadge = memo(function LlmSourceBadge({ source, testId = "llm-source", className = "" }) {
  const { t } = useLang();
  const model = llmSourceLabel(source, t);
  const aiGenerated = isAiGeneratedSource(source);
  const showBrands = llmSourceShowsBrands(source);
  const line = aiGenerated ? t("aiActGeneratedLabel", { model }) : model;

  return (
    <div
      data-testid={testId}
      data-ai-generated={aiGenerated ? "true" : "false"}
      data-llm-source={source || ""}
      className={`flex flex-col gap-0.5 min-w-0 ${className}`.trim()}
    >
      <span className="text-xs text-white leading-snug">{line}</span>
      {showBrands ? (
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
