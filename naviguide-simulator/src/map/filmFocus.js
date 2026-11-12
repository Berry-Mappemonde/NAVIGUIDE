/**
 * « Voir sur la carte » pendant le film (#102). La caméra du film tient le cadre :
 * le recentrage vise le bateau du film, la caméra reste sur le lieu tant que la
 * bulle est ouverte, puis le film reprend son bateau à son zoom d'avant.
 */

function finitePoint(p) {
  return Number.isFinite(p?.lat) && Number.isFinite(p?.lon) ? { lat: p.lat, lon: p.lon } : null;
}

/** Bateau du film : la pose de la caméra (même copie du monde que le cadre), sinon la position publiée. */
export function filmFocusAnchor(filmPose, film) {
  return finitePoint(filmPose) || finitePoint(film);
}

/** Longitude d'un lieu ramenée dans la copie du monde du bateau, pour un trait court. */
export function lonNearAnchor(lon, anchorLon) {
  if (!Number.isFinite(lon) || !Number.isFinite(anchorLon)) return lon;
  return lon + 360 * Math.round((anchorLon - lon) / 360);
}

/** Un recentrage venu d'ailleurs que la bulle (lien du panneau) rend la caméra au film après ce délai. */
export const FILM_FOCUS_UNBOUND_MS = 8000;
/** Filet : la bulle suit le bateau et peut sortir du cadre ; la caméra ne reste jamais figée plus longtemps. */
export const FILM_FOCUS_BUBBLE_MAX_MS = 20000;

/** Le recentrage vient du bouton de la bulle affichée : le lieu est l'entité même de sa carte. */
export function focusFromBubble(place, shownCard) {
  return Boolean(place && shownCard?.entity === place);
}

/**
 * Ce qu'il faut rendre au film : le zoom et la tenue de zoom d'avant le premier recentrage,
 * même si l'on enchaîne les recentrages. `fromBubble` : la caméra attend la fermeture de la bulle.
 */
export function filmFocusHold(previousHold, { zoom, zoomHold, fromBubble, at }) {
  return {
    zoom: previousHold ? previousHold.zoom : zoom,
    zoomHold: previousHold ? previousHold.zoomHold : (Number.isFinite(zoomHold) ? zoomHold : null),
    fromBubble: Boolean(fromBubble),
    at,
  };
}

/** Le recentrage a fait son temps : 8 s hors bulle, 20 s au plus pour une bulle. */
export function filmFocusExpired(hold, now) {
  if (!hold || !Number.isFinite(hold.at)) return false;
  return now - hold.at >= (hold.fromBubble ? FILM_FOCUS_BUBBLE_MAX_MS : FILM_FOCUS_UNBOUND_MS);
}

/** Zoom à laisser au film quand il s'arrête pendant un recentrage : celui d'avant le recentrage. */
export function filmExitZoomHold(hold) {
  if (!hold) return null;
  if (Number.isFinite(hold.zoomHold)) return hold.zoomHold;
  return Number.isFinite(hold.zoom) ? hold.zoom : null;
}

/** Pose du bateau pendant que la caméra est tenue : position brute du film, rien d'autre ne bouge. */
export function heldFilmPose(previousPose, film, lon) {
  if (!Number.isFinite(film?.lat) || !Number.isFinite(lon)) return previousPose;
  const filmNm = Number(film.filmNm);
  return {
    ...previousPose,
    lat: film.lat,
    lon,
    heading: film.heading ?? film.bearing ?? previousPose?.heading,
    filmNm: Number.isFinite(filmNm) ? filmNm : previousPose?.filmNm,
  };
}

/** Suivi de caméra remis à zéro à la reprise : le prochain pas recadre le bateau au zoom du film. */
export function filmTrackAfterFocus() {
  return {
    filmSetViewAt: 0,
    filmFlyingUntil: 0,
    filmLastCenter: null,
    filmFramesSinceReset: 0,
    filmLastBoat: null,
    filmStillAnchor: null,
  };
}
