import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  LANE_FREE,
  LANE_NOW,
  TTL,
  advanceMoments,
  cardFromEvent,
  cardSpeech,
  classifyMoment,
  dismissNow,
  emptyMoments,
  entityForEvent,
  infoItemsFromBag,
  nextFree,
} from "./momentCard.js";

const gale = {
  id: "wind-gale:1", stableKey: "wind-gale:a", type: "wind-gale", severity: "alert", judge: "now",
  judgeReason: "safety", whenNm: 0, filmCum: 100, payload: { tws: 36, kind: "forecast" },
};
const poeAhead = {
  id: "poe-ahead:1", stableKey: "poe-ahead:lr", type: "poe-ahead", severity: "info", judge: "now",
  judgeReason: "safety", whenNm: 12, filmCum: 112,
  payload: { poe: { name: "La Rochelle - La Pallice", nm: 12, lat: 46.16, lon: -1.22, url: "https://www.douane.gouv.fr/x" } },
};
const windShiftLater = {
  id: "wind-shift:1", stableKey: "wind-shift:b", type: "wind-shift", severity: "info", judge: "later",
  judgeReason: "later", whenNm: 0, filmCum: 140, payload: { tws: 18, twd: 240, dTws: 9, kind: "forecast" },
};
const digest = {
  id: "group:zee-ahead:1", type: "group", severity: "watch", judge: "now", judgeReason: "digest",
  whenNm: 20, filmCum: 120, payload: { members: ["zee-ahead", "poe-ahead"] },
  digest: { fr: "Depuis cette jambe : zee-ahead + poe-ahead.", en: "Along this leg: zee-ahead + poe-ahead." },
};

const bag = {
  at: { lat: 46.15, lon: -1.17 },
  nearby: {
    marinas: [{ name: "Port des Minimes", nm: 0.4, lat: 46.14, lon: -1.17, website: "https://port-la-rochelle.fr" }],
    capitaineries: [], wpi: [{ name: "La Pallice", nm: 2.2, lat: 46.16, lon: -1.22 }], anchorages: [],
  },
  science: { nearby: [{ name: "Cadastre napoléonien de La Rochelle 1811", nm: 0.8, lat: 46.15, lon: -1.15, source: "sextant", url: "https://sextant.ifremer.fr/x" }] },
  projects: [{ name: "Echo-Mer", nm: 0.7, lat: 46.15, lon: -1.16, url: "https://fondationdelamer.org" }],
  aton: { nearby: [{ name: "buoy_lateral", nm: 4.6, lat: 46.1, lon: -1.2, source: "osm-overpass" }] },
  satellites: { scene: { id: "S2A_MSIL2A_20260914T110651_N0512_R137_T30TXR_20260914T175111", product: "sentinel-2-l2a", datetime: "2026-09-14T11:06:51Z" } },
  climatology: { month: 9, source: "atlas", period: "1980-2020", point: { wind_atlas: { most_likely: { speed_knots: 8.8, dir_deg: 45 } } } },
};

describe("classifyMoment — deux voies", () => {
  it("sécurité / décision → NOW ; information → FREE ; caché → rien", () => {
    assert.equal(classifyMoment(gale), LANE_NOW);
    assert.equal(classifyMoment(poeAhead), LANE_NOW);
    assert.equal(classifyMoment({ ...gale, judge: "hide" }), null);
    assert.equal(classifyMoment(digest, { filmCum: 200 }), LANE_FREE);
    assert.equal(classifyMoment({ ...gale, type: "science-hit", judge: "now" }, { filmCum: 200 }), LANE_FREE);
  });

  it("« later » attend la tête de lecture en Simulation, jamais en Suivre", () => {
    assert.equal(classifyMoment(windShiftLater, { filmCum: 100 }), null);
    assert.equal(classifyMoment(windShiftLater, { filmCum: 140 }), LANE_FREE);
    assert.equal(classifyMoment(windShiftLater, { filmCum: 0, mode: "suivre" }), LANE_FREE);
    assert.equal(classifyMoment({ ...windShiftLater, judge: "now", promoted: true }, { filmCum: 0 }), LANE_FREE);
  });
});

