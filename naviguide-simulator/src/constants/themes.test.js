import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  DEFAULT_THEME,
  ROUTE_PALETTES,
  THEMES,
  THEME_STORAGE_KEY,
  applyThemeToDocument,
  isDayTheme,
  readStoredTheme,
  routePalette,
  storeTheme,
  themeForMode,
} from "./themes.js";
import { WAKE_DONE_COLOR, WAKE_REST_COLOR } from "../layers/styles.js";
import { REGIME_COLORS } from "../layers/regimeRoute.js";
import en from "../i18n/en.js";
import fr from "../i18n/fr.js";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "..", "index.css"), "utf8");
const sidebar = readFileSync(join(here, "..", "components", "ToolsSidebar.jsx"), "utf8");

function memoryStorage(initial = {}) {
  const data = { ...initial };
  return { getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = String(v); }, data };
}

function themeBlock(id) {
  const match = css.match(new RegExp(`:root\\[data-ng-theme="${id}"\\] \\{([\\s\\S]*?)\\n\\}`));
  return match ? match[1] : "";
}

function hue(hex) {
  const n = Number.parseInt(hex.slice(1), 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => v / 255);
  const max = Math.max(r, g, b);
  const d = max - Math.min(r, g, b);
  if (!d) return 0;
  const h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return (h * 60 + 360) % 360;
}

describe("themes: the four Chart themes", () => {
  it("are night, day, Night watch and Azur de Berry, Azur being a day theme", () => {
    assert.deepEqual(THEMES.map((t) => t.id), ["night", "day", "watch", "azur"]);
    assert.equal(DEFAULT_THEME, "night");
    assert.equal(isDayTheme("night"), false);
    assert.equal(isDayTheme("watch"), false);
    assert.equal(isDayTheme("day"), true);
    assert.equal(isDayTheme("azur"), true);
  });

  it("have a label in both languages", () => {
    for (const { labelKey } of THEMES) {
      assert.ok(en[labelKey], `en.${labelKey}`);
      assert.ok(fr[labelKey], `fr.${labelKey}`);
    }
    assert.ok(en.themeTitle && fr.themeTitle);
  });

  it("each give the route five colours, the Chart ones being the map constants", () => {
    for (const { id } of THEMES) {
      const palette = routePalette(id);
      assert.deepEqual(Object.keys(palette).sort(), ["climatology", "forecast", "hindcast", "planned", "sailed"]);
      for (const color of Object.values(palette)) assert.match(color, /^#[0-9a-f]{6}$/);
    }
    assert.equal(ROUTE_PALETTES.night.sailed, WAKE_DONE_COLOR);
    assert.equal(ROUTE_PALETTES.night.planned, WAKE_REST_COLOR);
    assert.equal(ROUTE_PALETTES.night.hindcast, REGIME_COLORS.hindcast);
    assert.equal(routePalette("unknown"), ROUTE_PALETTES.night);
  });
});

describe("themes: the Dark/Light switch", () => {
  it("keeps a theme that already has the wanted mode, otherwise goes to Chart night or day", () => {
    assert.equal(themeForMode("night", true), "day");
    assert.equal(themeForMode("day", false), "night");
    assert.equal(themeForMode("watch", true), "day");
    assert.equal(themeForMode("azur", false), "night");
    assert.equal(themeForMode("azur", true), "azur");
    assert.equal(themeForMode("watch", false), "watch");
  });
});

describe("themes: remembered per browser", () => {
  it("reads and writes one key, ignoring unknown values and blocked storage", () => {
    const storage = memoryStorage();
    assert.equal(readStoredTheme(storage), "night");
    storeTheme("watch", storage);
    assert.equal(storage.data[THEME_STORAGE_KEY], "watch");
    assert.equal(readStoredTheme(storage), "watch");
    storeTheme("neon", storage);
    assert.equal(readStoredTheme(storage), "watch");
    assert.equal(readStoredTheme(memoryStorage({ [THEME_STORAGE_KEY]: "neon" })), "night");
    const blocked = { getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); } };
    assert.equal(readStoredTheme(blocked), "night");
    assert.doesNotThrow(() => storeTheme("day", blocked));
  });

  it("marks <html> and mirrors the route colours for the legend pills", () => {
    const props = {};
    const doc = { documentElement: { dataset: {}, style: { setProperty: (k, v) => { props[k] = v; } } } };
    applyThemeToDocument("azur", doc);
    assert.equal(doc.documentElement.dataset.ngTheme, "azur");
    assert.equal(props["--route-sailed"], ROUTE_PALETTES.azur.sailed);
    assert.equal(props["--route-hindcast"], ROUTE_PALETTES.azur.hindcast);
    assert.doesNotThrow(() => applyThemeToDocument("night", null));
  });
});

describe("themes: CSS", () => {
  it("names the semantic tokens after the Figma variables and exposes them to Tailwind", () => {
    for (const token of ["surface-panel", "surface-raised", "line-hairline", "text-primary", "text-muted",
      "accent-fill", "accent-on", "accent-line", "accent-text", "accent-soft", "status-ok", "status-caution", "status-danger"]) {
      assert.match(css, new RegExp(`--${token}:`), token);
      assert.match(css, new RegExp(`--color-${token}: var\\(--${token}\\)`), `tailwind ${token}`);
    }
    assert.match(css, /--font-sans: var\(--font-ui\);/);
    assert.match(css, /--font-serif: var\(--font-display\);/);
  });

  it("Night watch: amber means caution only, the accent is another hue", () => {
    const block = themeBlock("watch");
    const accent = block.match(/--course-500: (#[0-9a-f]{6})/)?.[1];
    const caution = block.match(/--caution-400: (#[0-9a-f]{6})/)?.[1];
    assert.ok(accent && caution, "watch block defines its accent and caution");
    const distance = Math.abs(hue(accent) - hue(caution));
    assert.ok(Math.min(distance, 360 - distance) > 90, `accent ${accent} vs caution ${caution}`);
    assert.match(block, /IBM Plex Sans/);
  });

  it("Azur de Berry only restyles the day palette, with its own fonts", () => {
    assert.match(themeBlock("azur"), /Fraunces/);
    assert.match(themeBlock("azur"), /Public Sans/);
    assert.match(css, /:root\[data-ng-theme="azur"\] \.light-mode \{[\s\S]*?--ng-light-accent: #1c3f94;/);
  });

  it("the tools panel offers the four themes as a radio group", () => {
    assert.match(sidebar, /role="radiogroup"/);
    assert.match(sidebar, /data-testid=\{`theme-\$\{id\}`\}/);
    assert.match(sidebar, /aria-checked=\{theme === id\}/);
  });
});
