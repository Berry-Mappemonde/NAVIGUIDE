import { LEAFLET_ATTRIBUTION_BOTTOM_MIN_PX } from "../layers/styles.js";

/** Largeur d’une sidebar (gauche ou droite), en px. */
export const SIDEBAR_WIDTH_PX = 320;

/** Décalage Tailwind `bottom-5` de la barre film (1,25 rem = 20 px). */
export const FILM_BAR_BOTTOM_GAP_PX = 20;

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

/** Hauteur occupée par la barre film (bottom-5 + contenu), selon ses lignes. */
export const FILM_BAR_HEIGHT_PX = Object.freeze({
  hidden: 0,
  compact: 96, // lot O : titre + horloge + piste + une rangée de commandes
  controls: 96, // même rangée compacte en Simulation (pilules text-[9px])
});

/**
 * Variables CSS posées sur la racine : les crédits Leaflet (bas droite)
 * restent dans la carte visible — à gauche du panneau Outils, au-dessus de
 * la barre film — au lieu de transparaître sous un panneau translucide.
 */
export function mapInsetVars({
  sidebarOpen = true,
  toolsOpen = true,
  filmBarVisible = true,
  filmBarControls = false,
} = {}) {
  const insets = filmBarInsets({ sidebarOpen, toolsOpen });
  let bottom = FILM_BAR_HEIGHT_PX.hidden;
  if (filmBarVisible) {
    const bar = filmBarControls ? FILM_BAR_HEIGHT_PX.controls : FILM_BAR_HEIGHT_PX.compact;
    bottom = Math.max(bar + FILM_BAR_BOTTOM_GAP_PX, LEAFLET_ATTRIBUTION_BOTTOM_MIN_PX);
  }
  return {
    "--sim-inset-left": `${insets.left}px`,
    "--sim-inset-right": `${toolsOpen ? insets.right : 0}px`,
    "--sim-inset-bottom": `${bottom}px`,
  };
}
