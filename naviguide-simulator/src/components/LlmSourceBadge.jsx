import { memo } from "react";
import { useLang } from "../i18n/LangContext.jsx";
import { isAiGeneratedSource, llmSourceLabel, llmSourceShowsBrands } from "../utils/llmSourceLabel.js";

/**
 * Source under generated text. The cascade source stays visible, including
 * a fallback (OpenRouter, Claude, NIM). Nemotron on Token Factory adds the
 * names NVIDIA and Nebius as text — no third-party logo.
 */
export const LlmSourceBadge = memo(function LlmSourceBadge({ source, label = null, testId = "llm-source", className = "" }) {
  const { t } = useLang();
  // `label` lets a caller name the model with its own mapping (film sources).
  const model = label || llmSourceLabel(source, t);
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
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-white leading-snug" data-testid={`${testId}-brands`}>
          <span>{t("llmBrandNvidia")}</span>
          <span aria-hidden="true">·</span>
          <span>{t("llmBrandNebius")}</span>
        </div>
      ) : null}
    </div>
  );
});
