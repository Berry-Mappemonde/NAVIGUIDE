import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "EscaleSheet.jsx"), "utf8");
const hook = readFileSync(join(here, "..", "hooks", "useEscaleSheet.js"), "utf8");

describe("EscaleSheet contract (lot C)", () => {
  it("every place links to the map, its site and Google Maps; empty sections are not rendered", () => {
    assert.match(src, /googleMapsUrl\(item\.lat, item\.lon\)/);
    assert.match(src, /onFocus\(\{ name: item\.name, lat: item\.lat, lon: item\.lon, kind: SUB_KIND\[sub\]/);
    assert.match(src, /target="_blank" rel="noopener noreferrer"/);
    assert.match(src, /Object\.keys\(sections\)/, "sections come from the server: nothing invented client-side");
    assert.doesNotMatch(src, /fetch\(|Nemotron|Tavily|Nebius/i);
  });

  it("the paragraph is shown only when the cascade produced one; the listen button gets t and lang", () => {
    assert.match(src, /fiche\?\.paragraph\?\.status === "ready" \? fiche\.paragraph\.text : ""/);
    assert.match(src, /<ListenButton text=\{speech\} t=\{t\} lang=\{lang\} compact/);
  });

  it("the hook asks GET /escale once per (stop, lang) and keeps it in this tab", () => {
    assert.match(hook, /\/escale\?name=\$\{encodeURIComponent\(stop\.name\)\}&lat=\$\{stop\.lat\}&lon=\$\{stop\.lon\}&lang=/);
    assert.match(hook, /cacheRef\.current\.set\(key, fiche\)/);
    assert.match(hook, /controller\.abort\(\)/);
    assert.equal((hook.match(/useEffect\(/g) || []).length, 1, "one fetch on stop/lang, not per render");
  });

  it("shows the paragraph source under the text and does not fetch /escale itself", () => {
    assert.match(src, /data-testid="escale-source"/);
    assert.match(src, /storySourceLightning|storySourceSuper|storySourceRules/);
    assert.doesNotMatch(src, /useEffect/);
    assert.doesNotMatch(src, /\/escale/);
  });
});
