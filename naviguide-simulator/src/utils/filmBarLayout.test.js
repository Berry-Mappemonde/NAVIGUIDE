import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { FILM_BAR_HEIGHT_PX, SIDEBAR_WIDTH_PX, filmBarInsets, mapInsetVars } from "./filmBarLayout.js";

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

describe("mapInsetVars — crédits Leaflet dans la carte visible", () => {
  it("se décale du panneau Outils et de la barre film (Simulation)", () => {
    const vars = mapInsetVars({ sidebarOpen: true, toolsOpen: true, filmBarVisible: true, filmBarControls: true });
    assert.equal(vars["--sim-inset-right"], `${SIDEBAR_WIDTH_PX}px`);
    assert.equal(vars["--sim-inset-bottom"], `${FILM_BAR_HEIGHT_PX.controls}px`);
  });

  it("Suivre : barre plus basse ; Cinéma barre cachée : rien", () => {
    const suivre = mapInsetVars({ toolsOpen: false, filmBarVisible: true, filmBarControls: false });
    assert.equal(suivre["--sim-inset-right"], "0px");
    assert.equal(suivre["--sim-inset-bottom"], `${FILM_BAR_HEIGHT_PX.compact}px`);
    const hidden = mapInsetVars({ toolsOpen: false, filmBarVisible: false });
    assert.equal(hidden["--sim-inset-bottom"], "0px");
  });
});
