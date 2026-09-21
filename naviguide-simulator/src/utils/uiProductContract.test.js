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
    const simulationPanel = read("../components/SimulationPanel.jsx");
    assert.match(app, /showPlaybackControls=\{isSimulation\}/);
    assert.match(app, /if \(!isSimulation\) return;/);
    assert.match(filmBar, /disabled=\{!showPlaybackControls\}/);
    assert.match(filmBar, /goToNextStop/);
    assert.doesNotMatch(sidebar, /onNext=\{handleSimNext\}/);
    assert.doesNotMatch(simulationPanel, /PrevNextButtons/);
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

  it("compacte le départ en format français avec une heure éditable", () => {
    const departure = read("../components/DepartureField.jsx");
    assert.match(departure, /naviguide-departure-field h-\[46px\]/);
    assert.match(departure, /formatDepartureDate/);
    assert.match(departure, /parseFrenchDepartureDate/);
    assert.match(departure, /placeholder="HH:MM"/);
    assert.doesNotMatch(departure, /type="date"/);
  });

  it("garde LIVE une seule fois dans le HUD et la météo sur la même ligne", () => {
    const app = read("../App.jsx");
    const filmBar = read("../components/SimulationFilmBar.jsx");
    const simulationPanel = read("../components/SimulationPanel.jsx");
    assert.match(app, /liveStatus=\{isSuivre/);
    assert.match(filmBar, /<span data-testid="weather-line" className="text-cyan-200\/85">/);
    assert.doesNotMatch(simulationPanel, /bg-emerald-500\/20/);
  });

  it("dégage le zoom Leaflet et aligne les deux chevrons", () => {
    const sidebar = read("../components/Sidebar.jsx");
    const tools = read("../components/ToolsSidebar.jsx");
    assert.match(sidebar, /naviguide-sidebar-toggle--left/);
    assert.match(sidebar, /top-\[92px\]/);
    assert.match(tools, /naviguide-sidebar-toggle--right/);
    assert.match(tools, /w-9 h-9/);
    assert.doesNotMatch(tools, /w-12 h-12/);
  });

  it("retire la mention non éditable et la date répétée de la jambe", () => {
    const app = read("../App.jsx");
    const panel = read("../components/SimulationPanel.jsx");
    const fr = read("../i18n/fr.js");
    assert.doesNotMatch(app, /civilDate=/);
    assert.doesNotMatch(panel, /civilDate/);
    assert.doesNotMatch(fr, /non éditable/);
  });

  it("n’affiche un titre de briefing que si briefing_title est fourni", () => {
    const sidebar = read("../components/Sidebar.jsx");
    assert.match(sidebar, /plan\?\.briefing_title/);
    assert.doesNotMatch(sidebar, /t\("briefing"\)/);
  });

  it("lot C3 : barre film et contexte du chat lisent la même source", () => {
    const app = read("../App.jsx");
    const bar = read("../components/SimulationFilmBar.jsx");
    assert.match(app, /const displayKnots = isSuivre/);
    assert.match(app, /boatKnots=\{displayKnots\}/);
    assert.match(app, /speedKnots: Number\.isFinite\(displayKnots\) \? displayKnots : null/);
    assert.match(app, /follow: isSuivre/);
    assert.match(app, /window\.__naviguideDebug/);
    assert.match(bar, /data-testid="regime-legend"/);
    assert.doesNotMatch(app, /boatKnots=\{expeditionSpeed\.knots\}/);
    assert.doesNotMatch(app, /chatMeasuredKnots = atQuay \? 0 : expeditionSpeed\.knots/);
  });
});
