/**
 * The four themes of the Chart design system (Figma "NAVIGUIDE — visual
 * directions"). Each theme is night or day: day themes run on the light base
 * map and the .light-mode rules, night themes on the dark ones. Colours for
 * the interface live in index.css (`:root[data-ng-theme=…]`); the route is
 * drawn on a canvas, so its colours live here and are mirrored to CSS
 * variables for the legend pills.
 */
import { WAKE_DONE_COLOR, WAKE_REST_COLOR } from "../layers/styles.js";
import { REGIME_COLORS } from "../layers/regimeRoute.js";

export const THEMES = Object.freeze([
  { id: "night", mode: "night", labelKey: "themeNight" },
  { id: "day", mode: "day", labelKey: "themeDay" },
  { id: "watch", mode: "night", labelKey: "themeWatch" },
  { id: "azur", mode: "day", labelKey: "themeAzur" },
]);

export const DEFAULT_THEME = "night";
export const THEME_STORAGE_KEY = "naviguide_theme_v1";

const CHART_ROUTE = Object.freeze({
  sailed: WAKE_DONE_COLOR,
  planned: WAKE_REST_COLOR,
  ...REGIME_COLORS,
});

/**
 * Sailed track, route still to sail, and the three weather regimes of the
 * sailed track (the legend pills use the same values). Night watch follows
 * its cyan accent so amber means caution only; Azur de Berry its azure.
 * `recolor` maps the other fixed route-pane colours (road leg, draft route,
 * isochrones, briefing line) for the theme. On day themes index.css darkens
 * the route canvas so every line keeps 3:1 on the light chart.
 */
export const ROUTE_PALETTES = Object.freeze({
  night: CHART_ROUTE,
  day: CHART_ROUTE,
  watch: Object.freeze({
    sailed: "#3fb6da",
    planned: "#7690a0",
    hindcast: "#5cc7e6",
    forecast: "#9fb4ff",
    climatology: "#b4a9c9",
    recolor: Object.freeze({
      "#e6a84b": "#a3e2f3", // road leg: accent family, not caution amber
      "#fbbf24": "#8ea6b1", // isochrones
      "#22d3ee": "#7fd5ee", // draft route
      "#e0589f": "#3fb6da", // briefing line
    }),
  }),
  azur: Object.freeze({
    sailed: "#1c3f94",
    planned: "#56667f",
    hindcast: "#2c56b8",
    forecast: "#0f7a8a",
    climatology: "#65559a",
    recolor: Object.freeze({
      "#22d3ee": "#2c56b8",
      "#e0589f": "#1c3f94",
    }),
  }),
});

/** A fixed route-pane colour as the theme draws it (unchanged when the theme has no mapping). */
export function themedRouteColor(palette, color) {
  return palette?.recolor?.[String(color).toLowerCase()] || color;
}

export function isTheme(id) {
  return THEMES.some((theme) => theme.id === id);
}

export function isDayTheme(id) {
  return THEMES.find((theme) => theme.id === id)?.mode === "day";
}

export function routePalette(id) {
  return ROUTE_PALETTES[id] || ROUTE_PALETTES[DEFAULT_THEME];
}

/**
 * The Dark/Light switch keeps working next to the theme picker: it keeps the
 * current theme when it already has the wanted mode, otherwise it goes to the
 * Chart night or day theme.
 */
export function themeForMode(current, wantDay) {
  if (isTheme(current) && isDayTheme(current) === Boolean(wantDay)) return current;
  return wantDay ? "day" : "night";
}

export function readStoredTheme(storage = globalThis.localStorage) {
  try {
    const id = storage?.getItem(THEME_STORAGE_KEY);
    return isTheme(id) ? id : DEFAULT_THEME;
  } catch {
    return DEFAULT_THEME;
  }
}

export function storeTheme(id, storage = globalThis.localStorage) {
  try {
    if (isTheme(id)) storage?.setItem(THEME_STORAGE_KEY, id);
  } catch {
    /* private mode or storage blocked: the theme still applies for this visit */
  }
}

/** Marks <html> with the theme and mirrors the route colours to CSS variables. */
export function applyThemeToDocument(id, doc = globalThis.document) {
  const root = doc?.documentElement;
  if (!root) return;
  root.dataset.ngTheme = id;
  const palette = routePalette(id);
  for (const [name, color] of Object.entries(palette)) {
    if (typeof color === "string") root.style.setProperty(`--route-${name}`, color);
  }
}
