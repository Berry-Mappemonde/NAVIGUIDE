import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (file) => readFileSync(join(here, file), "utf8");

describe("PanelBoundary (#101)", () => {
  it("rattrape une erreur de rendu et propose de remonter le panneau", () => {
    const src = read("PanelBoundary.jsx");
    assert.match(src, /static getDerivedStateFromError\(error\)/);
    assert.match(src, /componentDidCatch\(error, info\)/);
    assert.match(src, /data-testid="panel-boundary"/);
    assert.match(src, /onClick=\{this\.reset\}/);
    assert.match(src, /data-testid="root-boundary"/);
    assert.match(src, /window\.location\.reload\(\)/);
  });

  it("entoure le volet gauche, les outils et la barre du film — pas la carte", () => {
    const app = read("../App.jsx");
    for (const [name, tag] of [["sidebar", "Sidebar"], ["tools", "ToolsSidebar"], ["film-bar", "SimulationFilmBar"]]) {
      const re = new RegExp(`<PanelBoundary name="${name}"[^>]*>\\s*<${tag}\\b[\\s\\S]*?\\/>\\s*<\\/PanelBoundary>`);
      assert.match(app, re, `${tag} doit être dans <PanelBoundary name="${name}">`);
    }
    assert.doesNotMatch(app, /<PanelBoundary[^>]*>\s*<MapScene/);
  });

  it("racine : journal des erreurs et dernier filet autour de l'app", () => {
    const main = read("../main.jsx");
    assert.match(main, /onUncaughtError:/);
    assert.match(main, /onCaughtError:/);
    assert.match(main, /<RootBoundary>\s*<LangProvider>\s*<App \/>/);
  });
});
