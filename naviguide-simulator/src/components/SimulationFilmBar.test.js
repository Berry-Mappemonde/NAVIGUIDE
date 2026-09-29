import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  clockRegimeText,
  clockWeatherTooltip,
  nextFilmSpeed,
  PROFILES,
  weatherUsesGfs,
} from "./filmBarClock.js";

const here = dirname(fileURLToPath(import.meta.url));
const bar = readFileSync(join(here, "SimulationFilmBar.jsx"), "utf8");

const DICT = {
  clockRegimeHindcast: "hindcast",
  clockRegimeForecast: "prévision",
  clockRegimeClimatology: "climatologie",
  clockWeatherGfs: "GFS",
  clockWeatherClimoGfs: "climatologie + GFS",
  clockRegimeSources: "{n} sources ±{spread} kn",
  clockRegimeSourcesPlain: "{n} sources",
};

function t(key, vars = {}) {
  return Object.entries(vars).reduce(
    (s, [k, v]) => s.replace(`{${k}}`, v),
    DICT[key] ?? key,
  );
}

describe("barre film (lot RB4) — vitesse cyclique", () => {
  it("4 clics : réel → lecture → normale → accélérée → réel", () => {
    assert.deepEqual(PROFILES.map((p) => p.id), ["real", "read", "normal", "fast"]);
    let id = "real";
    id = nextFilmSpeed(id);
    assert.equal(id, "read");
    id = nextFilmSpeed(id);
    assert.equal(id, "normal");
    id = nextFilmSpeed(id);
    assert.equal(id, "fast");
    id = nextFilmSpeed(id);
    assert.equal(id, "real");
  });

  it("un seul bouton de vitesse, plus de pilules", () => {
    assert.equal((bar.match(/data-testid="film-speed"/g) || []).length, 1);
    assert.doesNotMatch(bar, /PROFILES\.map/);
    assert.match(bar, /onClick=\{\(\) => onProfile\(nextFilmSpeed\(profile\)\)\}/);
  });
});

describe("barre film (lot RC1) — libellé météo du point", () => {
  it("climatology + weatherLine global + sources vides → climatologie seule", () => {
    assert.equal(
      clockRegimeText({
        regime: "climatology",
        sources: [],
        weatherLine: "GFS + GFS-Wave (Open-Meteo)",
        t,
      }),
      "climatologie",
    );
    assert.equal(
      weatherUsesGfs({
        regime: "climatology",
        sources: [],
        weatherLine: "GFS + GFS-Wave (Open-Meteo)",
      }),
      false,
    );
  });

  it("climatology + sources om-forecast → climatologie + GFS", () => {
    assert.equal(
      clockRegimeText({
        regime: "climatology",
        sources: ["om-forecast"],
        weatherLine: "",
        t,
      }),
      "climatologie + GFS",
    );
    assert.equal(
      weatherUsesGfs({ regime: "climatology", sources: ["om-forecast"] }),
      true,
    );
  });

  it("un seul : climatologie, ou GFS, ou hindcast (N sources ±spread inchangé)", () => {
    assert.equal(
      clockRegimeText({ regime: "climatology", sources: [], weatherLine: "", t }),
      "climatologie",
    );
    assert.equal(
      clockRegimeText({
        regime: "forecast",
        sources: ["om-forecast"],
        weatherLine: "GFS + GFS-Wave (Open-Meteo)",
        t,
      }),
      "GFS",
    );
    const hindcast = clockRegimeText({
      regime: "hindcast",
      sources: ["om-era5"],
      spread: 1.5,
      t,
      lang: "fr",
    });
    assert.match(hindcast, /hindcast/);
    assert.match(hindcast, /1 sources/);
    assert.match(hindcast, /±1[,.]5 kn/);
    assert.equal(weatherUsesGfs({ regime: "climatology", sources: [], weatherLine: "" }), false);
    assert.equal(weatherUsesGfs({ regime: "forecast", sources: [], weatherLine: "" }), true);
  });

  it("détail des modèles en info-bulle, pas dans le libellé", () => {
    const both = clockRegimeText({
      regime: "climatology",
      sources: ["om-forecast"],
      weatherLine: "GFS + GFS-Wave (Open-Meteo)",
      t,
    });
    assert.equal(both, "climatologie + GFS");
    assert.doesNotMatch(both, /GFS-Wave|Open-Meteo|sources/);
    const tip = clockWeatherTooltip({
      sources: ["atlas"],
      weatherLine: "GFS + GFS-Wave (Open-Meteo)",
      regimeTitle: "hindcast · prévision · climatologie",
      t,
    });
    assert.match(tip, /GFS-Wave/);
    assert.match(tip, /Open-Meteo/);
  });

  it("weather-line reste vide ; weatherUsesGfs n'ouvre plus weatherLine", () => {
    const clockSrc = readFileSync(join(here, "filmBarClock.js"), "utf8");
    assert.doesNotMatch(clockSrc, /\/gfs\/i\.test\(weatherLine\)/);
    assert.match(bar, /<span data-testid="weather-line" className="text-cyan-200\/85"><\/span>/);
  });
});

describe("barre film (lot RG9) — sous-titre = phrase en cours", () => {
  it("garde le sous-titre et met le lieu en avant, sans rangée ajoutée", () => {
    assert.match(bar, /data-testid="film-subtitle"/);
    assert.match(bar, /data-testid="film-subtitle-place"/);
    assert.match(bar, /filmSubtitleHighlight/);
    assert.match(bar, /replay\?\.active \|\| replay\?\.subtitle/);
    assert.equal((bar.match(/data-testid="film-subtitle"/g) || []).length, 1);
  });
});

describe("barre film (lot RG8) — pilules et durée estimée", () => {
  it("garde 2:30 / 3:00 et l'estimée hors film (RE3 : absentes pendant la lecture)", () => {
    assert.match(bar, /data-testid="film-duration"/);
    assert.match(bar, /filmDuration150/);
    assert.match(bar, /filmDuration180/);
    assert.match(bar, /data-testid="film-duration-estimate"/);
    assert.match(bar, /replay\.canStart \? \(/);
    assert.match(bar, /\{replay\.active \? \(/);
    assert.doesNotMatch(bar, /calibrateRate/);
  });
});
