import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { isCinemaKey } from "./cinemaHotkey.js";

describe("isCinemaKey", () => {
  it("C seule allume le cinéma", () => {
    assert.equal(isCinemaKey({ code: "KeyC", metaKey: false, ctrlKey: false }), true);
  });

  it("ignore ⌘C et Ctrl+C (Copier)", () => {
    assert.equal(isCinemaKey({ code: "KeyC", metaKey: true, ctrlKey: false }), false);
    assert.equal(isCinemaKey({ code: "KeyC", metaKey: false, ctrlKey: true }), false);
  });

  it("ignore les autres touches", () => {
    assert.equal(isCinemaKey({ code: "KeyL", metaKey: false, ctrlKey: false }), false);
    assert.equal(isCinemaKey(null), false);
  });
});
