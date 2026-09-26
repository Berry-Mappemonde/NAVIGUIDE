export const PROFILES = [
  { id: "real", labelKey: "speedReal" },
  { id: "read", labelKey: "speedRead" },
  { id: "normal", labelKey: "speedNormal" },
  { id: "fast", labelKey: "speedFast" },
];

const GFS_SOURCE_RE = /gfs|om-forecast|open-?meteo/i;

export function nextFilmSpeed(current) {
  const i = PROFILES.findIndex((p) => p.id === current);
  if (i < 0) return PROFILES[0].id;
  return PROFILES[(i + 1) % PROFILES.length].id;
}

/** GFS du *point* : régime prévision, ou une source GFS / om-forecast / Open-Meteo.
 *  `weatherLine` (mention globale « GFS + GFS-Wave (Open-Meteo) ») n'est pas une preuve. */
export function weatherUsesGfs({ regime, sources }) {
  if (regime === "forecast") return true;
  return (Array.isArray(sources) ? sources : []).some((s) => GFS_SOURCE_RE.test(String(s || "")));
}

export function clockRegimeText({ regime, sources, spread, t, lang = "fr" }) {
  const climo = regime === "climatology";
  const gfs = weatherUsesGfs({ regime, sources });
  if (climo && gfs) return t("clockWeatherClimoGfs");
  if (climo) return t("clockRegimeClimatology");
  if (regime === "hindcast") {
    const name = t("clockRegimeHindcast");
    const n = Array.isArray(sources) ? sources.length : 0;
    const loc = lang === "en" ? "en-US" : "fr-FR";
    if (n > 0 && Number.isFinite(Number(spread))) {
      const sp = Number(spread).toLocaleString(loc, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
      return `${name} · ${t("clockRegimeSources", { n, spread: sp })}`;
    }
    if (n > 0) return `${name} · ${t("clockRegimeSourcesPlain", { n })}`;
    return name;
  }
  if (gfs) return t("clockWeatherGfs");
  if (regime === "forecast") return t("clockRegimeForecast");
  return "";
}

export function clockWeatherTooltip({ sources, spread, weatherLine, regimeTitle, t, lang = "fr" }) {
  const bits = [];
  if (weatherLine) bits.push(weatherLine);
  const list = Array.isArray(sources) ? sources.filter(Boolean) : [];
  if (list.length) bits.push(list.join(" · "));
  if (list.length && Number.isFinite(Number(spread))) {
    const loc = lang === "en" ? "en-US" : "fr-FR";
    const sp = Number(spread).toLocaleString(loc, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    bits.push(t("clockRegimeSources", { n: list.length, spread: sp }));
  }
  if (regimeTitle) bits.push(regimeTitle);
  return bits.filter(Boolean).join(" · ");
}
