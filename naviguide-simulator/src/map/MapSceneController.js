import L from "leaflet";
import { catamaranSvg } from "../engine/catamaranIcon.js";
import { interpolateCast, isAirPhase } from "../engine/filmCast.js";
import { wakeCursorAt } from "../engine/filmWake.js";
import { haversineNm, unwrapLon, worldCopyLineCoords } from "../utils/geo.js";
import { computeMarkerOffsets, projectRouteSegments } from "../utils/markerOffsets.js";
import {
  cameraLngForBoat,
  flagIconMetrics,
  flagMarkerHtml,
  markerWorldLngs,
  waypointFlagSrcs,
  wrapLon,
} from "../utils/waypointFlags.js";
import {
  shouldPlaceInitialCamera,
  shouldResnapCamera,
} from "../utils/sceneGate.js";
import { applyMarkerRotation } from "../utils/markerRotation.js";
import {
  flagWorldLngsForView,
  markerOffsetDelay,
} from "../hooks/useMarkerOffsets.js";
import { createPanes } from "../layers/layerOrder.js";
import {
  ROUTE_CASING_COLOR,
  ROUTE_CASING_WEIGHT,
  ROUTE_MAIN_WEIGHT,
  TILE_ATTRIBUTION,
  TILE_URLS,
  WAKE_DONE_COLOR,
  WAKE_REST_COLOR,
} from "../layers/styles.js";
import { SceneLayerRegistry } from "./SceneLayerRegistry.js";
import { ScenePlaybackController } from "./ScenePlaybackController.js";
import { applyFilmCamera, filmChapterZoom } from "./filmCamera.js";
import { attachEventBubble } from "../components/EventBubble.jsx";
import { attachEscalePopup } from "../components/EscalePopup.jsx";

const WORLD_OFFSETS = [0, 360, -360];
const TELEPORT_NM = 80;

const WAKE_STYLE = {
  color: WAKE_DONE_COLOR,
  weight: 4,
  opacity: 0.92,
  pane: "route",
  interactive: false,
};

const REST_STYLE = {
  color: WAKE_REST_COLOR,
  weight: 4,
  opacity: 0.88,
  pane: "route",
  interactive: false,
};

function latLngs(coords, worldOffset = 0) {
  return coords.map(([lon, lat]) => [lat, lon + worldOffset]);
}

function addRouteLine(group, coords, { color, weight, dash, pane = "route" }) {
  if (!coords || coords.length < 2) return;
  worldCopyLineCoords(coords).forEach((copy) => {
    L.polyline(copy.map(([lon, lat]) => [lat, lon]), {
      color,
      weight,
      dashArray: dash,
      pane,
      interactive: true,
    }).addTo(group);
  });
}

function addWorldLine(group, coords, style) {
  if (!coords || coords.length < 2) return;
  worldCopyLineCoords(coords).forEach((copy) => {
    L.polyline(copy.map(([lon, lat]) => [lat, lon]), style).addTo(group);
  });
}

function staticWakeParts(flat) {
  const points = flat?.points || [];
  const parts = [];
  const partByPoint = new Array(points.length);
  const linePointByIndex = new Array(points.length);
  let current = null;
  points.forEach((point, index) => {
    if (!Number.isFinite(point?.lon) || !Number.isFinite(point?.lat)) return;
    if (!current || point.jump) {
      current = [];
      parts.push(current);
    }
    const lon = current.length ? unwrapLon(current.at(-1)[0], point.lon) : point.lon;
    const linePoint = [lon, point.lat];
    current.push(linePoint);
    partByPoint[index] = parts.length - 1;
    linePointByIndex[index] = linePoint;
  });
  return { points, parts, partByPoint, linePointByIndex };
}

function createWorldLines(group, style) {
  return WORLD_OFFSETS.map(() => L.polyline([], style).addTo(group));
}

function clearDoneLines(lines) {
  lines.forEach((worldLines) => worldLines.forEach((line) => line.setLatLngs([])));
}

function appendDonePoint(geometry, index) {
  const point = geometry.linePointByIndex[index];
  const partIndex = geometry.partByPoint[index];
  if (!point || partIndex == null) return;
  geometry.doneLines[partIndex].forEach((line, worldIndex) => {
    line.addLatLng([point[1], point[0] + WORLD_OFFSETS[worldIndex]]);
  });
}

function setWakeTail(lines, from, to) {
  if (!from || !to) {
    lines.forEach((line) => line.setLatLngs([]));
    return;
  }
  const coords = [[from.lon, from.lat], [to.lon, to.lat]];
  lines.forEach((line, index) => line.setLatLngs(latLngs(coords, WORLD_OFFSETS[index])));
}

function zoomForRemaining(nm) {
  if (nm > 1800) return 3;
  if (nm > 500) return 4;
  if (nm > 120) return 5;
  if (nm > 30) return 6;
  return 7;
}

function planeHtml() {
  return `<div class="plane-icon marker-rotatable" data-marker-rotatable style="width:64px;height:64px;">
    <svg viewBox="0 0 24 24" width="64" height="64" aria-label="avion">
      <path fill="#f8fafc" stroke="#22d3ee" stroke-width="0.8"
        d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5L21 16z"/>
    </svg>
  </div>`;
}

