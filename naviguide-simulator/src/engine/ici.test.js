import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  ICI_RADIUS_NM,
  boatPositionFromCast,
  emptyDossier,
  ici,
  mergeDossier,
  zeeEnterEvent,
} from "./ici.js";

describe("ici sac", () => {
  it("a les clés du sac", () => {
    const d = emptyDossier(46.15, -1.16);
    assert.equal(d.version, 1);
    assert.equal(d.radiusNm, ICI_RADIUS_NM);
    assert.equal(d.zee, null);
    assert.deepEqual(d.poe, []);
    assert.equal(d.science, null);
    assert.equal(d.event, null);
    assert.ok(d.nearby.marinas);
    assert.equal(d.sources.bi, null);
  });

  it("n'avale pas une grille polar et ajoute la jambe", () => {
    const d = ici(0, 0, {
      polarMeta: {
        boat_name: "Leopard 46",
        vmg_summary: { 12: { upwind: { vmg: 5 } } },
        grid: new Array(181),
      },
      jambe: { speedKnots: 7.2, etaHours: 12, fromStop: "La Rochelle", toStop: "Fort-de-France" },
    });
    assert.equal(d.polar.boat, "Leopard 46");
    assert.equal(d.polar.grid, undefined);
    assert.ok(d.polar.vmgHint);
    assert.equal(d.polar.speedKnots, 7.2);
    assert.equal(d.polar.etaHours, 12);
    assert.equal(d.marks[0].to, "Fort-de-France");
  });

  it("fusionne le sac serveur sans recoller toute la carte", () => {
    const remote = {
      ...emptyDossier(46.15, -1.16),
      zee: { name: "French Exclusive Economic Zone", mrgid: 5677, gold: true },
      poe: [{ name: "La Rochelle", nm: 1.2, url: "https://douane.gouv.fr/x" }],
      amp: [{ name: "Pertuis", nm: 8 }],
    };
    const d = mergeDossier(remote, {
      polarMeta: { boat_name: "Leopard 46", grid: [1, 2, 3] },
      event: { type: "zee-enter", name: remote.zee.name, mrgid: 5677 },
    });
    assert.equal(d.zee.mrgid, 5677);
    assert.equal(d.poe.length, 1);
    assert.equal(d.polar.grid, undefined);
    assert.equal(d.event.type, "zee-enter");
  });

  it("prend le bateau à quai pendant l’avion, le relais en side-sail", () => {
    const air = boatPositionFromCast({
      vehicle: "plane",
      main: { lat: 4.93, lon: -52.33 },
      plane: { lat: 30, lon: -40 },
    }, [-40, 30]);
    assert.equal(air.lat, 4.93);
    assert.equal(air.lon, -52.33);

    const side = boatPositionFromCast({
      vehicle: "side",
      main: { lat: 4.93, lon: -52.33 },
      side: { lat: 46.78, lon: -56.17 },
    }, [-56.17, 46.78]);
    assert.equal(side.lat, 46.78);
  });

  it("ajoute un sondage GEBCO au large, null près des côtes", () => {
    const far = mergeDossier(emptyDossier(0, 0), {
      gebcoGrid: { sample: () => -3200 },
      distToShoreNm: 80,
    });
    assert.equal(far.depthOffshore, -3200);
    const near = mergeDossier(emptyDossier(46.15, -1.16), {
      gebcoGrid: { sample: () => -12 },
      distToShoreNm: 4,
    });
    assert.equal(near.depthOffshore, null);
  });

  it("signale l’entrée de ZEE seulement au changement de mrgid", () => {
    const zee = { name: "French Exclusive Economic Zone", mrgid: 5677 };
    assert.equal(zeeEnterEvent(undefined, zee), null);
    assert.equal(zeeEnterEvent(5677, zee), null);
    const ev = zeeEnterEvent(8462, zee);
    assert.equal(ev.type, "zee-enter");
    assert.equal(ev.mrgid, 5677);
  });
});
