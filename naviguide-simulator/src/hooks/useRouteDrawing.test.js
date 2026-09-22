import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "url";
import { describe, it } from "node:test";
import { importPointsSequential } from "./useRouteDrawing.js";

const here = dirname(fileURLToPath(import.meta.url));
const hook = readFileSync(join(here, "useRouteDrawing.js"), "utf8");

const PTS = [
  { lat: 46.157, lon: -1.151, name: "La Rochelle" },
  { lat: 43.545, lon: -5.662, name: "Gijon" },
  { lat: 38.722, lon: -9.139, name: "Lisbonne" },
];

function makeSession() {
  const points = [];
  const segments = [];
  let resets = 0;
  async function addPoint(lat, lon, extra) {
    const next = { lat, lon, ...(extra?.name ? { name: extra.name } : {}) };
    const prev = points.at(-1);
    points.push(next);
    if (prev) segments.push({ from: prev, to: next });
  }
  function reset() {
    resets += 1;
    points.length = 0;
    segments.length = 0;
  }
  return { points, segments, resets: () => resets, addPoint, reset };
}

describe("useRouteDrawing importPoints (lot N1)", () => {
  it("expose importPoints qui rejoue importPointsSequential (reset + un addPoint par waypoint)", () => {
    assert.match(hook, /export async function importPointsSequential/);
    assert.match(hook, /const importPoints = useCallback/);
    assert.match(hook, /importPointsSequential\(addPoint, reset, points\)/);
    assert.match(hook, /if \(updated\.length >= 2\) return fetchSegment/);
    assert.match(hook, /importPoints,/);
  });

  it("importPoints ≡ N clics sur une route vide", async () => {
    const clicks = makeSession();
    for (const p of PTS) await clicks.addPoint(p.lat, p.lon, { name: p.name });

    const imported = makeSession();
    await importPointsSequential(imported.addPoint, imported.reset, PTS);

    assert.equal(imported.resets(), 1);
    assert.deepEqual(imported.points, clicks.points);
    assert.deepEqual(imported.segments, clicks.segments);
    assert.equal(imported.segments.length, 2);
  });

  it("remplace la route en cours (reset avant les N clics)", async () => {
    const session = makeSession();
    await session.addPoint(0, 0, { name: "Ancien" });
    await importPointsSequential(session.addPoint, session.reset, PTS);
    assert.equal(session.resets(), 1);
    assert.equal(session.points.length, 3);
    assert.equal(session.points[0].name, "La Rochelle");
    assert.equal(session.points.some((p) => p.name === "Ancien"), false);
  });
});
