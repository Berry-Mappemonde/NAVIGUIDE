import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { FILM_GLIDE_MS, filmGlideStep, followJumpNm } from "./filmGlide.js";
import { castAtClock, clockAirEpisodes, clockVertices } from "./clockCast.js";
import { haversineNm } from "../utils/geo.js";

const here = dirname(fileURLToPath(import.meta.url));
const EPISODE = JSON.parse(readFileSync(
  join(here, "..", "..", "server", "tests", "fixtures", "film_reread_20261027", "fixture-clock-episode.json"),
  "utf8",
));
const H = 3600000;

// Panamá → Papeete, les deux sommets que le film de prod (28/10) enjambait :
// fin du chapitre leg-13 (9.79, -79.88) puis tA de leg-14 à Papeete.
const PACIFIC = {
  t0: "2026-05-15T08:00:00Z",
  vertices: [
    { lat: 9.79, lon: -79.88, tHours: 2600, vehicle: "main", filmNm: 15000, sailNm: 15000 },
    { lat: 8.5, lon: -90, tHours: 2700, vehicle: "main", filmNm: 15600, sailNm: 15600 },
    { lat: -17.5, lon: -149.57, tHours: 3600, vehicle: "main", filmNm: 19400, sailNm: 19400 },
  ],
};
const T = (clock, h) => Date.parse(clock.t0) + h * H;

/** Rejoue la boucle du lecteur : la demande saute à `jumpTo` à la première image. */
function play(clock, fromT, jumpTo, frames = 200, frameMs = 16) {
  let state = null;
  let shown = fromT;
  const out = [];
  for (let i = 0; i < frames; i++) {
    const now = 1000 + i * frameMs;
    const step = filmGlideStep(state, { fromT: shown, toT: jumpTo, nowMs: now, clock });
    state = step.state;
    shown = step.t;
    out.push({ t: shown, cast: castAtClock(clock, shown) });
  }
  return out;
}

const pos = (c) => c.follow;
const gap = (a, b) => haversineNm(a.lat, a.lon, b.lat, b.lon);

describe("filmGlideStep — raccord de chapitre sans téléportation", () => {
  it("Panamá → Papeete : le bateau traverse au lieu de sauter", () => {
    const from = T(PACIFIC, 2600);
    const to = T(PACIFIC, 3600);
    assert.ok(followJumpNm(PACIFIC, from, to) > 4000, "le saut brut fait plus de 4 000 milles");
    const rows = play(PACIFIC, from, to);
    for (let i = 1; i < rows.length; i++) {
      const d = gap(pos(rows[i - 1].cast), pos(rows[i].cast));
      assert.ok(d < 150, `image ${i} : ${d.toFixed(0)} milles d'un coup`);
    }
    assert.equal(rows.at(-1).t, to, "la glisse arrive à tA du chapitre suivant");
    const mid = rows[Math.round(FILM_GLIDE_MS / 16 / 2)].cast.main;
    assert.ok(mid.lon < -90 && mid.lon > -149, `à mi-glisse le bateau est en plein Pacifique (${mid.lon})`);
  });

  it("SPM : B ne saute plus de 45 N 55 W à Saint-Pierre au changement de chapitre", () => {
    // Film de prod (28/10), leg-8 → leg-10 : 113 milles en une image (horloge rangée avant le correctif).
    const clock = {
      t0: "2026-05-15T08:00:00Z",
      vertices: [
        { lat: 45, lon: -55, tHours: 100, vehicle: "main", filmNm: 0, sailNm: 0 },
        { lat: 46.776, lon: -56.163, tHours: 110, vehicle: "main", filmNm: 113, sailNm: 113 },
      ],
    };
    const rows = play(clock, T(clock, 100), T(clock, 110), 40);
    for (let i = 1; i < rows.length; i++) {
      assert.ok(gap(pos(rows[i - 1].cast), pos(rows[i].cast)) < 30, `image ${i}`);
    }
    assert.equal(rows.at(-1).t, T(clock, 110));
  });

  it("un pas ordinaire passe tel quel", () => {
    const from = T(PACIFIC, 2600);
    const to = from + 2 * H;
    const step = filmGlideStep(null, { fromT: from, toT: to, nowMs: 0, clock: PACIFIC });
    assert.equal(step.t, to);
    assert.equal(step.state, null);
  });

  it("un retour en arrière (Stop, relance) lâche la glisse", () => {
    const from = T(PACIFIC, 2600);
    const first = filmGlideStep(null, { fromT: from, toT: T(PACIFIC, 3600), nowMs: 0, clock: PACIFIC });
    assert.ok(first.state);
    const back = filmGlideStep(first.state, { fromT: from, toT: from - H, nowMs: 16, clock: PACIFIC });
    assert.equal(back.t, from - H);
    assert.equal(back.state, null);
  });

  it("Cayenne → Halifax en une image : l'avion vole, A reste à Cayenne, B part de Halifax", () => {
    const verts = clockVertices(EPISODE);
    const [ep] = clockAirEpisodes(verts);
    const at = (v) => Date.parse(EPISODE.t0) + v.tHours * H;
    const from = at(verts[ep.out - 1]) - 2 * H; // A à quai, juste avant le vol
    const to = at(verts[ep.out]) + 96 * H; // B en route, quatre jours après Halifax
    const rows = play(EPISODE, from, to);
    const flying = rows.filter((r) => r.cast.plane.visible).length;
    assert.ok(flying >= 20, `l'avion est vu pendant le raccord (${flying} images)`);
    for (const r of rows) {
      assert.ok(gap(r.cast.main, { lat: 4.9333, lon: -52.3533 }) < 1, "A ne quitte pas Cayenne");
    }
    for (let i = 1; i < rows.length; i++) {
      assert.ok(gap(pos(rows[i - 1].cast), pos(rows[i].cast)) < 150, `image ${i} : saut de la caméra`);
    }
    const firstB = rows.find((r) => r.cast.side.visible);
    assert.ok(firstB && gap(firstB.cast.side, { lat: 44.656, lon: -63.562 }) < 5, "B apparaît à Halifax");
  });
});
