/** Largeur d’une sidebar (gauche ou droite), en px. */
export const SIDEBAR_WIDTH_PX = 320;

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
