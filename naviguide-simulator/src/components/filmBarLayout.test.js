import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const bar = readFileSync(join(here, "SimulationFilmBar.jsx"), "utf8");

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
  });
});
