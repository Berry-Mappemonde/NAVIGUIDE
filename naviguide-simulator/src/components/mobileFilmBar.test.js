import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "..", "index.css"), "utf8");
const app = readFileSync(join(here, "..", "App.jsx"), "utf8");

function phoneBlock() {
  const start = css.indexOf("@media (max-width: 599px)");
  assert.ok(start >= 0, "bloc téléphone introuvable");
  const end = css.indexOf("\n}\n", start);
  return css.slice(start, end);
}

describe("barre du film sur téléphone (#105)", () => {
  it("aucune commande sous 11 px", () => {
    const phone = phoneBlock();
    for (const m of phone.matchAll(/font-size:\s*(\d+(?:\.\d+)?)px/g)) {
      assert.ok(Number(m[1]) >= 11, `font-size ${m[1]}px dans le bloc téléphone`);
    }
    assert.match(phone, /\[data-testid="film-duration-estimate"\]/);
  });

  it("cibles de 24 px au moins, hors piste du film", () => {
    const phone = phoneBlock();
    assert.match(phone, /\.naviguide-film-bar button:not\(\.h-2 \*\) \{\s*min-height: 24px;\s*min-width: 24px;/);
  });

  it("racine en dvh, 100vh en repli — plus de hauteur 100vh en ligne", () => {
    assert.match(css, /\.naviguide-root \{ height: 100vh; height: 100dvh; \}/);
    assert.match(app, /className=\{`naviguide-root/);
    assert.doesNotMatch(app, /height: "100vh"/);
  });
});
