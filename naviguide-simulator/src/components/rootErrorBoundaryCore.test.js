import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { RootErrorBoundary, ROOT_ERROR_COPY, pickErrorLanguage, shouldReloadAfterPreloadError } from "./rootErrorBoundaryCore.js";

describe("root error boundary recovery", () => {
  it("getDerivedStateFromError stores the render error", () => {
    const error = new Error("broken");
    assert.deepEqual(RootErrorBoundary.getDerivedStateFromError(error), { error });
  });

  it("selects localized copy from the app language storage key", () => {
    const storage = (lang) => ({ getItem: (key) => key === "naviguide_lang_v4" ? lang : null });
    assert.equal(ROOT_ERROR_COPY[pickErrorLanguage(storage("fr"))].reload, "Recharger");
    assert.equal(ROOT_ERROR_COPY[pickErrorLanguage(storage("en"))].reload, "Reload");
  });

  it("reloads after a preload error only once per session", () => {
    const values = new Map();
    const storage = { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) };
    assert.equal(shouldReloadAfterPreloadError(storage), true);
    assert.equal(shouldReloadAfterPreloadError(storage), false);
  });
});
