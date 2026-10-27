import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  FILM_FOCUS_BUBBLE_MAX_MS,
  FILM_FOCUS_UNBOUND_MS,
  filmExitZoomHold,
  filmFocusAnchor,
  filmFocusExpired,
  filmFocusHold,
  filmTrackAfterFocus,
  focusFromBubble,
  heldFilmPose,
  lonNearAnchor,
} from "./filmFocus.js";
import { bubbleFocusEnds } from "../components/eventBubble.js";

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFileSync(join(here, path), "utf8");

describe("« Voir sur la carte » pendant le film (#102)", () => {
  it("vise le bateau du film : la pose de la caméra d'abord, sinon la position publiée", () => {
    const pose = { lat: 46.1, lon: -361.2, heading: 90 };
    const film = { lat: 46.2, lon: -1.3 };
    assert.deepEqual(filmFocusAnchor(pose, film), { lat: 46.1, lon: -361.2 });
    assert.deepEqual(filmFocusAnchor(null, film), { lat: 46.2, lon: -1.3 });
    assert.deepEqual(filmFocusAnchor({ lat: Number.NaN, lon: 2 }, film), { lat: 46.2, lon: -1.3 });
    assert.equal(filmFocusAnchor(null, {}), null);
  });

  it("ramène le lieu dans la copie du monde du bateau (trait court, pas un tour du monde)", () => {
    assert.equal(lonNearAnchor(-16.9, -361.2), -376.9);
    assert.equal(lonNearAnchor(-179, 179), 181);
    assert.equal(lonNearAnchor(10, 12), 10);
    assert.equal(lonNearAnchor(10, Number.NaN), 10);
  });

  it("garde le zoom d'avant le premier recentrage quand on en enchaîne plusieurs", () => {
    const first = filmFocusHold(null, { zoom: 5, zoomHold: undefined, fromBubble: true, at: 1000 });
    assert.deepEqual(first, { zoom: 5, zoomHold: null, fromBubble: true, at: 1000 });
    const second = filmFocusHold(first, { zoom: 9.5, zoomHold: 9.5, fromBubble: false, at: 4000 });
    assert.deepEqual(second, { zoom: 5, zoomHold: null, fromBubble: false, at: 4000 });
    assert.equal(filmFocusHold(null, { zoom: 6, zoomHold: 7, fromBubble: true, at: 0 }).zoomHold, 7);
  });

  it("seul le bouton de la bulle lie le recentrage à la bulle : le lieu est l'entité de la carte affichée", () => {
    const entity = { name: "Funchal", lat: 32.65, lon: -16.91 };
    assert.equal(focusFromBubble(entity, { id: "a", entity }), true);
    assert.equal(focusFromBubble({ ...entity }, { id: "a", entity }), false, "lien du panneau, même lieu");
    assert.equal(focusFromBubble(entity, null), false, "bulle en fondu ou absente");
    assert.equal(focusFromBubble(null, { id: "a" }), false);
  });

  it("la bulle tient la caméra jusqu'à sa fermeture (20 s au plus) ; hors bulle, la caméra revient après 8 s", () => {
    const bubble = filmFocusHold(null, { zoom: 5, fromBubble: true, at: 0 });
    const link = filmFocusHold(null, { zoom: 5, fromBubble: false, at: 0 });
    assert.ok(FILM_FOCUS_BUBBLE_MAX_MS > FILM_FOCUS_UNBOUND_MS);
    assert.equal(filmFocusExpired(bubble, FILM_FOCUS_BUBBLE_MAX_MS - 1), false);
    assert.equal(filmFocusExpired(bubble, FILM_FOCUS_BUBBLE_MAX_MS), true);
    assert.equal(filmFocusExpired(link, FILM_FOCUS_UNBOUND_MS - 1), false);
    assert.equal(filmFocusExpired(link, FILM_FOCUS_UNBOUND_MS), true);
    assert.equal(filmFocusExpired(null, 1e9), false);
  });

  it("si le film s'arrête pendant un recentrage, il garde le zoom d'avant le recentrage", () => {
    assert.equal(filmExitZoomHold(null), null);
    assert.equal(filmExitZoomHold({ zoom: 5, zoomHold: null }), 5);
    assert.equal(filmExitZoomHold({ zoom: 5, zoomHold: 7 }), 7);
  });

  it("pendant la tenue, le bateau continue sur la position brute du film", () => {
    const prev = { lat: 1, lon: 2, heading: 10, filmNm: 100, extra: "kept" };
    assert.deepEqual(heldFilmPose(prev, { lat: 3, lon: 4, bearing: 45, filmNm: 120 }, 364), {
      lat: 3, lon: 364, heading: 45, filmNm: 120, extra: "kept",
    });
    assert.deepEqual(heldFilmPose(prev, { lat: 3, lon: 4 }, 4), { ...prev, lat: 3, lon: 4 });
    assert.equal(heldFilmPose(prev, { lat: Number.NaN, lon: 4 }, 4), prev);
  });

  it("la reprise efface le suivi de caméra mais pas le zoom du film", () => {
    const reset = filmTrackAfterFocus();
    assert.equal(reset.filmLastBoat, null);
    assert.equal(reset.filmLastCenter, null);
    assert.equal(reset.filmFramesSinceReset, 0);
    for (const kept of ["filmZoom", "filmZoomBase", "filmChapterIdx"]) assert.ok(!(kept in reset), kept);
  });

  it("la bulle met fin au recentrage quand elle se ferme ou change de carte, pas quand elle se réaffiche", () => {
    assert.equal(bubbleFocusEnds(null, { id: "a" }), false);
    assert.equal(bubbleFocusEnds("a", { id: "a" }), false);
    assert.equal(bubbleFocusEnds("a", { id: "b" }), true);
    assert.equal(bubbleFocusEnds("a", null), true);
  });
});

