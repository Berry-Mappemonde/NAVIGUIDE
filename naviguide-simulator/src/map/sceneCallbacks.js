/**
 * Rappels confiés au contrôleur de scène. Chacun relit le gestionnaire React
 * courant au moment de l'appel. Les racines React des popups (bulle d'événement)
 * les appellent via `window.__naviguideScene.callbacks` : tout rappel qu'elles
 * utilisent doit figurer ici, sinon le bouton ne fait rien.
 */
export function sceneCallbacks(callbacksRef) {
  const current = () => callbacksRef.current || {};
  return {
    onPlayback: (snapshot) => current().onPlayback?.(snapshot),
    onCameraPlaced: (placed) => current().onCameraPlaced?.(placed),
    onManualNavigation: () => current().onManualNavigation?.(),
    onBoatDrag: (position) => current().onBoatDrag?.(position),
    onWaypointHover: (point) => current().onWaypointHover?.(point),
    onDrawingWaypointClick: (point, index) => current().onDrawingWaypointClick?.(point, index),
    onWaypointClick: (point, index) => current().onWaypointClick?.(point, index),
    onBriefingFocus: (entity) => current().onBriefingFocus?.(entity),
  };
}
