import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const sidebar = readFileSync(join(here, "Sidebar.jsx"), "utf8");
const chat = readFileSync(join(here, "LogbookChat.jsx"), "utf8");
const cards = readFileSync(join(here, "MomentCards.jsx"), "utf8");
const css = readFileSync(join(here, "..", "index.css"), "utf8");

function firstIndex(src, pattern) {
  const m = src.match(pattern);
  assert.ok(m, `motif introuvable : ${pattern}`);
  return m.index;
}

describe("Sidebar layout (lot N)", () => {
  it("place le chat avant la carte NOW, le sac ici et le récit", () => {
    const chatAt = firstIndex(sidebar, /<LogbookChat messages=\{chat\.messages\}/);
    const nowAt = firstIndex(sidebar, /<MomentNowCard /);
    const freeAt = firstIndex(sidebar, /<FreeMomentBlock /);
    const iciAt = firstIndex(sidebar, /data-testid="briefing"/);
    const storyAt = firstIndex(sidebar, /data-testid="expedition-story"/);
    const journalAt = firstIndex(sidebar, /<JournalPanel /);
    assert.ok(chatAt < nowAt, "LogbookChat avant MomentNowCard");
    assert.ok(nowAt < freeAt, "NOW avant FREE");
    assert.ok(freeAt < iciAt, "FREE avant sac ici");
    assert.ok(iciAt < storyAt, "sac ici avant récit");
    assert.ok(storyAt < journalAt, "récit avant journal");
    assert.doesNotMatch(sidebar, /EscaleSheet/);
  });

  it("garde les surfaces : étape, FREE, journal — plus de fiche d'escale dans le panneau", () => {
    assert.match(sidebar, /<SimulationPanel/);
    assert.match(sidebar, /<FreeMomentBlock /);
    assert.doesNotMatch(sidebar, /EscaleSheet/);
    assert.doesNotMatch(sidebar, /escaleStop|onEscaleClose/);
    assert.match(sidebar, /<JournalPanel /);
    assert.match(sidebar, /data-testid="here-product"/);
  });

  it("fixe les hauteurs via --sim-box-h-* et les classes sim-box-*", () => {
    assert.match(css, /--sim-box-h-chat:\s*168px/);
    assert.match(css, /--sim-box-h-now:/);
    assert.match(css, /--sim-box-h-ici:/);
    assert.match(css, /--sim-box-h-story:/);
    assert.match(css, /\.light-mode \.sim-box-chat/);
    assert.match(css, /\.light-mode \.sim-box-ici/);
    assert.match(css, /\.light-mode \.sim-box-story/);
    assert.match(chat, /sim-box-chat/);
    assert.match(cards, /sim-box-now/);
    assert.match(sidebar, /sim-box-ici/);
    assert.match(sidebar, /sim-box-story/);
  });

  it("réserve le sac ici à hauteur fixe avec le placeholder de remplissage", () => {
    assert.match(sidebar, /iciBriefingLoading/);
    assert.match(sidebar, /Le sac se remplit|iciBriefingLoading/);
    assert.match(sidebar, /\{!isDrawing \? \(/);
  });
});
