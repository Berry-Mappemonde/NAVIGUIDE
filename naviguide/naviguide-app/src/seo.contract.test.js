import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it } from "node:test";
import assert from "node:assert/strict";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const read = (rel) => readFileSync(join(root, rel), "utf8");

describe("contrat SEO naviguide.fr", () => {
  it("index.html : lang fr, canonical, OG, JSON-LD, H1 statique", () => {
    const html = read("index.html");
    assert.match(html, /<html lang="fr"/);
    assert.match(html, /rel="canonical" href="https:\/\/www\.naviguide\.fr\/"/);
    assert.match(
      html,
      /name="google-site-verification" content="wcHxYluJ5vTNo2dOGMj1T9A-dEfHXzaCTwMGM8OlAT0"/
    );
    assert.match(html, /property="og:title"/);
    assert.match(html, /name="twitter:card"/);
    assert.match(html, /"@type":\s*"WebApplication"/);
    assert.match(html, /berrymappemonde\.org\/#organization/);
    assert.match(html, /"sameAs":\s*\[/);
    assert.match(html, /https:\/\/github\.com\/Berry-Mappemonde/);
    assert.match(html, /"@type":\s*"VideoObject"/);
    assert.match(html, /KFl2-WEmVX4/);
    assert.match(html, /Demo: tracking a sailboat from La Rochelle to Mayotte/);
    assert.match(html, /"inLanguage":\s*"en"/);
    assert.match(html, /"description":\s*"3-minute demo: NAVIGUIDE follows/);
    assert.match(html, /"uploadDate":\s*"2026-10-16T00:00:00\+00:00"/);
    assert.match(html, /<h1>NAVIGUIDE/);
    assert.doesNotMatch(html, /<html lang="en"/);
  });

  it("public/robots.txt et sitemap.xml présents", () => {
    assert.ok(existsSync(join(root, "public/robots.txt")));
    assert.ok(existsSync(join(root, "public/sitemap.xml")));
    const robots = read("public/robots.txt");
    assert.match(robots, /Sitemap: https:\/\/www\.naviguide\.fr\/sitemap\.xml/);
    const sitemap = read("public/sitemap.xml");
    assert.match(sitemap, /<loc>https:\/\/www\.naviguide\.fr\/<\/loc>/);
  });
});
