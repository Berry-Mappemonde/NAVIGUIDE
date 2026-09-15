/** Deux boutons seulement. Pas de 3ᵉ interrupteur. */
export const VIEW_SUIVRE = "suivre";
export const VIEW_SIMULATION = "simulation";

export function isSuivreView(view) {
  return view === VIEW_SUIVRE;
}

export function isSimulationView(view) {
  return view === VIEW_SIMULATION;
}
