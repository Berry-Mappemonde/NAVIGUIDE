import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const app = readFileSync(join(here, "..", "App.jsx"), "utf8");

describe("openEscaleFromUi — pas d'ouverture de panneau (lot RD1)", () => {
  it("n'appelle plus setSidebarOpen", () => {
    const start = app.indexOf("const openEscaleFromUi");
    const end = app.indexOf("const replayControls");
    assert.ok(start >= 0 && end > start, "openEscaleFromUi introuvable");
    const block = app.slice(start, end);
    assert.match(block, /openEscaleSheet\(next\)/);
    assert.doesNotMatch(block, /setSidebarOpen/);
  });

  it("un escaleStop ne rouvre plus le panneau gauche", () => {
    assert.doesNotMatch(app, /if \(escaleStop && !replay\.active\) setSidebarOpen\(true\)/);
  });
});
