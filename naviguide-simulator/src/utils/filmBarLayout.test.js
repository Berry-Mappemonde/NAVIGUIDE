import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  ATTRIBUTION_FILM_GAP_PX,
  FILM_BAR_BOTTOM_GAP_PX,
  FILM_BAR_HEIGHT_PX,
  SIDEBAR_WIDTH_PX,
  filmBarInsets,
  mapInsetVars,
  measureFilmBarOccupiedPx,
} from "./filmBarLayout.js";

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
  it("se décale du panneau Outils ; premier rendu = constantes + 4 px (lot UI1)", () => {
    const vars = mapInsetVars({ sidebarOpen: true, toolsOpen: true, filmBarVisible: true, filmBarControls: true });
    assert.equal(vars["--sim-inset-right"], `${SIDEBAR_WIDTH_PX}px`);
    assert.equal(
      vars["--sim-inset-bottom"],
      `${FILM_BAR_HEIGHT_PX.controls + FILM_BAR_BOTTOM_GAP_PX + ATTRIBUTION_FILM_GAP_PX}px`,
    );
  });

  it("Suivre : même plancher de premier rendu ; barre invisible : rien", () => {
    const suivre = mapInsetVars({ toolsOpen: false, filmBarVisible: true, filmBarControls: false });
    assert.equal(suivre["--sim-inset-right"], "0px");
    assert.equal(
      suivre["--sim-inset-bottom"],
      `${FILM_BAR_HEIGHT_PX.compact + FILM_BAR_BOTTOM_GAP_PX + ATTRIBUTION_FILM_GAP_PX}px`,
    );
    const hidden = mapInsetVars({ toolsOpen: false, filmBarVisible: false });
    assert.equal(hidden["--sim-inset-bottom"], "0px");
  });

  it("inset = mesure + 4 (lot UI1)", () => {
    const tall = mapInsetVars({ filmBarVisible: true, filmBarMeasuredPx: 140 });
    assert.equal(tall["--sim-inset-bottom"], `${140 + ATTRIBUTION_FILM_GAP_PX}px`);
    const chip = mapInsetVars({ filmBarVisible: true, filmBarMeasuredPx: 44 });
    assert.equal(chip["--sim-inset-bottom"], `${44 + ATTRIBUTION_FILM_GAP_PX}px`);
    assert.equal(ATTRIBUTION_FILM_GAP_PX, 4);
  });

  it("mesure l’occupation depuis le bas jusqu’au haut de la barre", () => {
    const el = { getBoundingClientRect: () => ({ top: 680, bottom: 780 }) };
    assert.equal(measureFilmBarOccupiedPx(el, 800), 120);
    assert.equal(measureFilmBarOccupiedPx(null, 800), 0);
  });
});
