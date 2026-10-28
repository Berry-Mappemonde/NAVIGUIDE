import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { transformWithOxc } from "vite";
import { FILM_WRITE_NOTICE_MS, filmWriteOutcome, filmWritingElapsedSeconds } from "../hooks/useReplay.js";
import en from "../i18n/en.js";
import fr from "../i18n/fr.js";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "../..");
const hook = readFileSync(join(here, "../hooks/useReplay.js"), "utf8");

function chooseFilmStyleSrc() {
  const at = hook.indexOf("const chooseFilmStyle = useCallback");
  assert.ok(at > 0, "chooseFilmStyle introuvable");
  return hook.slice(at, hook.indexOf("}, [hasWritten, lang, targetSeconds, t0, voyageId]);", at));
}

describe("clic Rédigé — issue honnête", () => {
  it("brut servi, 429 ou corps vide → « pas rédigé », rédigé seulement si hasWritten", () => {
    assert.equal(filmWriteOutcome(null), "not-written", "429 / !r.ok arrive en null");
    assert.equal(filmWriteOutcome(undefined), "not-written");
    assert.equal(filmWriteOutcome("oops"), "not-written");
    assert.equal(filmWriteOutcome({ hasWritten: false, source: "rules", chapters: [{ text: "a" }] }), "not-written");
    assert.equal(filmWriteOutcome({ status: "preparing" }), "not-written");
    assert.equal(filmWriteOutcome({ hasWritten: true, source: "nemotron-super" }), "written");
  });

  it("compte les secondes depuis le clic avec l'horloge du navigateur", () => {
    assert.equal(filmWritingElapsedSeconds(1_000, 1_000), 0);
    assert.equal(filmWritingElapsedSeconds(1_000, 13_999), 12);
    assert.equal(filmWritingElapsedSeconds(5_000, 4_000), 0, "jamais négatif");
    assert.equal(filmWritingElapsedSeconds(0, 9_000), 0, "pas de clic, pas de compteur");
    assert.equal(filmWritingElapsedSeconds(Number.NaN, 9_000), 0);
  });

  it("chooseFilmStyle ne se tait plus : plus de return muet ni de catch vide", () => {
    const fn = chooseFilmStyleSrc();
    assert.doesNotMatch(fn, /if \(!data\) return;/);
    assert.doesNotMatch(fn, /\.catch\(\(\) => \{\}\)/);
    assert.match(fn, /filmWriteOutcome\(data\) !== "written"/);
    assert.match(fn, /\.catch\(\(\) => setFilmWriteNotice\("not-written"\)\)/);
    assert.match(fn, /setFilmWritingSince\(Date\.now\(\)\)/);
    assert.match(fn, /setFilmWriteNotice\(""\);\s*setFilmWritingSince/);
    assert.match(fn, /\.finally\(\(\) => setFilmWriting\(false\)\)/);
    assert.match(hook, /setTimeout\(\(\) => setFilmWriteNotice\(""\), FILM_WRITE_NOTICE_MS\)/);
    assert.ok(FILM_WRITE_NOTICE_MS >= 4000 && FILM_WRITE_NOTICE_MS <= 15000, "ligne brève");
    assert.match(hook, /filmWritingSince,\s*filmWriteNotice,/);
  });

  it("textes fr / en : neutres, sans modèle ni raison, compteur {n} seulement", () => {
    for (const dict of [en, fr]) {
      assert.match(dict.filmWritingElapsed, /\{n\} s$/);
      assert.doesNotMatch(dict.filmWriteNotWritten, /\d/);
      for (const key of ["filmWritingElapsed", "filmWriteNotWritten"]) {
        assert.doesNotMatch(dict[key], /Nemotron|Token Factory|NIM|OpenRouter|Claude|Nebius/i);
        assert.doesNotMatch(dict[key], /budget|quota|limit|plafond|erreur|error|429/i);
      }
    }
    assert.equal(en.filmWriteNotWritten, "Not edited — Raw shown");
    assert.equal(fr.filmWriteNotWritten, "Pas rédigé — Brut affiché");
    assert.match(en.filmWriteNotWritten, new RegExp(en.filmStoryWritten.split(" ")[0], "i"), "same verb as the pill");
    assert.match(en.filmWriteNotWritten, new RegExp(en.filmStoryRaw));
    assert.match(fr.filmWriteNotWritten, new RegExp(fr.filmStoryRaw));
    assert.equal(en.filmWritingElapsed, "Writing… {n} s");
    assert.equal(fr.filmWritingElapsed, "Rédaction en cours… {n} s");
  });
});

describe("FilmWriteStatus — ligne hors du flux de la barre", () => {
  it("rend le compteur, puis l'issue, puis rien ; toujours en absolute au-dessus", async () => {
    const dir = mkdtempSync(join(root, ".film-write-render-"));
    try {
      mkdirSync(join(dir, "i18n"));
      mkdirSync(join(dir, "components"));
      writeFileSync(join(dir, "i18n/LangContext.js"), `
import { createContext, useContext } from "react";
export const LangContext = createContext(null);
export function useLang() { return useContext(LangContext); }
`);
      const jsx = readFileSync(join(here, "FilmWriteStatus.jsx"), "utf8");
      const { code } = await transformWithOxc(jsx, "FilmWriteStatus.jsx");
      writeFileSync(join(dir, "components/FilmWriteStatus.js"), code
        .replaceAll("../i18n/LangContext.jsx", "../i18n/LangContext.js")
        .replaceAll("../hooks/useReplay.js", pathToFileURL(join(here, "../hooks/useReplay.js")).href));
      const { LangContext } = await import(pathToFileURL(join(dir, "i18n/LangContext.js")).href);
      const { FilmWriteStatus } = await import(pathToFileURL(join(dir, "components/FilmWriteStatus.js")).href);
      const render = (props, lang = "en") => {
        const dict = lang === "en" ? en : fr;
        const t = (key, vars = {}) => Object.entries(vars).reduce(
          (s, [k, v]) => s.replace(`{${k}}`, String(v)),
          dict[key] ?? key,
        );
        return renderToStaticMarkup(createElement(
          LangContext.Provider,
          { value: { lang, t } },
          createElement(FilmWriteStatus, props),
        ));
      };

      const writing = render({ writing: true, since: Date.now() - 12_400, notice: "" });
      assert.match(writing, /data-state="writing"/);
      assert.match(writing, />Writing… 12 s</);
      const writingFr = render({ writing: true, since: Date.now() - 3_200 }, "fr");
      assert.match(writingFr, />Rédaction en cours… 3 s</);

      const failed = render({ writing: false, since: 0, notice: "not-written" });
      assert.match(failed, /data-state="not-written"/);
      assert.match(failed, />Not edited — Raw shown</);
      assert.match(render({ notice: "not-written" }, "fr"), />Pas rédigé — Brut affiché</);
      // Screen readers hear a stable message while writing, not every second.
      assert.match(writing, /<span aria-hidden="true"[^>]*>Writing… 12 s<\/span>/);
      assert.match(writing, /<span class="sr-only">Writing the edited film<\/span>/);
      assert.match(failed, /<span class="sr-only">Not edited — Raw shown<\/span>/);

      const idle = render({ writing: false, notice: "" });
      assert.match(idle, /data-state="idle"/);
      assert.doesNotMatch(idle, /<span/);

      for (const html of [writing, failed, idle]) {
        assert.match(html, /role="status"/);
        assert.match(html, /class="absolute bottom-full left-0 mb-\[26px\] max-\[599px\]:mb-\[48px\] max-w-\[60%\] pointer-events-none"/);
      }
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