describe("cartes", () => {
  it("cardFromEvent : texte de phraseForEvent, entité du payload, liens", () => {
    const card = cardFromEvent(poeAhead, "fr");
    assert.equal(card.lane, LANE_NOW);
    assert.match(card.text, /Port d’entrée officiel devant : La Rochelle - La Pallice/);
    assert.equal(card.entity.kind, "poe");
    assert.equal(card.entity.lat, 46.16);
    assert.equal(card.entity.url, "https://www.douane.gouv.fr/x");
    assert.equal(entityForEvent(gale), null);
    assert.equal(cardSpeech(card), card.text);
  });

  it("infoItemsFromBag : lieux, image satellite, climatologie — clés stables", () => {
    const items = infoItemsFromBag(bag, "fr");
    const kinds = items.map((c) => c.kind);
    assert.deepEqual(kinds, ["marina", "wpi", "science", "project", "aton", "satellite", "climatology"]);
    const marina = items[0];
    assert.equal(marina.title, "Marina");
    assert.equal(marina.text, "Port des Minimes à 0,4 nm.");
    assert.equal(marina.entity.url, "https://port-la-rochelle.fr");
    assert.equal(items[4].text, "bouée latérale à 4,6 nm.");
    assert.match(items[5].text, /Dernière image satellite : Sentinel-2 \(S2A, tuile T30TXR\)/);
    assert.match(items[6].text, /Climatologie de septembre/);
    assert.equal(infoItemsFromBag(bag, "en")[0].title, "Marina");
    // Same bag twice → same keys (dedupe works on the key).
    assert.deepEqual(infoItemsFromBag(bag).map((c) => c.key), items.map((c) => c.key));
    assert.deepEqual(infoItemsFromBag(null), []);
  });
});

