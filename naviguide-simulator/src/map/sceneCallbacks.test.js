import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { sceneCallbacks } from "./sceneCallbacks.js";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "..");

function sourceFiles(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return entry.name === "fixtures" ? [] : sourceFiles(path);
    return /\.(jsx?|tsx?)$/.test(entry.name) && !/\.test\./.test(entry.name) ? [path] : [];
  });
}

describe("rappels de la scène (sceneCallbacks)", () => {
  it("relaient le gestionnaire courant, pas celui du montage", () => {
    const ref = { current: { onBriefingFocus: () => assert.fail("ancien gestionnaire") } };
    const callbacks = sceneCallbacks(ref);
    const seen = [];
    ref.current = { onBriefingFocus: (entity) => seen.push(entity.name) };
    callbacks.onBriefingFocus({ name: "Funchal", lat: 32.65, lon: -16.91 });
    assert.deepEqual(seen, ["Funchal"]);
  });

  it("ne lèvent rien quand aucun gestionnaire n'est branché", () => {
    for (const ref of [{ current: {} }, { current: null }]) {
      for (const callback of Object.values(sceneCallbacks(ref))) {
        assert.doesNotThrow(() => callback());
      }
    }
  });

  it("fournissent chaque rappel que les popups appellent via window.__naviguideScene (#102)", () => {
    const provided = new Set(Object.keys(sceneCallbacks({ current: {} })));
    const used = [];
    for (const file of sourceFiles(src)) {
      for (const [, name] of readFileSync(file, "utf8").matchAll(/__naviguideScene\??\.callbacks\??\.(\w+)/g)) {
        used.push(name);
        assert.ok(provided.has(name), `${file.slice(src.length + 1)} appelle callbacks.${name}, absent de sceneCallbacks`);
      }
    }
    assert.ok(used.includes("onBriefingFocus"), "la bulle d'événement appelle onBriefingFocus");
  });

  it("App branche le recentrage du briefing sur la scène, pas seulement sur le panneau", () => {
    const app = readFileSync(join(src, "App.jsx"), "utf8");
    const at = app.indexOf("<MapScene");
    assert.ok(at >= 0, "<MapScene> présent");
    assert.match(app.slice(at, app.indexOf("/>", at)), /onBriefingFocus=\{handleBriefingFocus\}/);
    const scene = readFileSync(join(here, "MapScene.jsx"), "utf8");
    assert.match(scene, /MapSceneController\.mount\(containerRef\.current, sceneCallbacks\(callbacksRef\)\)/);
    assert.match(scene, /controller\.setCallbacks\(sceneCallbacks\(callbacksRef\)\)/);
    // MapScene relaie chaque rappel lu par sceneCallbacks : prop reçue, puis callbacksRef.current.
    const propsAt = scene.indexOf("export function MapScene({");
    const props = scene.slice(propsAt, scene.indexOf("})", propsAt));
    const refAt = scene.indexOf("callbacksRef.current = {");
    const relayed = scene.slice(refAt, scene.indexOf("};", refAt));
    for (const key of Object.keys(sceneCallbacks({ current: {} }))) {
      assert.match(props, new RegExp(`\\b${key},`), `MapScene reçoit ${key}`);
      assert.match(relayed, new RegExp(`\\b${key},`), `MapScene relaie ${key}`);
    }
  });
});