function markerIcon(className, html) {
  return L.divIcon({
    className,
    html,
    iconSize: [64, 64],
    iconAnchor: [32, 32],
  });
}

/**
 * Single owner for the map's mutable Leaflet objects.
 *
 * Static changes call `update()`; animation frames only call `renderDynamic()`.
 * Every object is registered once and follows an explicit add/update/remove
 * lifecycle until `dispose()` tears the scene down.
 */
function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export class MapSceneController {
  static mount(container, callbacks) {
    const map = L.map(container, {
      center: [22, 5],
      zoom: 2,
      zoomSnap: 0.25,
      minZoom: 2,
      maxZoom: 18,
      worldCopyJump: false,
      preferCanvas: true,
    });
    createPanes(map);
    return new MapSceneController(map, callbacks);
  }

  constructor(map, callbacks = {}) {
    this.map = map;
    this.callbacks = callbacks;
    this.layers = new SceneLayerRegistry();
    this.config = {};
    this.baseLayer = L.tileLayer(TILE_URLS.dark, {
      attribution: TILE_ATTRIBUTION,
      updateWhenZooming: false,
    }).addTo(map);
    this.wakeGeometry = null;
    this.markerSets = new Map();
    this.waypointMarkers = new Map();
    this.divIconCache = new Map();
    this.currentPlayback = null;
    this.currentCast = null;
    this.routeInputs = null;
    this.altDraft = Symbol("uninitialized");
    this.waypointInputs = null;
    this.waypointsDirty = true;
    this.waypointTimer = null;
    this.cameraPlaced = false;
    this.userNavigated = false;
    this.ignoreUserNavigation = false;
    this.ignoreUserNavigationTimer = 0;
    this.camera = {
      lastFollow: 0,
      lastJump: 0,
      lastPos: null,
      followLon: null,
      lastPhase: null,
      resetKey: null,
      recapture: null,
      focus: null,
      filmChapterIdx: null,
      filmZoom: null,
      filmSetViewAt: 0,
      filmFlyingUntil: 0,
      filmLastCenter: null,
    };
    this.playback = new ScenePlaybackController({
      onFrame: (snapshot) => this.renderDynamic(snapshot),
      onPublish: (snapshot) => this.publishPlayback(snapshot),
    });
    this.zoomAnimating = false;
    this.zoomJustEnded = false;
    this.waypointZoom = map.getZoom();
    this.onZoomAnim = () => {
      this.zoomAnimating = true;
    };
    this.onZoomEnd = () => {
      this.zoomAnimating = false;
      this.zoomJustEnded = true;
      this.scheduleWaypoints({ reason: "zoom" });
      this.waypointZoom = this.map.getZoom();
    };
    this.onMoveEnd = () => {
      // Lot U : pas de sac ni de récit ici — seulement copies bateau + offsets.
      if (this.zoomAnimating) return;
      if (this.zoomJustEnded) {
        this.zoomJustEnded = false;
        this.waypointZoom = this.map.getZoom();
        return;
      }
      this.syncDynamicWorldCopies();
      // A pan the camera made while following the boat (lot I): the flags
      // keep their offsets — recomputing them at every step made them jump.
      // A zoom (projection change) or a pan the camera did not make: recompute.
      this.scheduleWaypoints({ reason: this.isCameraFollowing() && this.map.getZoom() === this.waypointZoom ? "follow" : "move" });
      this.waypointZoom = this.map.getZoom();
    };
    this.onUserNavigation = () => {
      if (this.ignoreUserNavigation) return;
      this.userNavigated = true;
      this.map.stop();
      this.callbacks.onManualNavigation?.();
    };
    map.on("zoomanim", this.onZoomAnim);
    map.on("zoomend", this.onZoomEnd);
    map.on("moveend", this.onMoveEnd);
    map.on("zoomstart", this.onUserNavigation);
    map.on("dragstart", this.onUserNavigation);
    this.eventBubble = attachEventBubble(this, L);
    this.escalePopup = attachEscalePopup(this, L);
  }

  /** Marqueur du bateau « à l'écran » (copie monde 0) — ancre de la bulle F4. */
  mainBoatMarker() {
    const liveMode = this.config.isSuivre && this.config.live && !this.config.previewing;
    const order = this.config.filmActive || liveMode
      ? ["live", "ghost", "simulation", "drawing"]
      : ["simulation", "live", "ghost", "drawing"];
    for (const role of order) {
      const marker = (this.markerSets.get(role) || [])[0];
      if (marker) return marker;
    }
    return null;
  }

  get api() {
    return {
      getMap: () => this.map,
      getView: () => ({ center: this.map.getCenter(), zoom: this.map.getZoom() }),
      setView: (center, zoom, options) => this.programmaticMove(() => this.map.setView(center, zoom, options)),
      playback: {
        play: () => this.playback.play(),
        pause: () => this.playback.pause(),
        toggle: () => this.playback.toggle(),
        seek: (nm, options) => this.playback.seek(nm, options),
        setProfile: (profile) => this.playback.setProfile(profile),
      },
      briefing: {
        focus: (place, boat) => this.focusBriefingPlace(place, boat),
        clear: () => this.clearBriefingFocus(),
      },
    };
  }

  /**
   * Briefing link "voir sur la carte": pin the named place, draw a dashed line
   * from the boat, and fit both in view. Counts as a manual navigation so the
   * camera does not snap back to the boat until the skipper recaptures it.
   */
  focusBriefingPlace(place, boat) {
    const lat = Number(place?.lat);
    const lon = Number(place?.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false;
    this.clearBriefingFocus();
    const group = L.layerGroup();
    const label = String(place.name || "").slice(0, 60);
    const icon = L.divIcon({
      className: "briefing-focus-pin",
      html: `<div class="briefing-focus-dot"></div><div class="briefing-focus-label">${escapeHtml(label)}</div>`,
      iconSize: [0, 0],
      iconAnchor: [0, 0],
    });
    L.marker([lat, lon], { icon, pane: "briefing-focus", interactive: false, keyboard: false }).addTo(group);
    const bounds = L.latLngBounds([[lat, lon]]);
    const bLat = Number(boat?.lat);
    const bLon = Number(boat?.lon);
    if (Number.isFinite(bLat) && Number.isFinite(bLon)) {
      L.polyline([[bLat, bLon], [lat, lon]], {
        pane: "briefing-focus",
        color: "#7dd3fc",
        weight: 1.5,
        dashArray: "4 6",
        opacity: 0.9,
        interactive: false,
      }).addTo(group);
      bounds.extend([bLat, bLon]);
    }
    group.addTo(this.map);
    this.briefingFocus = group;
    this.userNavigated = true;
    this.callbacks.onManualNavigation?.();
    this.programmaticMove(() => this.map.fitBounds(bounds.pad(0.35), {
      paddingTopLeft: [340, 60],
      paddingBottomRight: [340, 120],
      maxZoom: 13,
      animate: true,
    }));
    return true;
  }

  clearBriefingFocus() {
    if (this.briefingFocus) {
      this.briefingFocus.remove();
      this.briefingFocus = null;
    }
  }

  setCallbacks(callbacks) {
    this.callbacks = callbacks;
  }

  update(next) {
    const previous = this.config;
    const previousView = previous.view;
    this.config = { ...this.config, ...next };
    if (!previous.filmActive && this.config.filmActive) {
      this.camera.filmChapterIdx = null;
      this.camera.filmZoom = null;
      this.camera.filmSetViewAt = 0;
      this.camera.filmFlyingUntil = 0;
      this.camera.filmLastCenter = null;
    }
    if (previous.filmActive && !this.config.filmActive) {
      this.camera.filmChapterIdx = null;
      this.camera.filmZoom = null;
      this.camera.filmSetViewAt = 0;
      this.camera.filmFlyingUntil = 0;
      this.camera.filmLastCenter = null;
      this.camera.recapture = this.config.cinemaRecapture;
      const live = this.config.live;
      if (live && Number.isFinite(live.lat) && Number.isFinite(live.lon) && this.map) {
        const lonCam = cameraLngForBoat(live.lon, this.camera.followLon);
        this.camera.followLon = lonCam;
        this.camera.lastPos = { lat: live.lat, lon: live.lon };
        this.programmaticMove(() => this.map.setView(
          [live.lat, lonCam],
          this.map.getZoom(),
          { animate: false },
        ));
      }
    }
    if (previousView && previousView !== this.config.view) this.resetCameraForView();
    this.syncBaseLayer();
    this.syncInitialCamera();
    this.syncRoute();
    this.syncAltRoute();
    this.syncWaypoints();
    const playbackChanged = previous.flat !== this.config.flat
      || previous.marks !== this.config.marks
      || previous.boatKnots !== this.config.boatKnots
      || previous.routeReady !== this.config.routeReady
      || previous.stopAuto !== this.config.stopAuto;
    if (playbackChanged) {
      this.playback.configure({
        flat: this.config.flat,
        marks: this.config.marks,
        boatKnots: this.config.boatKnots,
        enabled: this.config.routeReady,
        stopAuto: this.config.stopAuto,
      });
    } else if (this.currentPlayback) {
      this.renderDynamic(this.currentPlayback);
    }
    if (this.config.filmActive) this.syncFilmCamera(this.config);
    // Entering / leaving the drawing mode (lot I): the boats of the official
    // route hide or come back at once, even while playback is paused.
    if (previous.drawingMode !== this.config.drawingMode || previous.sceneReady !== this.config.sceneReady) {
      this.syncMarkers(this.currentCast, this.currentPlayback);
    }
  }

  syncBaseLayer() {
    const url = this.config.isLightMode ? TILE_URLS.light : TILE_URLS.dark;
    if (this.baseLayer?._naviguideUrl === url) return;
    this.baseLayer?.remove();
    this.baseLayer = L.tileLayer(url, {
      attribution: TILE_ATTRIBUTION,
      updateWhenZooming: false,
    }).addTo(this.map);
    this.baseLayer._naviguideUrl = url;
    this.baseLayer.bringToBack();
  }

  syncRoute() {
    const input = {
      segments: this.config.segments,
      customRoute: this.config.customRoute,
      drawingMode: this.config.drawingMode,
      drawnSegments: this.config.drawnSegments,
      sceneReady: this.config.sceneReady,
    };
    if (
      this.routeInputs
      && this.routeInputs.segments === input.segments
      && this.routeInputs.customRoute === input.customRoute
      && this.routeInputs.drawingMode === input.drawingMode
      && this.routeInputs.drawnSegments === input.drawnSegments
      && this.routeInputs.sceneReady === input.sceneReady
    ) return;
    this.routeInputs = input;
    const group = this.layers.update("route", () => L.layerGroup().addTo(this.map), (layer) => layer.clearLayers());
    const visible = input.sceneReady || input.drawingMode;
    if (!visible) return;
    if (input.drawingMode) {
      (input.drawnSegments || []).forEach((segment) => {
        addRouteLine(group, segment.coords, {
          color: segment.failed ? "#f97316" : "#22c55e",
          weight: 3,
          dash: segment.failed ? "6 6" : null,
        });
      });
      return;
    }
    if (input.customRoute?.features) {
      input.customRoute.features
        .filter((feature) => feature.geometry?.type === "LineString")
        .forEach((feature) => addRouteLine(group, feature.geometry.coordinates, {
          color: "#0077ff",
          weight: ROUTE_MAIN_WEIGHT,
        }));
      return;
    }
    (input.segments || []).forEach((segment) => {
      if (!segment.coords?.length) return;
      if (segment.nonMaritime) {
        addRouteLine(group, segment.coords, { color: "orange", weight: 4, dash: "6 6" });
      }
    });
  }

  syncAltRoute() {
    const draft = this.config.draft;
    const showEnvelopes = Boolean(this.config.showEnvelopes);
    if (this.altDraft === draft && this.altShowEnvelopes === showEnvelopes) return;
    this.altDraft = draft;
    this.altShowEnvelopes = showEnvelopes;
    const group = this.layers.update("alt-route", () => L.layerGroup().addTo(this.map), (layer) => layer.clearLayers());
    if (!draft) return;
    const add = (coords, style) => {
      if (!coords?.length) return;
      addWorldLine(group, coords, { ...style, pane: "route" });
    };
    add(draft.old_geojson?.geometry?.coordinates, { color: "#94a3b8", weight: 2, dashArray: "7 7", opacity: 0.85 });
    add(draft.draft_geojson?.geometry?.coordinates, { color: "#22d3ee", weight: 3, opacity: 0.95 });
    if (showEnvelopes) {
      (draft.isochrones || []).forEach((iso) => {
        const ring = (iso || []).map((point) => [point.lon, point.lat]);
        if (ring.length > 2) add(ring, { color: "#fbbf24", weight: 1, dashArray: "2 4", opacity: 0.4 });
      });
    }
  }

  syncWake(sailNm, enabled) {
    const flat = this.config.flat;
    const group = this.layers.add("wake", () => L.layerGroup().addTo(this.map));
    if (!enabled || !flat?.points?.length) {
      if (this.wakeGeometry) group.clearLayers();
      this.wakeGeometry = null;
      return;
    }
    if (!this.wakeGeometry || this.wakeGeometry.flat !== flat) {
      group.clearLayers();
      const geometry = staticWakeParts(flat);
      geometry.flat = flat;
      geometry.parts.forEach((part) => {
        if (part.length < 2) return;
        WORLD_OFFSETS.forEach((offset) => L.polyline(latLngs(part, offset), REST_STYLE).addTo(group));
      });
      geometry.doneLines = geometry.parts.map(() => createWorldLines(group, WAKE_STYLE));
      geometry.tailLines = createWorldLines(group, WAKE_STYLE);
      geometry.completedIndex = -1;
      this.wakeGeometry = geometry;
    }
    const geometry = this.wakeGeometry;
    const target = Math.max(0, Number(sailNm) || 0);
    const targetIndex = wakeCursorAt({ points: geometry.points }, target, geometry.completedIndex);
    if (targetIndex < geometry.completedIndex) {
      clearDoneLines(geometry.doneLines);
      geometry.completedIndex = -1;
    }
    while (geometry.completedIndex < targetIndex) {
      geometry.completedIndex += 1;
      appendDonePoint(geometry, geometry.completedIndex);
    }
    const previous = geometry.points[geometry.completedIndex];
    const following = geometry.points[geometry.completedIndex + 1];
    const samePart = previous
      && following
      && geometry.partByPoint[geometry.completedIndex] === geometry.partByPoint[geometry.completedIndex + 1];
    const live = this.config.live;
    const filmPin = this.config.filmActive
      && live
      && Number.isFinite(live.lat)
      && Number.isFinite(live.lon);
    if (filmPin && previous && (!following || !following.jump)) {
      setWakeTail(geometry.tailLines, previous, {
        lon: unwrapLon(previous.lon, live.lon),
        lat: live.lat,
      });
      return;
    }
    if (!previous || !following || following.jump || !samePart) {
      setWakeTail(geometry.tailLines, null, null);
      return;
    }
    const span = (following.cumNm ?? 0) - (previous.cumNm ?? 0);
    const ratio = span > 0 ? Math.max(0, Math.min(1, (target - (previous.cumNm ?? 0)) / span)) : 0;
    const followingLon = unwrapLon(previous.lon, following.lon);
    setWakeTail(geometry.tailLines, previous, {
      lon: previous.lon + ratio * (followingLon - previous.lon),
      lat: previous.lat + ratio * (following.lat - previous.lat),
    });
  }

  syncMarker(role, {
    visible,
    lat,
    lon,
    bearing,
    className,
    html,
    draggable = false,
  }) {
    let markers = this.markerSets.get(role) || [];
    if (!visible || lat == null || lon == null) {
      markers.forEach((marker) => marker.remove());
      this.markerSets.set(role, []);
      return;
    }
    const lngs = markerWorldLngs(lon, this.map.getCenter()?.lng);
    if (markers.length !== lngs.length) {
      markers.forEach((marker) => marker.remove());
      markers = lngs.map((lng, index) => {
        const primary = index === 0;
        const marker = L.marker([lat, lng], {
          icon: markerIcon(className, html),
          draggable: draggable && primary,
          pane: "boat",
          interactive: draggable && primary,
        }).addTo(this.map);
        if (draggable && primary) {
          marker.on("dragstart", () => {
            this.playback.pause();
            this.callbacks.onBoatDragStart?.();
          });
          marker.on("drag", (event) => {
            const point = event.target.getLatLng();
            this.callbacks.onBoatDrag?.({ lat: point.lat, lon: wrapLon(point.lng) });
          });
        }
        return marker;
      });
      this.markerSets.set(role, markers);
    }
    markers.forEach((marker, index) => {
      marker.setLatLng([lat, lngs[index]]);
      applyMarkerRotation(marker, bearing || 0);
    });
    this.eventBubble?.sync();
  }

  syncMarkers(cast, snapshot) {
    const cfg = this.config;
    const ready = Boolean(cfg.sceneReady && !cfg.drawingMode);
    const liveMode = cfg.isSuivre && cfg.live && !cfg.previewing;
    // `visible` after the spread: a cast actor carries its own `visible`
    // flag, which used to override ours (ghost boats in Simulation, boats
    // left on the map while drawing — revue du 19 sept., lot I).
    this.syncMarker("simulation", {
      ...cast?.main,
      visible: ready && cfg.isSimulation && Boolean(cast?.main),
      className: "catamaran-divicon",
      html: catamaranSvg(0),
      draggable: true,
    });
    this.syncMarker("live", {
      visible: ready && liveMode && cast?.vehicle !== "plane",
      lat: cfg.live?.lat,
      lon: cfg.live?.lon,
      bearing: cfg.live?.bearing || 0,
      className: "catamaran-divicon catamaran-divicon--live",
      html: catamaranSvg(0),
    });
    this.syncMarker("ghost", {
      ...cast?.main,
      visible: ready && cfg.isSuivre && cfg.previewing && Boolean(cast?.main),
      className: "catamaran-divicon catamaran-divicon--ghost",
      html: catamaranSvg(0),
    });
    this.syncMarker("side", {
      ...cast?.side,
      visible: ready && Boolean(cast?.side?.visible),
      className: "catamaran-divicon catamaran-divicon--side",
      html: catamaranSvg(0),
    });
    this.syncMarker("plane", {
      ...cast?.plane,
      visible: ready && Boolean(cast?.plane?.visible),
      className: "plane-divicon",
      html: planeHtml(),
    });
    const drawBoat = cfg.drawnSegments?.length >= 1 ? cfg.drawnPoints?.at(-1) : null;
    this.syncMarker("drawing", {
      ...drawBoat,
      visible: Boolean(cfg.drawingMode && drawBoat),
      bearing: 0,
      className: "catamaran-divicon catamaran-divicon--draw",
      html: catamaranSvg(0),
    });
    this.eventBubble?.sync();
  }

  syncAirHop(cast) {
    const visible = isAirPhase(cast?.phase);
    if (!visible || !cast?.hopFrom || !cast?.hopTo) {
      this.layers.remove("air-hop");
      return;
    }
    const group = this.layers.add("air-hop", () => L.layerGroup().addTo(this.map));
    const copies = worldCopyLineCoords([
      [cast.hopFrom.lon, cast.hopFrom.lat],
      [cast.hopTo.lon, cast.hopTo.lat],
    ]);
    const style = {
      color: "#67e8f9",
      weight: 2,
      dashArray: "7 9",
      opacity: 0.8,
      pane: "route",
      interactive: false,
    };
    const lines = group.getLayers();
    if (lines.length !== copies.length) {
      group.clearLayers();
      copies.forEach((copy) => L.polyline(
        copy.map(([lon, lat]) => [lat, lon]),
        style,
      ).addTo(group));
      return;
    }
    lines.forEach((line, index) => {
      line.setLatLngs(copies[index].map(([lon, lat]) => [lat, lon]));
    });
  }

  syncWaypoints() {
    const cfg = this.config;
    const source = cfg.drawingMode
      ? (cfg.drawnPoints || []).map((point, index) => ({ ...point, name: point.name || `${index + 1}`, flag: "", flags: [] }))
      : (cfg.customRoute ? [] : (cfg.points || []));
    const inputs = {
      source,
      points: cfg.points,
      drawnPoints: cfg.drawnPoints,
      drawingMode: cfg.drawingMode,
      customRoute: cfg.customRoute,
      segments: cfg.segments,
    };
    if (
      !this.waypointsDirty
      && this.waypointInputs
      && this.waypointInputs.points === inputs.points
      && this.waypointInputs.drawnPoints === inputs.drawnPoints
      && this.waypointInputs.drawingMode === inputs.drawingMode
      && this.waypointInputs.customRoute === inputs.customRoute
      && this.waypointInputs.segments === inputs.segments
    ) return;
    this.waypointInputs = inputs;
    this.waypointsDirty = false;
    const routeCoords = (cfg.segments || []).filter((segment) => !segment.nonMaritime).flatMap((segment) => segment.coords || []);
    const project = (lon, lat) => {
      const point = this.map.latLngToLayerPoint([lat, lon]);
      return { x: point.x, y: point.y };
    };
    const offsets = source.length
      ? computeMarkerOffsets(source, project, projectRouteSegments(routeCoords, project))
      : [];
    const group = this.layers.add("waypoints", () => L.layerGroup().addTo(this.map));
    const expected = new Set();
    const bounds = this.map.getBounds();
    const west = bounds.getWest();
    const east = bounds.getEast();
    const cameraLng = this.map.getCenter()?.lng;
    source.forEach((point, index) => {
      const srcs = waypointFlagSrcs(point);
      if (!srcs.length && !cfg.drawingMode) return;
      const offset = offsets[index] || [0, 0];
      const stamp = ` data-testid="waypoint-flag" data-escale="${String(point.name || "").replace(/"/g, "&quot;")}"`;
      const html = srcs.length
        ? flagMarkerHtml(srcs, offset).replace("<div ", `<div${stamp} `)
        : `<div${stamp} style="width:10px;height:10px;border-radius:50%;background:${index === 0 ? "#22c55e" : "#e2e8f0"};border:2px solid #0f172a"></div>`;
      const metrics = srcs.length ? flagIconMetrics(srcs) : { iconSize: [24, 24], iconAnchor: [12, 12] };
      for (const [copyIndex, lng] of flagWorldLngsForView(point.lon, cameraLng, west, east).entries()) {
        const key = `${cfg.drawingMode ? "draw" : "route"}:${index}:${copyIndex}`;
        expected.add(key);
        const iconKey = `${html}|${metrics.iconSize.join(",")}|${metrics.iconAnchor.join(",")}`;
        let icon = this.divIconCache.get(iconKey);
        if (!icon) {
          icon = L.divIcon({
            className: "flag-divicon",
            html,
            iconSize: metrics.iconSize,
            iconAnchor: metrics.iconAnchor,
          });
          this.divIconCache.set(iconKey, icon);
        }
        let marker = this.waypointMarkers.get(key);
        if (!marker) {
          marker = L.marker([point.lat, lng], {
            icon,
            interactive: true,
          }).addTo(group);
          marker.on("mouseover", () => this.callbacks.onWaypointHover?.(marker._naviguideWaypoint));
          marker.on("mouseout", () => this.callbacks.onWaypointHover?.(null));
          marker.on("click", (event) => {
            L.DomEvent.stopPropagation(event);
            if (marker._naviguideDrawing) {
              this.callbacks.onDrawingWaypointClick?.(marker._naviguideWaypoint, marker._naviguideIndex);
              return;
            }
            this.callbacks.onWaypointClick?.(marker._naviguideWaypoint, marker._naviguideIndex);
          });
          this.waypointMarkers.set(key, marker);
        }
        marker._naviguideWaypoint = point;
        marker._naviguideDrawing = cfg.drawingMode;
        marker._naviguideIndex = index;
        marker.setLatLng([point.lat, lng]);
        if (marker._naviguideIconKey !== iconKey) {
          marker.setIcon(icon);
          marker._naviguideIconKey = iconKey;
        }
      }
    });
    this.waypointMarkers.forEach((marker, key) => {
      if (expected.has(key)) return;
      group.removeLayer(marker);
      this.waypointMarkers.delete(key);
    });
    this.escalePopup?.sync();
  }

  /** The camera is driving the map: playback running, or the live boat followed. */
  isCameraFollowing() {
    const cfg = this.config || {};
    if (cfg.filmActive) return true;
    if (!cfg.cameraFollow) return false;
    const liveMode = Boolean(cfg.isSuivre && cfg.live && !cfg.previewing);
    return Boolean(this.currentPlayback?.playing || liveMode);
  }

  scheduleWaypoints({ reason = "move" } = {}) {
    if (this.config?.filmActive) return; // flags stay put for the whole film (lot F1)
    if (!this.config.points?.length && !this.config.drawnPoints?.length) return;
    if (reason === "follow") return; // flags stay put while the camera follows (lot I)
    if (this.zoomAnimating && reason !== "zoom") return;
    window.clearTimeout(this.waypointTimer);
    this.waypointTimer = window.setTimeout(() => {
      this.waypointsDirty = true;
      this.syncWaypoints();
    }, markerOffsetDelay(this.config.cameraFollow, reason));
  }

  syncInitialCamera() {
    const cfg = this.config;
    if (!cfg.routeReady || !cfg.flat?.points?.length) {
      this.setCameraPlaced(false);
      return;
    }
    if (cfg.filmActive) {
      this.setCameraPlaced(true);
      return;
    }
    const recette = cfg.recetteMap;
    if (recette) {
      this.programmaticMove(() => this.map.setView([recette.lat, recette.lon], recette.z, { animate: false }));
      this.setCameraPlaced(true);
      return;
    }
    if (cfg.isSuivre && (!cfg.live || cfg.live.lat == null || cfg.live.lon == null)) {
      this.setCameraPlaced(false);
      return;
    }
    if (!shouldPlaceInitialCamera({ userNavigated: this.userNavigated })) {
      if (cfg.isSuivre) this.initialLive = { lat: cfg.live.lat, lon: cfg.live.lon };
      this.setCameraPlaced(true);
      return;
    }
    if (cfg.isSuivre) {
      if (this.initialLive && !shouldResnapCamera(this.initialLive, cfg.live)) {
        this.setCameraPlaced(true);
        return;
      }
      this.programmaticMove(() => this.map.setView([cfg.live.lat, cfg.live.lon], 6.5, { animate: false }));
      this.initialLive = { lat: cfg.live.lat, lon: cfg.live.lon };
    }
    this.setCameraPlaced(true);
  }

  resetCameraForView() {
    this.initialLive = null;
    this.userNavigated = false;
    this.cameraPlaced = false;
    this.camera = {
      lastFollow: 0,
      lastJump: 0,
      lastPos: null,
      followLon: null,
      lastPhase: null,
      resetKey: null,
      recapture: null,
      focus: null,
      filmChapterIdx: null,
      filmZoom: null,
      filmSetViewAt: 0,
      filmFlyingUntil: 0,
      filmLastCenter: null,
    };
  }

  setCameraPlaced(next) {
    if (this.cameraPlaced === next) return;
    this.cameraPlaced = next;
    this.callbacks.onCameraPlaced?.(next);
  }

  programmaticMove(fn) {
    this.ignoreUserNavigation = true;
    window.clearTimeout(this.ignoreUserNavigationTimer);
    this.ignoreUserNavigationTimer = window.setTimeout(() => {
      this.ignoreUserNavigation = false;
    }, 120);
    fn();
  }

  syncFilmCamera(cfg) {
    const subject = cfg.live;
    if (!subject || !Number.isFinite(subject.lat) || !Number.isFinite(subject.lon)) return;
    const lonCam = cameraLngForBoat(subject.lon, this.camera.followLon);
    this.camera.followLon = lonCam;
    const chapterIdx = Number.isFinite(Number(cfg.filmChapterIdx)) ? Number(cfg.filmChapterIdx) : 0;
    if (this.camera.filmZoom == null || this.camera.filmChapterIdx !== chapterIdx) {
      this.camera.filmZoom = filmChapterZoom(this.map, cfg.filmLeg);
    }
    let next;
    this.programmaticMove(() => {
      next = applyFilmCamera(this.map, {
        chapterIdx,
        lastChapterIdx: this.camera.filmChapterIdx,
        lat: subject.lat,
        lon: lonCam,
        heading: subject.bearing,
        zoom: this.camera.filmZoom,
        now: Date.now(),
        lastSetViewAt: this.camera.filmSetViewAt || 0,
        flyingUntil: this.camera.filmFlyingUntil || 0,
        lastCenter: this.camera.filmLastCenter,
      });
    });
    this.camera.filmChapterIdx = next.lastChapterIdx;
    this.camera.filmSetViewAt = next.lastSetViewAt;
    this.camera.filmFlyingUntil = next.flyingUntil || 0;
    this.camera.filmLastCenter = next.lastCenter ?? this.camera.filmLastCenter;
    this.camera.lastFollow = Date.now();
  }

  syncCamera(cast, snapshot) {
    const cfg = this.config;
    if (cfg.filmActive) {
      this.syncFilmCamera(cfg);
      return;
    }
    const liveMode = cfg.isSuivre && cfg.live && !cfg.previewing;
    const subject = liveMode ? cfg.live : cast?.follow;
    const enabled = Boolean(
      cfg.sceneReady
      && (
        (cfg.cameraFollow && (cast?.follow || liveMode))
        || (cfg.isSimulation && cfg.cameraFocusToken > 0 && cast?.follow)
      )
      && subject?.lat != null
      && subject?.lon != null,
    );
    if (!enabled) return;
    const resetKey = `${cfg.view}-${cfg.sceneReady ? "ready" : "load"}-${cfg.cinemaRecapture}`;
    if (this.camera.resetKey !== resetKey) {
      this.camera.lastFollow = 0;
      this.camera.lastJump = 0;
      this.camera.lastPos = null;
      this.camera.followLon = null;
      this.camera.lastPhase = null;
      this.camera.focus = cfg.cameraFocusToken;
      this.camera.resetKey = resetKey;
    }
    const lonCam = cameraLngForBoat(subject.lon, this.camera.followLon);
    this.camera.followLon = lonCam;
    const previous = this.camera.lastPos;
    const movedNm = previous ? haversineNm(previous.lat, previous.lon, subject.lat, subject.lon) : 0;
    this.camera.lastPos = { lat: subject.lat, lon: subject.lon };
    const zoom = zoomForRemaining(cfg.remainingNm ?? snapshot.sailTotalNm);
    const tokenJump = !liveMode && snapshot.jumpToken && snapshot.jumpToken !== this.camera.lastJump;
    if (tokenJump) this.camera.lastJump = snapshot.jumpToken;
    const phaseChanged = cast?.phase && cast.phase !== this.camera.lastPhase;
    if (cast?.phase) this.camera.lastPhase = cast.phase;
    const recapture = cfg.cinemaRecapture !== this.camera.recapture;
    if (recapture) this.camera.recapture = cfg.cinemaRecapture;
    const focus = cfg.cameraFocusToken !== this.camera.focus;
    if (focus) this.camera.focus = cfg.cameraFocusToken;
    if (isAirPhase(cast?.phase) && cast?.hopFrom && cast?.hopTo) {
      if (cfg.cameraFollow && (phaseChanged || tokenJump || recapture)) {
        const lonA = cameraLngForBoat(cast.hopFrom.lon, this.camera.followLon);
        const lonB = cameraLngForBoat(cast.hopTo.lon, lonA);
        this.camera.followLon = lonB;
        this.programmaticMove(() => this.map.fitBounds(
          [[cast.hopFrom.lat, lonA], [cast.hopTo.lat, lonB]],
          { padding: [72, 96], maxZoom: 3.15, animate: true, duration: 0.9 },
        ));
        this.camera.lastFollow = Date.now();
        this.camera.lastPos = null;
      }
      return;
    }
    if (focus) {
      this.programmaticMove(() => this.map.setView([subject.lat, lonCam], this.map.getZoom(), { animate: false }));
      this.camera.lastFollow = Date.now();
      return;
    }
    if (recapture || previous == null) {
      this.programmaticMove(() => this.map.setView([subject.lat, lonCam], zoom, { animate: false }));
      this.camera.lastFollow = Date.now();
      return;
    }
    if (!cfg.cameraFollow || (!liveMode && !snapshot.playing)) return;
    if (tokenJump || phaseChanged || movedNm >= TELEPORT_NM) {
      this.programmaticMove(() => this.map.flyTo(
        [subject.lat, lonCam],
        zoom,
        { duration: movedNm >= TELEPORT_NM || phaseChanged ? 0.7 : 1.05 },
      ));
      this.camera.lastFollow = Date.now();
      return;
    }
    const now = Date.now();
    if (now - this.camera.lastFollow < 700) return;
    this.camera.lastFollow = now;
    const currentZoom = this.map.getZoom();
    this.programmaticMove(() => this.map.setView(
      [subject.lat, lonCam],
      Math.abs(currentZoom - zoom) >= 1.25 ? zoom : currentZoom,
      { animate: true, duration: 0.55 },
    ));
  }

  renderDynamic(snapshot) {
    this.currentPlayback = snapshot;
    const cast = interpolateCast(this.config.flat, snapshot.nm, { stops: this.config.stops });
    this.currentCast = cast;
    const liveMode = this.config.isSuivre && this.config.live && !this.config.previewing;
    const sailNm = liveMode ? (this.config.live.sailNm ?? 0) : (cast?.sailNm ?? 0);
    this.syncWake(sailNm, this.config.sceneReady && !this.config.drawingMode && !this.config.customRoute);
    this.syncMarkers(cast, snapshot);
    this.syncAirHop(cast);
    this.syncCamera(cast, snapshot);
  }

  syncDynamicWorldCopies() {
    if (!this.currentPlayback) return;
    this.syncMarkers(this.currentCast, this.currentPlayback);
  }

  publishPlayback(snapshot) {
    this.callbacks.onPlayback?.({ ...snapshot, cast: this.currentCast });
  }

  dispose() {
    this.eventBubble?.dispose();
    this.eventBubble = null;
    this.escalePopup?.dispose();
    this.escalePopup = null;
    this.clearBriefingFocus();
    window.clearTimeout(this.waypointTimer);
    window.clearTimeout(this.ignoreUserNavigationTimer);
    this.playback.destroy();
    this.map.off("zoomanim", this.onZoomAnim);
    this.map.off("zoomend", this.onZoomEnd);
    this.map.off("moveend", this.onMoveEnd);
    this.map.off("zoomstart", this.onUserNavigation);
    this.map.off("dragstart", this.onUserNavigation);
    this.layers.clear();
    this.markerSets.forEach((markers) => markers.forEach((marker) => marker.remove()));
    this.markerSets.clear();
    this.waypointMarkers.clear();
    this.divIconCache.clear();
    this.baseLayer?.remove();
    this.map.remove();
  }
}
