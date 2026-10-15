import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const src = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "llmSourceLabel.js"), "utf8");

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