describe("advanceMoments — file, expiration, moment libre", () => {
  it("une carte NOW à la fois ; l’alerte passe devant ; FREE attend", () => {
    let s = advanceMoments(emptyMoments(), { events: [poeAhead, gale], bag, filmCum: 100, nowMs: 1000, playing: true, legId: "A" });
    assert.equal(s.now.type, "wind-gale", "l’alerte est posée d’abord");
    assert.equal(s.nowQueue.length, 1);
    assert.equal(s.free, null, "rien en FREE tant qu’une carte NOW est posée");
    assert.ok(s.freeQueue.length >= 7, "le sac remplit la file d’information");

    // Same inputs → same object (no render).
    const again = advanceMoments(s, { events: [poeAhead, gale], bag, filmCum: 100, nowMs: 2000, playing: true, legId: "A" });
    assert.equal(again, s);

    // Playing: the gale expires after TTL.nowPlayingMs, the PoE card follows.
    s = advanceMoments(s, { events: [poeAhead, gale], bag, filmCum: 100, nowMs: 1000 + TTL.nowPlayingMs, playing: true, legId: "A" });
    assert.equal(s.now.type, "poe-ahead");
    assert.equal(s.nowQueue.length, 0);

    // Then the free block breathes.
    s = advanceMoments(s, { events: [poeAhead, gale], bag, filmCum: 100, nowMs: 1000 + 2 * TTL.nowPlayingMs, playing: true, legId: "A" });
    assert.equal(s.now, null);
    assert.equal(s.free.kind, "marina");
    const firstFree = s.free;
    s = advanceMoments(s, { events: [], bag, filmCum: 100, nowMs: firstFree.shownAt + TTL.freeMs, playing: true, legId: "A" });
    assert.equal(s.free.kind, "wpi", "rotation après TTL.freeMs");
  });

  it("en pause, une carte NOW ne s’efface pas seule ; fermer la fait passer", () => {
    let s = advanceMoments(emptyMoments(), { events: [gale, poeAhead], filmCum: 100, nowMs: 0, playing: false, legId: "A" });
    s = advanceMoments(s, { events: [gale, poeAhead], filmCum: 100, nowMs: 10 * 60_000, playing: false, legId: "A" });
    assert.equal(s.now.type, "wind-gale");
    s = dismissNow(s, 1);
    assert.equal(s.now.type, "poe-ahead");
    assert.ok(s.dismissed.has("ev:wind-gale:a"));
    // Never back, even if the ledger still has it.
    s = dismissNow(s, 2);
    assert.equal(s.now, null);
    s = advanceMoments(s, { events: [gale, poeAhead], filmCum: 100, nowMs: 3, playing: false, legId: "A" });
    assert.equal(s.now, null);
  });

  it("Suivre : NOW expire après 90 s, une fiche « later » se montre sans attendre le film", () => {
    let s = advanceMoments(emptyMoments(), { events: [gale, windShiftLater], filmCum: 0, nowMs: 0, mode: "suivre", legId: "A" });
    assert.equal(s.now.type, "wind-gale");
    s = advanceMoments(s, { events: [gale, windShiftLater], filmCum: 0, nowMs: TTL.nowSuivreMs, mode: "suivre", legId: "A" });
    assert.equal(s.now, null);
    assert.equal(s.free.type, "wind-shift");
  });

  it("file vide : le bloc boucle sur les fiches du sac, jamais sur les événements", () => {
    const small = { at: bag.at, nearby: { marinas: bag.nearby.marinas, wpi: bag.nearby.wpi } };
    let s = advanceMoments(emptyMoments(), { events: [windShiftLater], bag: small, filmCum: 200, nowMs: 0, mode: "suivre", legId: "A" });
    const order = [s.free.kind];
    for (let i = 1; i <= 6; i++) {
      s = advanceMoments(s, { events: [windShiftLater], bag: small, filmCum: 200, nowMs: i * TTL.freeSuivreMs, mode: "suivre", legId: "A" });
      order.push(s.free?.kind ?? null);
    }
    // wind-shift (event) once, then marina / wpi loop forever.
    assert.deepEqual(order, ["wind-shift", "marina", "wpi", "marina", "wpi", "marina", "wpi"]);
    assert.equal(s.seen.size, 3);
  });

  it("le récit arrive après la carte : le texte affiché se met à jour", () => {
    let s = advanceMoments(emptyMoments(), { events: [gale], filmCum: 100, nowMs: 0, playing: false, legId: "A" });
    assert.match(s.now.text, /Coup de vent : 36 kn/);
    const withStory = { ...gale, story: { status: "ready", text: "Le vent monte à 36 nœuds : on réduit la toile." } };
    s = advanceMoments(s, { events: [withStory], filmCum: 100, nowMs: 1, playing: false, legId: "A" });
    assert.equal(s.now.text, "Le vent monte à 36 nœuds : on réduit la toile.");
    assert.equal(s.now.storyStatus, "ready");
  });

  it("changement de jambe : les files se vident, le vu reste vu", () => {
    let s = advanceMoments(emptyMoments(), { events: [gale, poeAhead], bag, filmCum: 100, nowMs: 0, playing: false, legId: "A" });
    assert.equal(s.nowQueue.length, 1);
    s = advanceMoments(s, { events: [], bag, filmCum: 100, nowMs: 1, playing: false, legId: "B" });
    assert.equal(s.nowQueue.length, 0);
    assert.equal(s.freeQueue.length, 0);
    assert.ok(s.seen.has("bag:marina:Port des Minimes:46.14:-1.17"));
  });

  it("pur : deux appels sur le même état précédent donnent le même résultat (StrictMode)", () => {
    const prev = emptyMoments();
    const input = { events: [gale], bag, filmCum: 100, nowMs: 0, playing: false, legId: "A" };
    const a = advanceMoments(prev, input);
    const b = advanceMoments(prev, input);
    assert.equal(prev.seen.size, 0, "l’état précédent n’est jamais muté");
    assert.equal(a.now.type, "wind-gale");
    assert.equal(b.now.type, "wind-gale");
    assert.equal(a.freeQueue.length, b.freeQueue.length);
    assert.equal(a.seen.size, b.seen.size);
  });

  it("nextFree avance à la main et reboucle sur le sac", () => {
    let s = advanceMoments(emptyMoments(), { events: [], bag, filmCum: 0, nowMs: 0, playing: false, legId: "A" });
    assert.equal(s.free.kind, "marina");
    s = nextFree(s, 1);
    assert.equal(s.free.kind, "wpi");
    const total = 1 + s.freeQueue.length;
    for (let i = 0; i < total; i++) s = nextFree(s, 2 + i);
    assert.equal(s.free.kind, "marina", "après un tour complet, on revient au début");
    // One event card alone never loops.
    let e = advanceMoments(emptyMoments(), { events: [windShiftLater], filmCum: 200, nowMs: 0, playing: false, legId: "A" });
    assert.equal(e.free.type, "wind-shift");
    e = nextFree(e, 1);
    assert.equal(e.free, null);
    assert.equal(nextFree(e, 2), e);
  });
});
