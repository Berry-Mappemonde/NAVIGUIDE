import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const src = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "llmSourceLabel.js"), "utf8");

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
  });
});
