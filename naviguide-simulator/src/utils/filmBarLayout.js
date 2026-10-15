/** Largeur d’une sidebar (gauche ou droite), en px. */
export const SIDEBAR_WIDTH_PX = 320;

/** Décalage Tailwind `bottom-5` de la barre film (1,25 rem = 20 px). */
export const FILM_BAR_BOTTOM_GAP_PX = 20;

/** Espace entre le bas des crédits Leaflet et le haut de la barre film (lot UI1). */
export const ATTRIBUTION_FILM_GAP_PX = 4;

/**
 * La barre du bas occupe l’espace entre les deux sidebars ouvertes.
 * Si une sidebar se range, la barre s’élargit dans le trou.
 */
export function filmBarInsets({
  sidebarOpen = true,
  toolsOpen = true,
  width = SIDEBAR_WIDTH_PX,
  gutter = 8,
} = {}) {
  return {
    left: sidebarOpen ? width : gutter,
    right: toolsOpen ? width : gutter,
  };
}

/** Hauteur occupée par la barre film (contenu), selon ses lignes — premier rendu seulement. */
export const FILM_BAR_HEIGHT_PX = Object.freeze({
  hidden: 0,
  compact: 96, // lot O : titre + horloge + piste + une rangée de commandes
  controls: 96, // même rangée compacte en Simulation (pilules text-[9px])
});

/**
 * Espace réel du bas de la carte jusqu’au haut de la barre film (ou du
 * bouton « Afficher »). Inclut le `bottom-5` : c’est cette mesure, pas la
 * constante 96, qui positionne les crédits (lot UI1).
 */
export function measureFilmBarOccupiedPx(el, viewportBottom) {
  if (!el || typeof el.getBoundingClientRect !== "function") return 0;
  const top = Number(el.getBoundingClientRect().top);
  if (!Number.isFinite(top)) return 0;
  let bottom = Number(viewportBottom);
  if (!Number.isFinite(bottom)) {
    const root = typeof el.closest === "function" ? el.closest("[data-testid='sim-root']") : null;
    bottom = root
      ? root.getBoundingClientRect().bottom
      : Number(globalThis.innerHeight) || 0;
  }
  return Math.max(0, Math.round(bottom - top));
}

/**
 * Variables CSS posées sur la racine : les crédits Leaflet (bas droite)
 * restent dans la carte visible — à gauche du panneau Outils, juste au-dessus
 * de la barre film (mesure + 4 px), pas sous un panneau translucide.
 */
export function mapInsetVars({
  sidebarOpen = true,
  toolsOpen = true,
  filmBarVisible = true,
  filmBarControls = false,
  filmBarMeasuredPx = null,
} = {}) {
  const insets = filmBarInsets({ sidebarOpen, toolsOpen });
  let bottom = FILM_BAR_HEIGHT_PX.hidden;
  if (filmBarVisible) {
    const fallback = (filmBarControls ? FILM_BAR_HEIGHT_PX.controls : FILM_BAR_HEIGHT_PX.compact)
      + FILM_BAR_BOTTOM_GAP_PX;
    const occupied = Number.isFinite(filmBarMeasuredPx) ? filmBarMeasuredPx : fallback;
    bottom = occupied + ATTRIBUTION_FILM_GAP_PX;
  }
  return {
    "--sim-inset-left": `${insets.left}px`,
    "--sim-inset-right": `${toolsOpen ? insets.right : 0}px`,
    "--sim-inset-bottom": `${bottom}px`,
  };
}
