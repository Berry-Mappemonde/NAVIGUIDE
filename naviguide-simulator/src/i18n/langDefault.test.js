import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readStoredLang, STORAGE_KEY } from "./langStorage.js";

describe("default language", () => {
  it("is French when no key is stored", () => {
    const mem = { getItem: () => null };
    assert.equal(readStoredLang(mem), "fr");
  });

  it("respects a language already chosen", () => {
    const mem = { getItem: (k) => (k === STORAGE_KEY ? "en" : null) };
    assert.equal(readStoredLang(mem), "en");
  });
});
