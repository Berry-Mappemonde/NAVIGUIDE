/** Touche C seule = Cinéma. ⌘C / Ctrl+C restent Copier. */
export function isCinemaKey(e) {
  if (!e || e.code !== "KeyC") return false;
  if (e.metaKey || e.ctrlKey) return false;
  if (e.altKey) return false;
  return true;
}
