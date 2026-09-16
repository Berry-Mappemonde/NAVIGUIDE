import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const read = (rel) => readFileSync(join(root, rel), "utf8");

describe("recette A–G (contrats source)", () => {
  it("A — bateau et drapeaux sur la même lon enveloppée que la caméra", () => {
    assert.match(read("../components/CatamaranMarker.jsx"), /markerWorldLngs/);
    assert.match(read("../components/PlaneMarker.jsx"), /markerWorldLngs/);
    assert.match(read("../App.jsx"), /shouldResnapCamera/);
    assert.match(read("../App.jsx"), /markerWorldLngs/);
    assert.match(read("../hooks/useFilmCamera.js"), /cameraLngForBoat/);
    assert.doesNotMatch(read("../hooks/useFilmCamera.js"), /unwrapLon/);
    assert.match(read("../hooks/useSimulatorMap.js"), /worldCopyJump:\s*false/);
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

  it("E — GRIB2 branché, même lon enveloppée que le bateau", () => {
    const app = read("../App.jsx");
    assert.match(app, /maritimeLayers\.showGrib && isSuivre/);
    assert.match(read("../layers/useToggleLayers.js"), /DEFAULT_SHOW_GRIB/);
    const grib = read("../layers/useGribCorridorLayer.js");
    assert.match(grib, /markerWorldLngs/);
    assert.match(grib, /cameraLngForBoat/);
    assert.match(grib, /getPane\("grib"\)/);
    assert.doesNotMatch(grib, /getPane\("boat"\)/);
    assert.match(read("../layers/layerOrder.js"), /name:\s*"grib"/);
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

  it("H — GRIB sous le bateau, catamaran SVG proue = cap", () => {
    const icon = read("../engine/catamaranIcon.js");
    const marker = read("../components/CatamaranMarker.jsx");
    assert.match(icon, /data-bow="north"/);
    assert.match(icon, /rotate\(\$\{/);
    assert.match(marker, /catamaranSvg/);
    assert.doesNotMatch(marker, /catamaran\.jpg/);
    assert.doesNotMatch(icon, /scaleX/);
  });
});
