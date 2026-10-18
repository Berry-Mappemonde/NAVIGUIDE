import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import en from "../i18n/en.js";
import fr from "../i18n/fr.js";
import { isAiGeneratedSource, llmSourceI18nKey, llmSourceLabel, llmSourceShowsBrands } from "./llmSourceLabel.js";

const src = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "llmSourceLabel.js"), "utf8");
const badge = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../components/LlmSourceBadge.jsx"), "utf8");

const tEn = (key) => en[key];

describe("AI transparency — source helpers", () => {
  it("exports isAiGeneratedSource and maps legacy film ids", () => {
    assert.match(src, /export function isAiGeneratedSource/);
    assert.match(src, /export function isLlmWrittenSource/);
    assert.match(src, /storySourceSuperReviewed/);
    assert.match(src, /nemotron-super-token-factory/);
    assert.match(src, /s === "rules" \|\| s === "budget"/);
    assert.match(src, /\+local/);
    const keyFn = src.slice(src.indexOf("export function llmSourceI18nKey"));
    const reviewed = keyFn.indexOf("storySourceSuperReviewed");
    const ultra = keyFn.indexOf('endsWith("-ultra")');
    assert.ok(reviewed > 0 && reviewed < ultra, "reviewed-ultra avant le suffixe ultra");
  });
});

describe("llmSourceI18nKey", () => {
  it("maps Nemotron suffixes and does not disguise NIM as rules", () => {
    assert.match(src, /endsWith\("-ultra"\)/);
    assert.match(src, /gpt-oss\|nvidia-gpt\|\\bnim\\b/);
    assert.match(src, /return "storySourceNim"/);
    const nimIdx = src.indexOf("storySourceNim");
    const rulesReturn = src.lastIndexOf('return "storySourceRules"');
    assert.ok(nimIdx > 0 && nimIdx < rulesReturn, "NIM avant le repli rules");
  });

  it("names each Token Factory tier exactly, and never a fallback", () => {
    const exact = {
      "nemotron-lightning": "Nemotron 3.5 Lightning · Token Factory",
      "nvidia/Nemotron-3_5-Lightning": "Nemotron 3.5 Lightning · Token Factory",
      "nemotron-super": "Nemotron 3 Super · Token Factory",
      "nvidia/nemotron-3-super-120b-a12b": "Nemotron 3 Super · Token Factory",
      "nemotron-ultra": "Nemotron 3 Ultra · Token Factory",
      "nvidia/Nemotron-3-Ultra-550b-a55b": "Nemotron 3 Ultra · Token Factory",
      openrouter: "OpenRouter",
      "openai/gpt-4o-mini": "OpenRouter",
      claude: "Claude",
      "claude-haiku-4-5": "Claude",
      "nvidia-gpt-oss-20b": "NVIDIA NIM (fallback)",
      "openai/gpt-oss-20b": "NVIDIA NIM (fallback)",
      nim: "NVIDIA NIM (fallback)",
    };
    for (const [source, label] of Object.entries(exact)) {
      assert.equal(llmSourceLabel(source, tEn), label, source);
      assert.equal(en[llmSourceI18nKey(source)], label, source);
    }
    assert.equal(fr.storySourceOpenrouter, "OpenRouter");
    assert.equal(fr.storySourceClaude, "Claude");
    assert.equal(fr.llmBrandNvidia, "NVIDIA");
    assert.equal(fr.llmBrandNebius, "Nebius");
    assert.equal(en.llmBrandNvidia, "NVIDIA");
    assert.equal(en.llmBrandNebius, "Nebius");
    for (const source of ["openrouter", "openai/gpt-4o-mini", "claude", "claude-haiku-4-5", "nvidia-gpt-oss-20b", "openai/gpt-oss-20b", "nim"]) {
      assert.equal(llmSourceShowsBrands(source), false, source);
      assert.doesNotMatch(llmSourceLabel(source, tEn), /Token Factory/, source);
      assert.doesNotMatch(llmSourceLabel(source, (key) => fr[key]), /Token Factory/, source);
    }
    for (const source of [
      "nemotron-lightning",
      "nvidia/Nemotron-3_5-Lightning",
      "nemotron-super",
      "nvidia/nemotron-3-super-120b-a12b",
      "nemotron-ultra",
      "nvidia/Nemotron-3-Ultra-550b-a55b",
    ]) {
      assert.equal(llmSourceShowsBrands(source), true, source);
      assert.match(llmSourceLabel(source, tEn), /Nemotron .+ · Token Factory/, source);
    }
  });
});

describe("LlmSourceBadge — texte seul", () => {
  it("n'a aucune image de logo et nomme NVIDIA et Nebius en texte", () => {
    assert.doesNotMatch(badge, /<img\b/);
    assert.doesNotMatch(badge, /<svg\b/i);
    assert.doesNotMatch(badge, /backgroundImage|background-image/);
    assert.doesNotMatch(badge, /background\s*:\s*url\s*\(/i);
    assert.doesNotMatch(badge, /bg-\[url\(/);
    assert.doesNotMatch(badge, /\.svg|LLM_BRAND_LOGOS/);
    assert.doesNotMatch(src, /<img\b|<svg\b|backgroundImage|background\s*:\s*url\s*\(|bg-\[url\(|\.svg|LLM_BRAND_LOGOS/i);
    assert.equal(isAiGeneratedSource("openai/gpt-4o-mini"), true);
    assert.match(badge, /llmBrandNvidia/);
    assert.match(badge, /llmBrandNebius/);
    assert.match(badge, /llmSourceShowsBrands/);
    assert.match(badge, /llmSourceLabel/);
  });
});
