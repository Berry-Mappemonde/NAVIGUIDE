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
    const official = read("../hooks/useOfficialExpedition.js");
    assert.match(official, /officialGribQuery\(serverClock/);
    assert.doesNotMatch(official, /sampleClockAtTime\(clockRef/);
    assert.match(read("../hooks/gribStatus.js"), /wrapLon\(sample\.lon\)/);
    assert.match(read("../main.jsx"), /Icon\.Default\.mergeOptions/);
    assert.match(read("./getCardinalDirection.js"), /typeof input === "number"/);
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

  it("I — atlas climatologie peint + moteur, distinct du GRIB2", () => {
    const app = read("../App.jsx");
    assert.match(app, /useClimatologyLayer/);
    assert.match(app, /useAtlasLookup/);
    assert.match(app, /climatology-banner/);
    assert.doesNotMatch(app, /overlay climatologie à l’étape 6/);
    assert.match(read("../layers/useToggleLayers.js"), /showClimoWind/);
    assert.match(read("../layers/useToggleLayers.js"), /showClimoWave/);
    assert.match(read("../layers/useToggleLayers.js"), /showClimoCurrent/);
    assert.match(read("../layers/useToggleLayers.js"), /showClimoCyclones/);
    assert.match(read("../layers/useClimatologyLayer.js"), /waveP50/);
    assert.match(read("../layers/useClimatologyLayer.js"), /waveP90/);
    assert.match(read("../layers/useClimatologyLayer.js"), /wave-mean/);
    assert.match(read("../layers/useClimatologyLayer.js"), /cyclones/);
    assert.match(read("../layers/useClimatologyLayer.js"), /climoPointLngs/);
    assert.match(read("../layers/useClimatologyLayer.js"), /cycloneLatLngCopies/);
    assert.match(read("../layers/useClimatologyLayer.js"), /groupCycloneFeatures/);
    assert.match(read("../layers/climatologyWorld.js"), /unwrapCycloneCoords/);
    assert.doesNotMatch(read("../layers/climatologyWorld.js"), /splitCycloneAtMeridian/);
    assert.match(read("../../../frontend/src/components/map/cycloneTracks.js"), /unwrapCycloneCoords/);
    assert.doesNotMatch(read("../../../frontend/src/components/map/cycloneTracks.js"), /splitCycloneAtMeridian/);
    assert.match(read("../../../frontend/src/components/map/useClimatologyLayer.js"), /cycloneLatLngCopies/);
    assert.match(read("../../../frontend/src/components/map/useClimatologyLayer.js"), /groupCycloneFeatures/);
    assert.match(read("../layers/layerOrder.js"), /climatology-raster/);
    assert.match(read("../utils/atlasPoint.js"), /kind !== "climatology"/);
    assert.match(read("../engine/voyageClock.js"), /windAt/);
    assert.match(read("../engine/ici.js"), /climatology: null/);
    assert.match(read("../engine/iciBriefing.js"), /kind climatology/);
    assert.match(read("../hooks/useIciDossier.js"), /dest_lat/);
    const grib = read("../layers/useGribCorridorLayer.js");
    assert.match(grib, /status !== "ready"/);
    assert.doesNotMatch(grib, /climatology\/point/);
  });
});
