import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const src = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "useIciDossier.js"), "utf8");

describe("useIciDossier contract", () => {
  it("collects GET /ici without awaiting a chat, then judges locally", () => {
    assert.match(src, /One step = one GET \/ici/);
    assert.match(src, /Never await a model/);
    assert.match(src, /DEBOUNCE_MS = 800/);
    assert.match(src, /MOVE_NM = 3/);
    assert.match(src, /MIN_SCHEDULE_MS = 8000/);
    assert.match(src, /detectEvents/);
    assert.match(src, /judgeEvents/);
    assert.match(src, /along: null/);
    assert.doesNotMatch(src, /await fetch\(.*chat|Nemotron|Token Factory|enqueueStory/);
    assert.doesNotMatch(src, /tavily\?|nvidia\?/);
  });
});
