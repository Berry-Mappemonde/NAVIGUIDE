import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { SIDEBAR_WIDTH_PX, filmBarInsets } from "./filmBarLayout.js";

describe("filmBarLayout U6", () => {
  it("entre les deux sidebars ouvertes", () => {
    const box = filmBarInsets({ sidebarOpen: true, toolsOpen: true });
    assert.equal(box.left, SIDEBAR_WIDTH_PX);
    assert.equal(box.right, SIDEBAR_WIDTH_PX);
  });

  it("s’élargit si une sidebar se range", () => {
    const cinema = filmBarInsets({ sidebarOpen: false, toolsOpen: false, gutter: 8 });
    assert.equal(cinema.left, 8);
    assert.equal(cinema.right, 8);
    const leftOnly = filmBarInsets({ sidebarOpen: true, toolsOpen: false, gutter: 8 });
    assert.equal(leftOnly.left, SIDEBAR_WIDTH_PX);
    assert.equal(leftOnly.right, 8);
  });
});
