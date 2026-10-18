/** Masque le hero HTML statique (#lcp-hero) une fois la carte prête. */
export function markAppReady() {
  document.documentElement.classList.add("app-ready");
  document.getElementById("lcp-hero")?.setAttribute("aria-hidden", "true");
}
