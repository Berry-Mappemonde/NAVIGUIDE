import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "LogbookChat.jsx"), "utf8");
const hook = readFileSync(join(here, "..", "hooks", "useLogbookChat.js"), "utf8");
const sidebar = readFileSync(join(here, "Sidebar.jsx"), "utf8");

describe("LogbookChat contract (lot D)", () => {
  it("lives in the left sidebar, in both views, and says whether exchanges are logged", () => {
    assert.match(sidebar, /<LogbookChat messages=\{chat\.messages\}/);
    assert.match(sidebar, /\{!isDrawing && chat \? \(/, "any view, not while drawing");
    assert.match(src, /hasAdminSecret\(\)/);
    assert.match(src, /logbookChatSaved|logbookChatUnsaved/);
  });

  it("the hook posts one question at a time to /logbook/chat with the admin header and the client facts", () => {
    assert.match(hook, /fetch\(`\$\{API_URL\}\/logbook\/chat`/);
    assert.match(hook, /\.\.\.adminHeaders\(\)/);
    assert.match(hook, /inFlight\.current/);
    assert.match(hook, /contextFn\(\)/);
    assert.match(hook, /source: body\.source \|\| body\.engine \|\| null/);
    assert.doesNotMatch(hook, /Nemotron|Tavily|Nebius/i);
    assert.doesNotMatch(hook, /useEffect/);
  });

  it("shows the cascade source under the answer and does not fetch on render", () => {
    assert.match(src, /data-testid="chat-source"/);
    assert.match(src, /storySourceLightning|storySourceSuper|storySourceRules/);
    assert.doesNotMatch(src, /\/logbook\/chat/);
    const effects = src.match(/useEffect\(/g) || [];
    assert.equal(effects.length, 1, "only the scroll-to-bottom effect");
    assert.match(src, /el\.scrollTop = el\.scrollHeight/);
  });

  it("cadre de réponse sous la question (lot RA6)", () => {
    assert.match(src, /data-testid="logbook-chat-reply"/);
    const replyAt = src.indexOf('data-testid="logbook-chat-reply"');
    const listAt = src.indexOf('data-testid="logbook-chat-list"');
    const inputAt = src.indexOf('data-testid="logbook-chat-input"');
    assert.ok(replyAt > 0 && listAt > replyAt, "la liste est dans le cadre");
    assert.ok(inputAt > listAt, "le champ reste sous le cadre");
    assert.doesNotMatch(src, /logbookChatHint/);
  });
});
