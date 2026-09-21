import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { featuresToSegments } from "../utils/geo.js";
import { isAirSegment } from "../utils/berryLegs.js";
import { useToggleLayers } from "../layers/useToggleLayers.js";
import { useClimatologyLayer } from "../layers/useClimatologyLayer.js";
import { useGribCorridorLayer } from "../layers/useGribCorridorLayer.js";
import { useRouteLayer } from "../layers/useRouteLayer.js";
import { MapSceneController } from "./MapSceneController.js";

function pointToSegmentPx(map, lat, lon, coords) {
  const point = map.latLngToLayerPoint([lat, lon]);
  let best = Infinity;
  for (let index = 0; index < coords.length - 1; index += 1) {
    const [lon1, lat1] = coords[index];
    const [lon2, lat2] = coords[index + 1];
    const from = map.latLngToLayerPoint([lat1, lon1]);
    const to = map.latLngToLayerPoint([lat2, lon2]);
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const lengthSq = dx * dx + dy * dy;
    const ratio = lengthSq
      ? Math.max(0, Math.min(1, ((point.x - from.x) * dx + (point.y - from.y) * dy) / lengthSq))
      : 0;
    best = Math.min(best, Math.hypot(point.x - (from.x + ratio * dx), point.y - (from.y + ratio * dy)));
  }
  return best;
}

/**
 * React boundary for the map. Its controller owns all mobile Leaflet objects;
 * the root only receives commands and a HUD snapshot at a bounded cadence.
 */
export function MapScene({
  scene,
  gateRef,
  onReady,
  onPlayback,
  onLayerState,
  onClimatologyState,
  onFeature,
  onCameraPlaced,
  onManualNavigation,
  onDrawingClick,
  onRouteClick,
  onBoatDrag,
  onCoordinatesCopied,
  onWaypointHover,
  onDrawingWaypointClick,
  onWaypointClick,
}) {
  const containerRef = useRef(null);
  const controllerRef = useRef(null);
  const mapRef = useRef(null);
  const [mapReady, setMapReady] = useState(0);
  const callbacksRef = useRef({});
  callbacksRef.current = {
    onReady,
    onPlayback,
    onCameraPlaced,
    onManualNavigation,
    onDrawingClick,
    onRouteClick,
    onBoatDrag,
    onCoordinatesCopied,
    onWaypointHover,
    onDrawingWaypointClick,
    onWaypointClick,
  };

  useEffect(() => {
    if (!containerRef.current) return undefined;
    const controller = MapSceneController.mount(containerRef.current, {
      onPlayback: (snapshot) => callbacksRef.current.onPlayback?.(snapshot),
      onCameraPlaced: (placed) => callbacksRef.current.onCameraPlaced?.(placed),
      onManualNavigation: () => callbacksRef.current.onManualNavigation?.(),
      onBoatDrag: (position) => callbacksRef.current.onBoatDrag?.(position),
      onWaypointHover: (point) => callbacksRef.current.onWaypointHover?.(point),
      onDrawingWaypointClick: (point, index) => callbacksRef.current.onDrawingWaypointClick?.(point, index),
      onWaypointClick: (point, index) => callbacksRef.current.onWaypointClick?.(point, index),
    });
    controllerRef.current = controller;
    mapRef.current = controller.map;
    // Recette / e2e : le contrôleur de scène est exposé (zoom, carte).
    if (typeof window !== "undefined") window.__naviguideScene = controller;
    setMapReady(1);
    callbacksRef.current.onReady?.(controller.api);
    return () => {
      callbacksRef.current.onReady?.(null);
      if (typeof window !== "undefined" && window.__naviguideScene === controller) {
        delete window.__naviguideScene;
      }
      controller.dispose();
      controllerRef.current = null;
      mapRef.current = null;
    };
  }, []);

  const maritimeLayers = useToggleLayers(mapRef, onFeature, mapReady, gateRef, {
    cameraFollowing: scene.cameraFollow,
  });
  const climoLayer = useClimatologyLayer({
    mapRef,
    mapReady,
    showWind: maritimeLayers.showClimoWind,
    showWave: maritimeLayers.showClimoWave,
    showCurrent: maritimeLayers.showClimoCurrent,
    showCyclones: maritimeLayers.showClimoCyclones,
    month: scene.climoMonth,
    drawing: scene.drawingMode,
    t: scene.t,
  });

  useGribCorridorLayer(mapRef, {
    grib: scene.grib,
    mapReady,
    visible: maritimeLayers.showGrib && scene.isSuivre && scene.gribStatus === "ready",
    whenIso: scene.clockSample?.iso,
    lat: scene.isSuivre ? scene.live?.lat : null,
    lon: scene.isSuivre ? scene.live?.lon : null,
  });
  useRouteLayer(mapRef, {
    segments: scene.segments,
    customRoute: scene.customRoute,
    drawingMode: scene.drawingMode,
    drawnSegments: scene.drawnSegments,
    mapReady,
    visible: Boolean(scene.sceneReady) && !scene.drawingMode,
    paintMain: false,
    clockVertices: scene.clockVertices,
    traveledNm: scene.traveledNm,
  });

  useEffect(() => {
    onLayerState?.(maritimeLayers);
  }, [maritimeLayers, onLayerState]);

  useEffect(() => {
    onClimatologyState?.(climoLayer);
  }, [climoLayer, onClimatologyState]);

  useEffect(() => {
    const controller = controllerRef.current;
    if (!controller || !mapReady) return;
    controller.setCallbacks({
      onPlayback: (snapshot) => callbacksRef.current.onPlayback?.(snapshot),
      onCameraPlaced: (placed) => callbacksRef.current.onCameraPlaced?.(placed),
      onManualNavigation: () => callbacksRef.current.onManualNavigation?.(),
      onBoatDrag: (position) => callbacksRef.current.onBoatDrag?.(position),
      onWaypointHover: (point) => callbacksRef.current.onWaypointHover?.(point),
      onDrawingWaypointClick: (point, index) => callbacksRef.current.onDrawingWaypointClick?.(point, index),
      onWaypointClick: (point, index) => callbacksRef.current.onWaypointClick?.(point, index),
    });
    controller.update(scene);
  }, [mapReady, scene]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return undefined;
    const onClick = (event) => {
      const { lat, lng: lon } = event.latlng;
      if (scene.drawingMode) {
        callbacksRef.current.onDrawingClick?.(lat, lon);
        return;
      }
      const active = scene.customRoute ? featuresToSegments(scene.customRoute) : scene.segments;
      const nearby = active.some((segment) => (
        !isAirSegment(segment)
        && segment.coords?.length > 1
        && pointToSegmentPx(map, lat, lon, segment.coords) < 16
      ));
      if (nearby) callbacksRef.current.onRouteClick?.({ lat, lon });
    };
    const onContextMenu = (event) => {
      L.DomEvent.preventDefault(event);
      callbacksRef.current.onCoordinatesCopied?.(
        `${event.latlng.lat.toFixed(6)}, ${event.latlng.lng.toFixed(6)}`,
      );
    };
    map.on("click", onClick);
    map.on("contextmenu", onContextMenu);
    map.getContainer().style.cursor = scene.drawingMode ? "crosshair" : "";
    return () => {
      map.off("click", onClick);
      map.off("contextmenu", onContextMenu);
      map.getContainer().style.cursor = "";
    };
  }, [mapReady, scene]);

  return <div ref={containerRef} id="simulator-map" style={{ height: "100%", width: "100%" }} />;
}
