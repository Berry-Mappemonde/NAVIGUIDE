import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const read = (rel) => readFileSync(join(root, rel), "utf8");

describe("recette A–G (contrats source)", () => {
  it("A — bateau et drapeaux sur worldCopyLngs", () => {
    assert.match(read("../components/CatamaranMarker.jsx"), /worldCopyLngs/);
    assert.match(read("../components/PlaneMarker.jsx"), /worldCopyLngs/);
    assert.match(read("../App.jsx"), /worldCopyLngs/);
  });

  it("C — plus d’ArrivalCard ni d’effect banner", () => {
    const app = read("../App.jsx");
    assert.doesNotMatch(app, /ArrivalCard/);
    assert.doesNotMatch(app, /arrivalBanner/);
    assert.doesNotMatch(app, /setArrivalBanner/);
  });

  it("D — KeyC ignore meta/ctrl", () => {
    const app = read("../App.jsx");
    assert.match(app, /isCinemaKey/);
    assert.match(read("./cinemaHotkey.js"), /metaKey \|\| e\.ctrlKey/);
  });

  it("E — GRIB2 branché, pas allumé en dur hors config", () => {
    const app = read("../App.jsx");
    assert.match(app, /maritimeLayers\.showGrib && isSuivre/);
    assert.match(read("../layers/useToggleLayers.js"), /DEFAULT_SHOW_GRIB/);
  });

  it("F — Annuler Draw + bateau après 1er segment", () => {
    const app = read("../App.jsx");
    assert.match(app, /handleDrawCancel/);
    assert.match(app, /drawnSegments\.length >= 1/);
    assert.match(read("../components/Sidebar.jsx"), /onDrawCancel/);
  });

  it("G — Open-Meteo une fois, jambe sans modèle", () => {
    const panel = read("../components/SimulationPanel.jsx");
    assert.doesNotMatch(panel, /forecastModel/);
    assert.doesNotMatch(panel, /clockSample\.model/);
    assert.doesNotMatch(panel, /Open-Meteo/);
    assert.match(read("../App.jsx"), /buildWeatherLine\(/);
    assert.match(read("../components/SimulationFilmBar.jsx"), /weather-line/);
  });
});