describe("« Voir sur la carte » pendant le film — branchements (#102)", () => {
  const controller = read("MapSceneController.js");
  const bubble = read("../components/EventBubble.jsx");

  it("la boucle du film tient la caméra pendant le recentrage et la rend à l'échéance", () => {
    const loop = controller.slice(controller.indexOf("ensureFilmCameraLoop() {"), controller.indexOf("stopFilmCameraLoop() {"));
    assert.match(loop, /if \(filmFocusExpired\(this\.filmFocusHold, now\)\) this\.clearBriefingFocus\(\);/);
    assert.match(loop, /if \(this\.filmFocusHold\) this\.holdFilmBoat\(\);\s*else this\.syncFilmCamera\(this\.config, now\);/);
  });

  it("hors film, le recentrage reste une navigation manuelle ; pendant le film, il ne touche pas au suivi", () => {
    const focus = controller.slice(controller.indexOf("focusBriefingPlace(place, boat) {"), controller.indexOf("clearBriefingFocus() {"));
    assert.match(focus, /boat = filmFocusAnchor\(this\.filmPose, film\) \|\| boat;/);
    assert.match(focus, /fromBubble: focusFromBubble\(place, this\.eventBubble\?\.shownCard\?\.\(\)\)/);
    assert.match(focus, /if \(!filming\) \{\s*this\.userNavigated = true;\s*this\.callbacks\.onManualNavigation\?\.\(\);/);
  });

  it("un geste pendant la tenue ne coupe pas le suivi ; la bulle ne rend que les recentrages qu'elle a lancés", () => {
    assert.match(controller, /this\.onUserNavigation = \(event\) => \{[\s\S]{0,160}if \(this\.ignoreUserNavigation \|\| this\.filmFocusHold\) return;/);
    assert.match(controller, /releaseBubbleFocus\(\) \{\s*if \(this\.filmFocusHold\?\.fromBubble\) this\.clearBriefingFocus\(\);/);
  });

  it("la reprise rend le zoom et la tenue de zoom du film, sur son bateau", () => {
    const release = controller.slice(controller.indexOf("releaseFilmFocus() {"), controller.indexOf("dropFilmFocus() {"));
    assert.match(release, /this\.camera\.filmZoomHold = hold\.zoomHold;/);
    assert.match(release, /Object\.assign\(this\.camera, filmTrackAfterFocus\(\)\);/);
    assert.match(release, /setView\(\[boat\.lat, boat\.lon\], hold\.zoom, \{ animate: false \}\)/);
  });

  it("l'arrêt du film, un changement de vue et le démontage oublient la tenue sans bouger la caméra", () => {
    assert.match(controller, /if \(previous\.filmActive && !this\.config\.filmActive\) \{\s*const focusZoom = filmExitZoomHold\(this\.filmFocusHold\);\s*this\.dropFilmFocus\(\);\s*if \(Number\.isFinite\(focusZoom\)\) this\.camera\.filmZoomHold = focusZoom;/);
    const reset = controller.slice(controller.indexOf("resetCameraForView() {"), controller.indexOf("setCameraPlaced(next) {"));
    assert.match(reset, /this\.dropFilmFocus\(\);/);
    assert.match(controller, /dispose\(\) \{\s*this\.filmFocusHold = null;/);
  });

  it("la bulle prévient la scène quand elle se ferme ou change de carte, et donne la carte affichée", () => {
    const hide = bubble.slice(bubble.indexOf("function hide("), bubble.indexOf("function show("));
    assert.match(hide, /scene\.releaseBubbleFocus\?\.\(\);/);
    const show = bubble.slice(bubble.indexOf("function show("), bubble.indexOf("function setCard("));
    assert.match(show, /if \(bubbleFocusEnds\(shownId, card\)\) scene\.releaseBubbleFocus\?\.\(\);/);
    assert.match(bubble, /shownCard: \(\) => \(shownId \? currentCard : null\),/);
  });
});
