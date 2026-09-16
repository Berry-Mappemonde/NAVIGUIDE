import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  KEEP_STORY_TYPES,
  MAX_STORY_PENDING,
  enqueueStory,
  pendingStoryCount,
  resetStoryQueue,
  shouldEnqueueStory,
  storyPayload,
  subscribeStories,
} from "./storyQueue.js";

const src = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "storyQueue.js"), "utf8");

function waitJob(eventId, status, ms = 400) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error(`timeout waiting ${status}`)), ms);
    const off = subscribeStories((job) => {
      if (job.eventId === eventId && job.status === status) {
        clearTimeout(t);
        off();
        resolve(job);
      }
    });
  });
}

describe("storyQueue contract", () => {
  it("is the usual cascade, not Nemotron / Tavily / Token Factory", () => {
    assert.match(src, /nim-or-claude/);
    assert.match(src, /void runStory/);
    assert.match(src, /Play never awaits/);
    assert.match(src, /Not Nemotron/);
    assert.match(src, /Not Token Factory/);
    assert.doesNotMatch(src, /tavily\.search|nvidia-nemotron/);
  });
});

describe("shouldEnqueueStory + payload", () => {
  it("enqueues now/group, skips hide/later/already pending", () => {
    assert.equal(shouldEnqueueStory({ judge: "now", story: { status: "template" } }), true);
    assert.equal(shouldEnqueueStory({ judge: "group", story: { status: "template" } }), true);
    assert.equal(shouldEnqueueStory({ judge: "later", story: { status: "template" } }), false);
    assert.equal(shouldEnqueueStory({ judge: "hide" }), false);
    assert.equal(shouldEnqueueStory({ judge: "now", story: { status: "pending" } }), false);
    assert.equal(shouldEnqueueStory({ judge: "now", story: { status: "ready" } }), false);
  });

  it("asks for :online only when a pack URL + gold/alert/click", () => {
    const gold = storyPayload({
      id: "zee-enter:1",
      type: "zee-enter",
      severity: "watch",
      judge: "now",
      payload: {
        zee: { gold_pack: true },
        poe: { url: "https://douane.gouv.fr", name: "La Rochelle" },
        tavily: null,
      },
    });
    assert.equal(gold.needPage, true);
    assert.equal(gold.pageUrl, "https://douane.gouv.fr");
    assert.equal(gold.tavily, null);

    const plain = storyPayload({
      id: "wind-shift:1",
      type: "wind-shift",
      severity: "info",
      judge: "now",
      payload: { kind: "forecast", tavily: null },
    });
    assert.equal(plain.needPage, false);
    assert.equal(plain.pageUrl, null);
  });
});

describe("enqueueStory fire-and-forget", () => {
  const origFetch = globalThis.fetch;

  beforeEach(() => {
    resetStoryQueue();
    globalThis.fetch = async () => new Response(JSON.stringify({
      status: "ready",
      text: "On vient d’entrer dans la ZEE espagnole. Ports d’entrée : Palma.",
      engine: "nvidia-gpt-oss-20b",
      cascade: "nim-or-claude",
      tavily: null,
      nvidia: "nvidia-gpt-oss-20b",
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  });

  afterEach(() => {
    globalThis.fetch = origFetch;
    resetStoryQueue();
  });

  it("returns pending immediately and becomes ready without blocking", async () => {
    const first = enqueueStory({
      event: "zee-enter",
      eventId: "zee-enter:1",
      tavily: null,
      nvidia: null,
    });
    assert.equal(first.status, "pending");
    assert.equal(first.cascade, "nim-or-claude");
    assert.equal(first.tavily, null);
    assert.equal(first.nvidia, null);
    const ready = await waitJob("zee-enter:1", "ready");
    assert.match(ready.text, /ZEE/);
    assert.equal(ready.tavily, null);
    assert.equal(ready.nvidia, "nvidia-gpt-oss-20b");
  });

  it("does not open a fourth later job when three are pending", () => {
    globalThis.fetch = (_url, opts) => new Promise((_, reject) => {
      opts?.signal?.addEventListener("abort", () => {
        const err = new Error("aborted");
        err.name = "AbortError";
        reject(err);
      });
    });
    enqueueStory({ event: "zee-ahead", eventId: "a", type: "zee-ahead" });
    enqueueStory({ event: "amp-ahead", eventId: "b", type: "amp-ahead" });
    enqueueStory({ event: "poe-ahead", eventId: "c", type: "poe-ahead" });
    const fourth = enqueueStory({ event: "wind-shift", eventId: "d", type: "wind-shift" });
    assert.equal(fourth.status, "pending");
    assert.ok(pendingStoryCount() <= MAX_STORY_PENDING);
    const marina = enqueueStory({ event: "marina-refuge", eventId: "e", type: "marina-refuge" });
    assert.equal(marina.status, "pending");
    assert.ok(pendingStoryCount() <= MAX_STORY_PENDING);
    assert.ok(KEEP_STORY_TYPES.includes("marina-refuge"));
  });
});
