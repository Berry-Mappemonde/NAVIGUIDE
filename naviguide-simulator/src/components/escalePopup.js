export const ESCALE_POPUP_MAX_WIDTH = 340;
export const ESCALE_POPUP_MAX_HEIGHT = 260;

const ESCALE_CLOSE_SEL = "[data-testid='escale-close']";

/** Suivre, Revoir, ou film en cours : la fiche d'escale doit disparaître (RA5). */
export function shouldCloseEscaleSheet({
  nextView,
  replayActive = false,
  replayStarting = false,
} = {}) {
  if (replayActive || replayStarting) return true;
  return nextView === "suivre";
}

export function isEscaleCloseClick(event) {
  return Boolean(event?.target?.closest?.(ESCALE_CLOSE_SEL));
}

/** Ferme l'état React ; ignore le clic drapeau qui suivrait le retrait du popup. */
export function requestEscaleClose(sheet) {
  globalThis.__naviguideIgnoreEscaleOpen = Date.now() + 400;
  sheet?.onClose?.();
  return true;
}

/** Hors dessin : ouvre la fiche. En dessin : le clic reste au mode tracer. */
export function handleWaypointMarkerClick(drawing, point, index, callbacks) {
  if (drawing) {
    callbacks?.onDrawingWaypointClick?.(point, index);
    return "draw";
  }
  const ignoreUntil = Number(globalThis.__naviguideIgnoreEscaleOpen);
  if (Number.isFinite(ignoreUntil) && ignoreUntil > Date.now()) {
    return "ignore";
  }
  callbacks?.onWaypointClick?.(point, index);
  return "sheet";
}

export function createEscalePopupOptions() {
  return {
    autoPan: true,
    closeButton: false,
    className: "escale-popup",
    maxWidth: ESCALE_POPUP_MAX_WIDTH,
    minWidth: 220,
    closeOnClick: false,
    autoClose: false,
    keepInView: false,
  };
}

export function ensureEscalePopup(popup, L) {
  return popup || L.popup(createEscalePopupOptions());
}

function sameStop(point, stop) {
  if (!point || !stop) return false;
  if (stop.name && point.name && stop.name === point.name) return true;
  if (!Number.isFinite(stop.lat) || !Number.isFinite(point.lat)) return false;
  if (Math.abs(point.lat - stop.lat) > 1e-4) return false;
  const a = Number(point.lon);
  const b = Number(stop.lon);
  if (!Number.isFinite(a) || !Number.isFinite(b)) return false;
  return Math.abs(((a - b + 540) % 360) - 180) < 1e-3;
}

/** Copie monde du drapeau la plus proche du centre carte. */
export function findWaypointMarker(scene, stop) {
  const markers = scene?.waypointMarkers;
  if (!markers || !stop) return null;
  const matches = [];
  for (const marker of markers.values()) {
    if (sameStop(marker._naviguideWaypoint, stop)) matches.push(marker);
  }
  if (!matches.length) return null;
  const cam = scene.map?.getCenter?.()?.lng;
  if (!Number.isFinite(cam)) return matches[0];
  return matches.reduce((best, marker) => {
    const lng = marker.getLatLng?.()?.lng;
    const bl = best.getLatLng?.()?.lng;
    if (!Number.isFinite(lng)) return best;
    if (!Number.isFinite(bl)) return marker;
    return Math.abs(lng - cam) < Math.abs(bl - cam) ? marker : best;
  });
}
