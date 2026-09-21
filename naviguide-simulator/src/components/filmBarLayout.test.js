import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { FILM_BAR_HEIGHT_PX } from "../utils/filmBarLayout.js";

const here = dirname(fileURLToPath(import.meta.url));
const bar = readFileSync(join(here, "SimulationFilmBar.jsx"), "utf8");
const app = readFileSync(join(here, "../App.jsx"), "utf8");

function firstIndex(src, pattern) {
  const m = src.match(pattern);
  assert.ok(m, `motif introuvable : ${pattern}`);
  return m.index;
}

describe("film bar layout (lot O)", () => {
  it("a une seule ListenButton, plus de replay-voice, testids conservés", () => {
    const listens = bar.match(/<ListenButton/g) || [];
    assert.equal(listens.length, 1, "un seul ListenButton dans la barre");
    assert.doesNotMatch(bar, /data-testid="replay-voice"/);
    assert.doesNotMatch(bar, /🔊/);
    assert.match(bar, /testId="listen"/);
    assert.match(bar, /data-testid="replay-start"/);
    assert.match(bar, /data-testid="replay-stop"/);
    assert.match(bar, /"view-suivre"/);
    assert.match(bar, /"view-simulation"/);
    assert.match(bar, /"mode-follow"/);
    assert.match(bar, /"mode-sim"/);
    assert.match(bar, /data-testid="film-commands"/);
    assert.match(bar, /data-testid="film-subtitle"/);
    assert.match(bar, /data-testid="film-duration"/);
    assert.match(bar, /data-testid="film-source"/);
    assert.match(bar, /data-testid="film-style"/);
    assert.match(bar, /data-testid="film-fullscreen"/);
  });

  it("range les commandes : Masquer · Cinéma · Écouter · Suivre/Simulation · Revoir, lecture à droite", () => {
    const hideAt = firstIndex(bar, /t\("hideFilmBar"\)/);
    const cinemaAt = firstIndex(bar, /t\("cinema"\)/);
    const listenAt = firstIndex(bar, /testId="listen"/);
    const viewAt = firstIndex(bar, /data-testid="film-view-switch"/);
    const replayAt = firstIndex(bar, /data-testid="replay-controls"/);
    const playAt = firstIndex(bar, /onClick=\{onTogglePlay\}/);
    const speedsAt = firstIndex(bar, /\{PROFILES\.map/);
    assert.ok(hideAt < cinemaAt, "Masquer avant Cinéma");
    assert.ok(cinemaAt < listenAt, "Cinéma avant Écouter");
    assert.ok(listenAt < viewAt, "Écouter avant le commutateur de vue");
    assert.ok(viewAt < replayAt, "commutateur avant Revoir");
    assert.ok(replayAt < playAt, "Revoir à gauche, lecture à droite");
    assert.ok(playAt < speedsAt, "vitesses à droite, pilules text-[9px]");
    assert.match(bar, /rounded-md text-\[9px\] font-semibold border whitespace-nowrap/);
  });

  it("garde les commandes existantes hors le doublon son", () => {
    assert.match(bar, /t\("cinema"\)/);
    assert.match(bar, /t\("hideFilmBar"\)/);
    assert.match(bar, /t\("goToNextStop"\)/);
    assert.match(bar, /data-testid="stop-auto"/);
    assert.match(bar, /PROFILES\.map/);
    assert.match(bar, /onCinema/);
    assert.match(bar, /onFilmFullscreen/);
    assert.match(bar, /t\("filmFullscreen"\)/);
  });
});

describe("film bar (lot R2)", () => {
  it("n’a plus de légende des régimes, un prev-stop, hauteur contrat ≤ 96 px", () => {
    assert.doesNotMatch(bar, /t\("regimeLegend"\)/);
    assert.doesNotMatch(bar, /REGIME_COLORS/);
    assert.match(bar, /data-testid="regime-legend"/);
    assert.doesNotMatch(bar, /className="sr-only"/);
    assert.match(bar, /aria-label=\{regimeTitle\}/);
    assert.match(bar, /data-testid="prev-stop"/);
    assert.match(bar, /t\("previousEscale"\)/);
    assert.match(bar, /data-testid="speed-regime-pill"/);
    assert.match(bar, /regimeTooltipHindcast/);
    const prevAt = firstIndex(bar, /data-testid="prev-stop"/);
    const nextAt = firstIndex(bar, /t\("goToNextStop"\)/);
    assert.ok(prevAt < nextAt, "Escale précédente à gauche de Prochaine escale");
    assert.ok(FILM_BAR_HEIGHT_PX.compact <= 96);
    assert.ok(FILM_BAR_HEIGHT_PX.controls <= 96);
  });

  it("montre Masquer la barre dès que onHideBar est fourni, Cinéma ou non", () => {
    assert.doesNotMatch(bar, /cinema && onHideBar/);
    assert.match(bar, /\{onHideBar \? \(/);
    assert.match(bar, /data-testid="hide-film-bar"/);
    assert.match(bar, /data-testid="show-film-bar"/);
    assert.match(app, /hideBar=\{hideFilmBar\}/);
    assert.doesNotMatch(app, /hideBar=\{cinemaMode && hideFilmBar\}/);
    assert.match(app, /onPrev=\{handleSimPrev\}/);
    assert.match(app, /canPrev=\{canPrevEscale/);
  });
});

describe("film bar (lot RA6)", () => {
  it("info-bulle hindcast/prévision/climatologie sur la pilule, Suivre comme Simulation", () => {
    assert.match(bar, /title=\{regimeTitle\}/);
    assert.match(bar, /data-testid="speed-regime-pill" title=\{regimeTitle\}/);
    assert.match(bar, /regimeTooltipHindcast/);
    assert.match(bar, /regimeTooltipForecast/);
    assert.match(bar, /regimeTooltipClimatology/);
    assert.doesNotMatch(bar, /showPlaybackControls\s*\?\s*regimeTitle/);
    assert.doesNotMatch(bar, /isSimulation[\s\S]{0,40}regimeTitle/);
  });

  it("jambe terrestre en km par la route dans la barre", () => {
    assert.match(bar, /formatLandLegClock/);
    assert.match(bar, /isLandLegNames/);
    assert.match(bar, /data-testid="film-land-leg"/);
    assert.match(bar, /unitKm/);
    assert.match(bar, /byRoad/);
    assert.match(bar, /unitRoadHours/);
  });
});

describe("plein écran film (lot F5) — sidebars masquées, pas démontées", () => {
  it("App pose .film-fullscreen et garde <Sidebar> / <ToolsSidebar> montés", () => {
    assert.match(app, /film-fullscreen/);
    assert.match(app, /setFilmFullscreen/);
    assert.match(app, /<Sidebar[\s\S]*open=\{sidebarOpen\}/);
    assert.match(app, /<ToolsSidebar[\s\S]*open=\{toolsOpen\}/);
    assert.doesNotMatch(app, /\{[^}]*filmFullscreen[^}]*&&\s*<Sidebar/);
    assert.doesNotMatch(app, /\{[^}]*!filmFullscreen[^}]*&&\s*<Sidebar/);
  });
});
