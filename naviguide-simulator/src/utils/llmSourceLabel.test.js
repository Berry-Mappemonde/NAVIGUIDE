import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import en from "../i18n/en.js";
import fr from "../i18n/fr.js";

const src = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "llmSourceLabel.js"), "utf8");

async function loadLabelModule() {
  const stripped = src
    .replace(/^import .+\.svg";\n/gm, "")
    .replace(
      /export const LLM_BRAND_LOGOS = Object\.freeze\(\{[\s\S]*?\}\);/,
      "export const LLM_BRAND_LOGOS = Object.freeze({});",
    );
  const dir = mkdtempSync(join(tmpdir(), "llm-label-"));
  const file = join(dir, "llmSourceLabel.js");
  writeFileSync(file, stripped);
  try {
    return await import(pathToFileURL(file).href);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

describe("AI transparency — source helpers", () => {
  it("exports isAiGeneratedSource and maps legacy film ids", () => {
    assert.match(src, /export function isAiGeneratedSource/);
    assert.match(src, /export function isLlmWrittenSource/);
    assert.match(src, /storySourceSuperReviewed/);
    assert.match(src, /reviewedBy/);
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
    assert.match(src, /lower === "nemotron" \|\| lower\.includes\("super"\)/);
  });

  it("Lightning relu par Ultra ne devient pas Super relu par Ultra", async () => {
    const { llmSourceI18nKey } = await loadLabelModule();
    const lightning = llmSourceI18nKey("nemotron-lightning", "nemotron-ultra");
    assert.equal(lightning, "storySourceLightning");
    assert.equal(llmSourceI18nKey("nemotron-lightning", null), "storySourceLightning");
    assert.doesNotMatch(en[lightning], /reviewed by Ultra/i);
    assert.doesNotMatch(fr[lightning], /relu par Ultra/i);
    assert.equal(llmSourceI18nKey("nemotron-super", "nemotron-ultra"), "storySourceSuperReviewed");
    assert.equal(llmSourceI18nKey("nemotron", "nemotron-ultra"), "storySourceSuperReviewed");
    assert.match(fr.storySourceSuperReviewed, /relu par Ultra/);
  });
});
