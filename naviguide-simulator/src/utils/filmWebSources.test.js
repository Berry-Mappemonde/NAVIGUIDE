import assert from "node:assert/strict";
import test from "node:test";
import { publicFilmWebContext } from "./filmWebSources.js";
import { resolveServedFilm } from "../hooks/useReplay.js";
import fr from "../i18n/fr.js";
import en from "../i18n/en.js";

const CTX = {
  basis: "tavily",
  port: "Papeete",
  fetchedAt: "2026-10-29T07:40:00Z",
  sources: [
    { title: "Papeete — Noonsite", url: "https://www.noonsite.com/place/french-polynesia/papeete/", domain: "noonsite.com" },
    { title: "", url: "https://example.org/marina" },
    { title: "x", url: "javascript:alert(1)" },
  ],
};

test("publicFilmWebContext garde port, domaines et liens http(s)", () => {
  const out = publicFilmWebContext({ webContext: CTX });
  assert.equal(out.port, "Papeete");
  assert.deepEqual(out.sources.map((s) => s.domain), ["noonsite.com", "example.org"]);
  assert.equal(out.sources[1].title, "example.org");
});

test("publicFilmWebContext : rien sans provenance Tavily réelle", () => {
  assert.equal(publicFilmWebContext(null), null);
  assert.equal(publicFilmWebContext({}), null);
  assert.equal(publicFilmWebContext({ webContext: { ...CTX, basis: "llm" } }), null);
  assert.equal(publicFilmWebContext({ webContext: { ...CTX, sources: [] } }), null);
  assert.equal(publicFilmWebContext({ webContext: { ...CTX, port: "" } }), null);
});

test("resolveServedFilm transmet la provenance Tavily (rédigé et brut)", () => {
  const written = resolveServedFilm({ hasWritten: true, source: "nemotron-super", webContext: CTX }, "written");
  assert.equal(written.webContext?.port, "Papeete");
  const raw = resolveServedFilm({ webContext: CTX }, "raw");
  assert.equal(raw.webContext?.port, "Papeete");
  const none = resolveServedFilm({ hasWritten: true, source: "nemotron-super" }, "written");
  assert.equal(none.webContext, null);
});

test("libellé du film : Tavily nommé en FR et EN", () => {
  assert.match(fr.filmWebSourcesTitle, /Tavily/);
  assert.match(en.filmWebSourcesTitle, /Tavily/);
  assert.match(fr.filmWebSourcesTitle, /\{port\}/);
  assert.match(en.filmWebSourcesTitle, /\{port\}/);
});
