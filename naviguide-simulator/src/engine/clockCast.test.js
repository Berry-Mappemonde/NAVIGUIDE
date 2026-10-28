import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { castAtClock, clockAirEpisodes, clockVertices, pickSceneCast } from "./clockCast.js";
import { positionAt } from "./replay.js";
import { haversineNm } from "../utils/geo.js";

const here = dirname(fileURLToPath(import.meta.url));
// Horloge de production (GET 27/10), sommets 2040–2340 : tout l'épisode Guyane.
const CLOCK = JSON.parse(readFileSync(
  join(here, "..", "..", "server", "tests", "fixtures", "film_reread_20261027", "fixture-clock-episode.json"),
  "utf8",
));
const CAYENNE = { lat: 4.9333, lon: -52.3533 };
const HALIFAX = { lat: 44.656, lon: -63.562 };
const T0 = Date.parse(CLOCK.t0);
const H = 3600000;
const STEP_H = 1 / 6;

const nm = (a, b) => haversineNm(a.lat, a.lon, b.lat, b.lon);
const at = (v) => T0 + v.tHours * H;

function samples() {
  const v = clockVertices(CLOCK);
  const out = [];
  for (let t = at(v[0]); t <= at(v[v.length - 1]); t += STEP_H * H) out.push({ t, cast: castAtClock(CLOCK, t) });
  return out;
}

describe("castAtClock — deux bateaux, un avion, horloge de production", () => {
  const verts = clockVertices(CLOCK);
  const [ep] = clockAirEpisodes(verts);
  const tOut0 = at(verts[ep.out - 1]);
  const tOut1 = at(verts[ep.out]);
  const tRet0 = at(verts[ep.ret - 1]);
  const tRet1 = at(verts[ep.ret]);
  const rows = samples();

  it("trouve un seul épisode Cayenne → Halifax … Halifax → Cayenne", () => {
    assert.equal(clockAirEpisodes(verts).length, 1);
    assert.ok(nm(ep.park, CAYENNE) < 2);
    assert.ok(nm(ep.hub, HALIFAX) < 2);
  });

  it("aucun acteur ne fait de saut invraisemblable", () => {
    const limits = { main: 25, side: 25, plane: 650 };
    for (let i = 1; i < rows.length; i++) {
      for (const who of ["main", "side", "plane"]) {
        const a = rows[i - 1].cast[who];
        const b = rows[i].cast[who];
        if (!a.visible || !b.visible) continue;
        const d = nm(a, b);
        assert.ok(d <= limits[who] * STEP_H + 1, `${who} saute de ${d.toFixed(0)} nm à ${new Date(rows[i].t).toISOString()}`);
      }
    }
  });

  it("le bateau A reste à Cayenne pendant tout l'épisode", () => {
    for (const { t, cast } of rows) {
      assert.ok(cast.main.visible);
      if (t > tOut0 && t <= tRet1) assert.ok(nm(cast.main, CAYENNE) < 1, new Date(t).toISOString());
    }
  });

  it("le bateau B n'existe qu'entre Halifax et Halifax (via Saint-Pierre)", () => {
    const seen = rows.filter((r) => r.cast.side.visible);
    assert.ok(seen.length > 0);
    for (const { t, cast } of rows) {
      const inside = t > tOut1 && t <= tRet0;
      assert.equal(cast.side.visible, inside, new Date(t).toISOString());
      if (inside) {
        assert.ok(cast.side.lat > 43.5 && cast.side.lat < 47.5 && cast.side.lon < -54 && cast.side.lon > -64.5);
      }
    }
    assert.ok(nm(seen[0].cast.side, HALIFAX) < 5);
    assert.ok(nm(seen[seen.length - 1].cast.side, HALIFAX) < 5);
    assert.ok(seen.some((r) => nm(r.cast.side, { lat: 46.7761, lon: -56.1628 }) < 5), "B touche Saint-Pierre");
  });

  it("l'avion n'apparaît que pendant les deux vols", () => {
    for (const { t, cast } of rows) {
      const flying = (t > tOut0 && t <= tOut1) || (t > tRet0 && t <= tRet1);
      assert.equal(cast.plane.visible, flying, new Date(t).toISOString());
      if (flying) assert.equal(cast.follow, cast.plane);
    }
  });

  it("le suivi caméra suit l'acteur qui bouge", () => {
    for (const { cast } of rows) {
      const want = { plane: cast.plane, side: cast.side, main: cast.main }[cast.vehicle];
      assert.equal(cast.follow, want);
    }
  });
});

describe("positionAt — axe film de l'horloge de production", () => {
  it("filmNm ne recule jamais (quai Cayenne au retour : 8680 après 9818)", () => {
    const v = clockVertices(CLOCK);
    let last = -Infinity;
    for (let t = at(v[0]); t <= at(v[v.length - 1]); t += 600000) {
      const p = positionAt(CLOCK, t);
      assert.ok(p.filmNm >= last - 1e-6, `${new Date(t).toISOString()} ${p.filmNm} < ${last}`);
      last = p.filmNm;
    }
  });
});

describe("pickSceneCast", () => {
  it("en film, la carte dessine la distribution publiée par le lecteur", () => {
    const cast = castAtClock(CLOCK, Date.parse("2026-08-18T00:00:00Z"));
    const fallback = () => ({ main: { visible: true }, side: { visible: false } });
    assert.equal(pickSceneCast({ filmActive: true, film: { cast }, fallback }), cast);
    assert.deepEqual(pickSceneCast({ filmActive: false, film: { cast }, fallback }), fallback());
    assert.deepEqual(pickSceneCast({ filmActive: true, film: {}, fallback }), fallback());
  });
});
