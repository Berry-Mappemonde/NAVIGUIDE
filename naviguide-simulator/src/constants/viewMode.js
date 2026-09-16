/** Deux boutons seulement. Pas de 3ᵉ interrupteur. */
export const VIEW_SUIVRE = "suivre";
export const VIEW_SIMULATION = "simulation";

export function isSuivreView(view) {
  return view === VIEW_SUIVRE;
}

export function isSimulationView(view) {
  return view === VIEW_SIMULATION;
}

/** Lecture, curseur et sauts sont réservés au film de Simulation. */
export function hasSimulationPlaybackControls(view) {
  return isSimulationView(view);
}
