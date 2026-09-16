import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it } from "node:test";
import assert from "node:assert/strict";

const src = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFileSync(join(src, path), "utf8");

describe("contrat UI produit", () => {
  it("démarre en Simulation sur la vue monde sans recadrage initial", () => {
    const app = read("../App.jsx");
    const map = read("../hooks/useSimulatorMap.js");
    assert.match(app, /useState\(VIEW_SIMULATION\)/);
    assert.match(map, /zoom:\s*2/);
    assert.doesNotMatch(app, /map\.setView\(\[start\.lat,\s*start\.lon\],\s*8/);
  });

  it("utilise les PNG validés et le favicon d’origine", () => {
    const sidebar = read("../components/Sidebar.jsx");
    const index = read("../../index.html");
    assert.match(sidebar, /const NAVIGUIDE_LOGO = "\/logo-naviguide\.png"/);
    assert.match(sidebar, /const BERRY_LOGO = "\/logo-berry-mappemonde\.png"/);
    assert.match(index, /href="\/favicon-n-bl\.png"/);
    assert.ok(existsSync(join(src, "../../public/logo-naviguide.png")));
    assert.ok(existsSync(join(src, "../../public/logo-berry-mappemonde.png")));
    assert.ok(existsSync(join(src, "../../public/favicon-n-bl.png")));
  });

  it("réserve les contrôles de lecture et les sauts à Simulation", () => {
    const app = read("../App.jsx");
    const filmBar = read("../components/SimulationFilmBar.jsx");
    const sidebar = read("../components/Sidebar.jsx");
    assert.match(app, /showPlaybackControls=\{isSimulation\}/);
    assert.match(app, /if \(!isSimulation\) return;/);
    assert.match(filmBar, /disabled=\{!showPlaybackControls\}/);
    assert.match(sidebar, /showNavigation=\{isSimulation\}/);
  });

  it("entre en Suivre directement en LIVE cinéma", () => {
    const app = read("../App.jsx");
    assert.match(app, /if \(next === VIEW_SUIVRE\)/);
    assert.match(app, /setUserPreview\(false\)/);
    assert.match(app, /setCinemaMode\(true\)/);
    assert.match(app, /recaptureBoat\(\)/);
  });

  it("garde Saint-Maur en interne, sans choix de départ visible", () => {
    const app = read("../App.jsx");
    const departure = read("../components/DepartureField.jsx");
    assert.match(app, /voyage\.setStartAt\("saint-maur"\)/);
    assert.doesNotMatch(departure, /type="radio"/);
  });

  it("n’affiche un titre de briefing que si briefing_title est fourni", () => {
    const sidebar = read("../components/Sidebar.jsx");
    assert.match(sidebar, /plan\?\.briefing_title/);
    assert.doesNotMatch(sidebar, /t\("briefing"\)/);
  });
});
