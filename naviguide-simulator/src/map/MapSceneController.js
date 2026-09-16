import L from "leaflet";
import { catamaranSvg } from "../engine/catamaranIcon.js";
import { interpolateCast, isAirPhase } from "../engine/filmCast.js";
import { wakeCursorAt } from "../engine/filmWake.js";
import { haversineNm, splitAntimeridianCoords, unwrapLon, worldCopyCoords } from "../utils/geo.js";
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
import { markerOffsetDelay } from "../hooks/useMarkerOffsets.js";
import { createPanes } from "../layers/layerOrder.js";
import {
  ROUTE_CASING_COLOR,
  ROUTE_CASING_WEIGHT,
  ROUTE_MAIN_WEIGHT,
  TILE_URLS,
  WAKE_DONE_COLOR,
  WAKE_REST_COLOR,
} from "../layers/styles.js";
import { SceneLayerRegistry } from "./SceneLayerRegistry.js";
import { ScenePlaybackController } from "./ScenePlaybackController.js";

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
  for (const part of splitAntimeridianCoords(coords)) {
    for (const copy of worldCopyCoords(part)) {
      L.polyline(copy.map(([lon, lat]) => [lat, lon]), {
        color,
        weight,
        dashArray: dash,
        pane,
        interactive: true,
      }).addTo(group);
    }
  }
}

function staticWakeParts(flat) {
  const points = flat?.points || [];
  const parts = [];
  const partByPoint = new Array(points.length);
  let current = null;
  points.forEach((point, index) => {
    if (!Number.isFinite(point?.lon) || !Number.isFinite(point?.lat)) return;
    const previous = index > 0 ? points[index - 1] : null;
    const crossesAntimeridian = Boolean(current?.length && previous && Math.abs(point.lon - previous.lon) > 180);
    if (!current || point.jump || crossesAntimeridian) {
      current = [];
      parts.push(current);
    }
    current.push([point.lon, point.lat]);
    partByPoint[index] = parts.length - 1;
  });
  return { points, parts, partByPoint };
}

function createWorldLines(group, style) {
  return WORLD_OFFSETS.map(() => L.polyline([], style).addTo(group));
}

function clearDoneLines(lines) {
  lines.forEach((worldLines) => worldLines.forEach((line) => line.setLatLngs([])));
}

