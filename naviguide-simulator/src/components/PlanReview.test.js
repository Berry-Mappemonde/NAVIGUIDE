import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "PlanReview.jsx"), "utf8");
const tools = readFileSync(join(here, "ToolsSidebar.jsx"), "utf8");
const app = readFileSync(join(here, "..", "App.jsx"), "utf8");

describe("PlanReview — commentaire (lot L5)", () => {
  it("affiche le paragraphe sous le tableau avec source i18n", () => {
    assert.match(src, /data-testid="plan-review-comment"/);
    assert.match(src, /planReviewCommentTitle/);
    assert.match(src, /storySourceRules/);
    assert.match(src, /commentSource/);
    assert.doesNotMatch(src, /Nemotron|Tavily|Nebius/);
  });

  it("reçoit le commentaire depuis la revue serveur, sans retirer le tableau", () => {
    assert.match(app, /comment: planReviewState\.review\?\.comment\?\.text/);
    assert.match(app, /commentSource: planReviewState\.review\?\.comment\?\.source/);
    assert.match(tools, /comment=\{planReview\.comment\}/);
    assert.match(tools, /<PlanReview[\s\S]*legs=\{planReview\.legs\}/);
    assert.match(src, /data-testid="plan-review"/);
    assert.match(src, /data-testid="plan-review-leg"/);
    assert.match(src, /data-testid="plan-review-leg-dates"/);
  });
});
