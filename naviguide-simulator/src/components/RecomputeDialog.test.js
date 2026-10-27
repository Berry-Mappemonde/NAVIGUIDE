import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { transformWithOxc } from "vite";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "../..");
const dialogSrc = readFileSync(join(here, "RecomputeDialog.jsx"), "utf8");

async function jsxModule(rel, name) {
  const jsx = readFileSync(join(root, "src", rel), "utf8");
  const { code } = await transformWithOxc(jsx, name);
  return code
    .replaceAll("../i18n/LangContext.jsx", "../i18n/LangContext.js")
    .replaceAll("./LlmSourceBadge.jsx", "./LlmSourceBadge.js");
}

describe("RecomputeDialog — la phrase du recalcul porte sa source", () => {
  it("garde la ligne épinglée et pose le badge juste après", () => {
    const adviceAt = dialogSrc.indexOf("<RouteAdviceText draft={draft} />");
    const badgeAt = dialogSrc.indexOf('testId="route-advice-source"');
    assert.ok(adviceAt > 0, "ligne <RouteAdviceText draft={draft} /> conservée");
    assert.ok(badgeAt > adviceAt, "badge sous la phrase");
    assert.match(dialogSrc, /source=\{draft\.advice\?\.source\}/);
    assert.match(dialogSrc, /<LlmSourceBadge/);
  });

  it("rend « contenu généré par IA » pour Lightning, la source honnête sinon, rien sans phrase", async () => {
    const dir = mkdtempSync(join(root, ".recompute-render-"));
    try {
      for (const sub of ["i18n", "utils", "components", "hooks"]) mkdirSync(join(dir, sub));
      writeFileSync(join(dir, "utils/llmSourceLabel.js"), readFileSync(join(root, "src/utils/llmSourceLabel.js"), "utf8"));
      writeFileSync(join(dir, "i18n/LangContext.js"), `
import { createContext, useContext } from "react";
export const LangContext = createContext(null);
export function useLang() { return useContext(LangContext); }
`);
      // Node n'a pas import.meta.env : on garde le vrai RouteAdviceText, sans l'URL d'API.
      const hook = readFileSync(join(root, "src/hooks/useVirtualVessel.js"), "utf8")
        .replace("import.meta.env.VITE_API_URL", "undefined");
      writeFileSync(join(dir, "hooks/useVirtualVessel.js"), hook);
      writeFileSync(join(dir, "components/LlmSourceBadge.js"), await jsxModule("components/LlmSourceBadge.jsx", "LlmSourceBadge.jsx"));
      writeFileSync(join(dir, "components/RecomputeDialog.js"), await jsxModule("components/RecomputeDialog.jsx", "RecomputeDialog.jsx"));
      const { LangContext } = await import(pathToFileURL(join(dir, "i18n/LangContext.js")).href);
      const { RecomputeDialog } = await import(pathToFileURL(join(dir, "components/RecomputeDialog.js")).href);
      const dicts = {
        en: (await import(pathToFileURL(join(root, "src/i18n/en.js")).href)).default,
        fr: (await import(pathToFileURL(join(root, "src/i18n/fr.js")).href)).default,
      };
      const render = (advice, lang = "en") => {
        const t = (key, vars = {}) => Object.entries(vars).reduce(
          (s, [k, v]) => s.replace(`{${k}}`, String(v)),
          dicts[lang][key] ?? key,
        );
        return renderToStaticMarkup(createElement(
          LangContext.Provider,
          { value: { lang, t } },
          createElement(RecomputeDialog, {
            draft: { status: "ok", to_name: "Halifax", distance_nm: 812, hours: 120, advice },
            busy: false,
            onAccept: () => {},
            onReject: () => {},
          }),
        ));
      };

      const ai = render({ text: "Le détour évite 2 alertes.", source: "nemotron-lightning", delta: {} });
      assert.match(ai, /data-testid="route-advice-text"[^>]*>Le détour évite 2 alertes\.<\/p>/);
      assert.match(ai, /data-testid="route-advice-source" data-ai-generated="true" data-llm-source="nemotron-lightning"/);
      assert.match(ai, /AI-generated content \(model: Nemotron 3\.5 Lightning · Token Factory\)/);
      assert.ok(ai.indexOf("route-advice-text") < ai.indexOf("route-advice-source"), "badge après la phrase");

      const fr = render({ text: "Le détour évite 2 alertes.", source: "nemotron-lightning" }, "fr");
      assert.match(fr, /Contenu généré par IA \(modèle : Nemotron 3\.5 Lightning · Token Factory\)/);

      const fallback = render({ text: "Route kept.", source: "openrouter" });
      assert.match(fallback, /AI-generated content \(model: OpenRouter\)/);
      assert.doesNotMatch(fallback, /Token Factory/);

      // Phrase des règles : pas d'étiquette IA, la source « rules » reste dite.
      const rules = render({ text: "Route kept.", source: "rules" });
      assert.match(rules, /data-testid="route-advice-source" data-ai-generated="false" data-llm-source="rules"/);
      assert.doesNotMatch(rules, /AI-generated/);

      for (const advice of [undefined, { text: "   ", source: "nemotron-lightning" }]) {
        const none = render(advice);
        assert.doesNotMatch(none, /route-advice-text|route-advice-source/);
      }
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