function appendDonePoint(geometry, index) {
  const point = geometry.points[index];
  const partIndex = geometry.partByPoint[index];
  if (!point || partIndex == null) return;
  geometry.doneLines[partIndex].forEach((line, worldIndex) => {
    line.addLatLng([point.lat, point.lon + WORLD_OFFSETS[worldIndex]]);
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
export class MapSceneController {
  static mount(container, callbacks) {
    const map = L.map(container, {
      center: [22, 5],
      zoom: 2,
      zoomSnap: 0.25,
      minZoom: 2,
      maxZoom: 18,
      worldCopyJump: false,
    });
    createPanes(map);
    return new MapSceneController(map, callbacks);
  }

  constructor(map, callbacks = {}) {
    this.map = map;
    this.callbacks = callbacks;
    this.layers = new SceneLayerRegistry();
    this.config = {};
    this.baseLayer = L.tileLayer(TILE_URLS.dark, { attribution: "Leaflet | Tiles © Esri" }).addTo(map);
    this.wakeGeometry = null;
    this.markerSets = new Map();
    this.waypointMarkers = new Map();
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
    };
    this.playback = new ScenePlaybackController({
      onFrame: (snapshot) => this.renderDynamic(snapshot),
      onPublish: (snapshot) => this.publishPlayback(snapshot),
    });
    this.onMoveEnd = () => {
      this.syncDynamicWorldCopies();
      this.scheduleWaypoints();
    };
    this.onUserNavigation = () => {
      if (this.ignoreUserNavigation) return;
      this.userNavigated = true;
      this.map.stop();
      this.callbacks.onManualNavigation?.();
    };
    map.on("moveend", this.onMoveEnd);
    map.on("zoomstart", this.onUserNavigation);
    map.on("dragstart", this.onUserNavigation);
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
    };
  }

  setCallbacks(callbacks) {
    this.callbacks = callbacks;
  }

  update(next) {
    const previous = this.config;
    const previousView = previous.view;
    this.config = { ...this.config, ...next };
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
  }

  syncBaseLayer() {
    const url = this.config.isLightMode ? TILE_URLS.light : TILE_URLS.dark;
    if (this.baseLayer?._naviguideUrl === url) return;
    this.baseLayer?.remove();
    this.baseLayer = L.tileLayer(url, { attribution: "Leaflet | Tiles © Esri" }).addTo(this.map);
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
      splitAntimeridianCoords(coords).forEach((part) => {
        L.polyline(part.map(([lon, lat]) => [lat, lon]), { ...style, pane: "route" }).addTo(group);
      });
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
    if (!previous || !following || following.jump || !samePart) {
      setWakeTail(geometry.tailLines, null, null);
      return;
    }
    const span = (following.cumNm ?? 0) - (previous.cumNm ?? 0);
    const ratio = span > 0 ? Math.max(0, Math.min(1, (target - (previous.cumNm ?? 0)) / span)) : 0;
    setWakeTail(geometry.tailLines, previous, {
      lon: previous.lon + ratio * (following.lon - previous.lon),
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
  }

  syncMarkers(cast, snapshot) {
    const cfg = this.config;
    const ready = Boolean(cfg.sceneReady && !cfg.drawingMode);
    const liveMode = cfg.isSuivre && cfg.live && !cfg.previewing;
    this.syncMarker("simulation", {
      visible: ready && cfg.isSimulation && Boolean(cast?.main),
      ...cast?.main,
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
      visible: ready && cfg.isSuivre && cfg.previewing && Boolean(cast?.main),
      ...cast?.main,
      className: "catamaran-divicon catamaran-divicon--ghost",
      html: catamaranSvg(0),
    });
    this.syncMarker("side", {
      visible: ready && Boolean(cast?.side?.visible),
      ...cast?.side,
      className: "catamaran-divicon catamaran-divicon--side",
      html: catamaranSvg(0),
    });
    this.syncMarker("plane", {
      visible: ready && Boolean(cast?.plane?.visible),
      ...cast?.plane,
      className: "plane-divicon",
      html: planeHtml(),
    });
    const drawBoat = cfg.drawnSegments?.length >= 1 ? cfg.drawnPoints?.at(-1) : null;
    this.syncMarker("drawing", {
      visible: Boolean(cfg.drawingMode && drawBoat),
      ...drawBoat,
      bearing: 0,
      className: "catamaran-divicon catamaran-divicon--draw",
      html: catamaranSvg(0),
    });
  }

  syncAirHop(cast) {
    const visible = isAirPhase(cast?.phase);
    if (!visible || !cast?.hopFrom || !cast?.hopTo) {
      this.layers.remove("air-hop");
      return;
    }
    const lonB = unwrapLon(cast.hopFrom.lon, cast.hopTo.lon);
    this.layers.update(
      "air-hop",
      () => L.polyline([], {
        color: "#67e8f9",
        weight: 2,
        dashArray: "7 9",
        opacity: 0.8,
        pane: "route",
        interactive: false,
      }).addTo(this.map),
      (line) => line.setLatLngs([
        [cast.hopFrom.lat, cast.hopFrom.lon],
        [cast.hopTo.lat, lonB],
      ]),
    );
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
    source.forEach((point, index) => {
      const srcs = waypointFlagSrcs(point);
      if (!srcs.length && !cfg.drawingMode) return;
      const offset = offsets[index] || [0, 0];
      const html = srcs.length
        ? flagMarkerHtml(srcs, offset)
        : `<div style="width:10px;height:10px;border-radius:50%;background:${index === 0 ? "#22c55e" : "#e2e8f0"};border:2px solid #0f172a"></div>`;
      const metrics = srcs.length ? flagIconMetrics(srcs) : { iconSize: [24, 24], iconAnchor: [12, 12] };
      for (const [copyIndex, lng] of markerWorldLngs(point.lon, this.map.getCenter()?.lng).entries()) {
        const key = `${cfg.drawingMode ? "draw" : "route"}:${index}:${copyIndex}`;
        expected.add(key);
        const iconKey = `${html}|${metrics.iconSize.join(",")}|${metrics.iconAnchor.join(",")}`;
        let marker = this.waypointMarkers.get(key);
        if (!marker) {
          marker = L.marker([point.lat, lng], {
            icon: L.divIcon({ className: "flag-divicon", html, iconSize: metrics.iconSize, iconAnchor: metrics.iconAnchor }),
            interactive: true,
          }).addTo(group);
          marker.on("mouseover", () => this.callbacks.onWaypointHover?.(marker._naviguideWaypoint));
          marker.on("mouseout", () => this.callbacks.onWaypointHover?.(null));
          marker.on("click", (event) => {
            if (!marker._naviguideDrawing) return;
            L.DomEvent.stopPropagation(event);
            this.callbacks.onDrawingWaypointClick?.(marker._naviguideWaypoint, marker._naviguideIndex);
          });
          this.waypointMarkers.set(key, marker);
        }
        marker._naviguideWaypoint = point;
        marker._naviguideDrawing = cfg.drawingMode;
        marker._naviguideIndex = index;
        marker.setLatLng([point.lat, lng]);
        if (marker._naviguideIconKey !== iconKey) {
          marker.setIcon(L.divIcon({
            className: "flag-divicon",
            html,
            iconSize: metrics.iconSize,
            iconAnchor: metrics.iconAnchor,
          }));
          marker._naviguideIconKey = iconKey;
        }
      }
    });
    this.waypointMarkers.forEach((marker, key) => {
      if (expected.has(key)) return;
      group.removeLayer(marker);
      this.waypointMarkers.delete(key);
    });
  }

  scheduleWaypoints() {
    if (!this.config.points?.length && !this.config.drawnPoints?.length) return;
    window.clearTimeout(this.waypointTimer);
    this.waypointTimer = window.setTimeout(() => {
      this.waypointsDirty = true;
      this.syncWaypoints();
    }, markerOffsetDelay(this.config.cameraFollow));
  }

  syncInitialCamera() {
    const cfg = this.config;
    if (!cfg.routeReady || !cfg.flat?.points?.length) {
      this.setCameraPlaced(false);
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

  syncCamera(cast, snapshot) {
    const cfg = this.config;
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
    window.clearTimeout(this.waypointTimer);
    window.clearTimeout(this.ignoreUserNavigationTimer);
    this.playback.destroy();
    this.map.off("moveend", this.onMoveEnd);
    this.map.off("zoomstart", this.onUserNavigation);
    this.map.off("dragstart", this.onUserNavigation);
    this.layers.clear();
    this.markerSets.forEach((markers) => markers.forEach((marker) => marker.remove()));
    this.markerSets.clear();
    this.waypointMarkers.clear();
    this.baseLayer?.remove();
    this.map.remove();
  }
}
