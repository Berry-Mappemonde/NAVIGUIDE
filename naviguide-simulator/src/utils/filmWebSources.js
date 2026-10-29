/**
 * Écart n° 43 : provenance Tavily du film rédigé (Revoir → Rédigé).
 * Le serveur range au clic Rédigé le résultat d'une recherche Tavily sur le
 * dernier port du film (`webContext`). On n'affiche que ce qui est servi :
 * port, titres, domaines et liens — jamais un extrait, jamais une source inventée.
 */
const MAX_SOURCES = 3;

function domainOf(url) {
  try {
    const host = new URL(url).hostname.toLowerCase();
    return host.startsWith("www.") ? host.slice(4) : host;
  } catch {
    return "";
  }
}

export function publicFilmWebContext(data) {
  const ctx = data?.webContext;
  if (!ctx || typeof ctx !== "object" || ctx.basis !== "tavily") return null;
  const port = String(ctx.port || "").trim();
  const sources = [];
  for (const row of Array.isArray(ctx.sources) ? ctx.sources : []) {
    const url = String(row?.url || "").trim();
    if (!/^https?:\/\//i.test(url)) continue;
    const domain = String(row?.domain || "").trim() || domainOf(url);
    if (!domain) continue;
    sources.push({ url, domain, title: String(row?.title || "").trim() || domain });
    if (sources.length >= MAX_SOURCES) break;
  }
  if (!port || !sources.length) return null;
  return { port, fetchedAt: ctx.fetchedAt || null, sources };
}
