import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { getDemoSteps } from "./demoWalkthrough.js";

describe("judges walkthrough", () => {
  it("keeps a stable sequence that covers live follow, logbook, layers, replay, and route drawing", () => {
    for (const lang of ["en", "fr"]) {
      const steps = getDemoSteps(lang, false);
      assert.deepEqual(steps.map((step) => step.id), [
        "welcome", "live", "briefing", "layers", "replay", "trace", "return",
      ]);
      assert.equal(new Set(steps.map((step) => step.action)).size, steps.length);
    }
  });

  it("does not promise a fabricated film when the official film is unavailable", () => {
    const unavailable = getDemoSteps("en", false).find((step) => step.id === "replay");
    const ready = getDemoSteps("en", true).find((step) => step.id === "replay");
    assert.match(unavailable.body, /not ready/i);
    assert.match(unavailable.body, /fake demo/i);
    assert.match(ready.body, /official film is ready/i);
  });

  it("provides French copy for every step", () => {
    const steps = getDemoSteps("fr", true);
    assert.ok(steps.every((step) => step.title.length > 0 && step.body.length > 0));
    assert.match(steps.find((step) => step.id === "trace").body, /mode Tracer/i);
  });
});
