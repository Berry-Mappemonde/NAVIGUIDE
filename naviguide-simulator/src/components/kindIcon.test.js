import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { Dot } from "lucide-react";
import { KIND_ICON } from "../engine/journalFormat.js";
import { KIND_LUCIDE, KindIcon, kindIconComponent } from "./kindIcon.js";

const here = dirname(fileURLToPath(import.meta.url));
const bubbleSrc = readFileSync(join(here, "EventBubble.jsx"), "utf8");
const journalSrc = readFileSync(join(here, "JournalPanel.jsx"), "utf8");
const EMOJI = /\p{Extended_Pictographic}/u;

describe("kindIcon — pictogrammes lucide à la place des émojis", () => {
  it("chaque type du journal a son pictogramme ; un type inconnu retombe sur un point", () => {
    for (const kind of Object.keys(KIND_ICON)) {
      assert.ok(KIND_LUCIDE[kind], `pictogramme manquant pour ${kind}`);
      assert.notEqual(kindIconComponent(kind), Dot, kind);
    }
    assert.equal(kindIconComponent("weird"), Dot);
    assert.equal(kindIconComponent(undefined), Dot);
  });

  it("SVG caché aux lecteurs d'écran, à la taille et à la couleur du texte, sans émoji", () => {
    for (const kind of [...Object.keys(KIND_ICON), "weird"]) {
      const html = renderToStaticMarkup(createElement(KindIcon, { kind }));
      assert.match(html, /^<svg /, kind);
      assert.match(html, /aria-hidden="true"/, kind);
      assert.match(html, /width="1em"/, kind);
      assert.match(html, /height="1em"/, kind);
      assert.match(html, /stroke="currentColor"/, kind);
      assert.doesNotMatch(html, EMOJI, kind);
    }
  });

  it("la bulle du film et le journal dessinent KindIcon, plus l'émoji", () => {
    assert.match(bubbleSrc, /<KindIcon kind=\{card\.kind\}/);
    assert.doesNotMatch(bubbleSrc, /\{bubbleKindIcon\(card\)\}/);
    assert.match(journalSrc, /<KindIcon kind=\{e\.kind\}/);
    assert.doesNotMatch(journalSrc, /\{e\.icon\}/);
    assert.doesNotMatch(journalSrc, EMOJI);
  });
});

describe("kindIcon — inherited keys", () => {
  it("treats Object method names as unknown kinds", async () => {
    const { kindIconComponent } = await import("./kindIcon.js");
    const fallback = kindIconComponent("no-such-kind");
    for (const kind of ["constructor", "__proto__", "valueOf", "toString"]) {
      assert.equal(kindIconComponent(kind), fallback, kind);
    }
  });
});
