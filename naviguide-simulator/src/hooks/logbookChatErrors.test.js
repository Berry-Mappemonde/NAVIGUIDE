import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { CHAT_TIMEOUT_MS, chatErrorCode, chatErrorKey } from "./logbookChatErrors.js";
import en from "../i18n/en.js";
import fr from "../i18n/fr.js";

const here = dirname(fileURLToPath(import.meta.url));
const hook = readFileSync(join(here, "useLogbookChat.js"), "utf8");
const chat = readFileSync(join(here, "..", "components", "LogbookChat.jsx"), "utf8");

describe("erreurs du chat du journal (#104)", () => {
  it("chaque échec a son code", () => {
    assert.equal(chatErrorCode({ aborted: true }), "timeout");
    assert.equal(chatErrorCode({ network: true }), "network");
    assert.equal(chatErrorCode({ status: 400 }), "empty");
    assert.equal(chatErrorCode({ status: 413 }), "tooLong");
    assert.equal(chatErrorCode({ status: 422 }), "tooLong");
    assert.equal(chatErrorCode({ status: 429 }), "busy");
    assert.equal(chatErrorCode({ status: 504 }), "timeout");
    assert.equal(chatErrorCode({ status: 500 }), "server");
    assert.equal(chatErrorCode({ status: 502 }), "server");
  });

  it("chaque code a sa phrase en anglais et en français ; un texte brut retombe sur l'erreur serveur", () => {
    for (const code of ["timeout", "network", "busy", "server", "tooLong", "empty"]) {
      const key = chatErrorKey(code);
      assert.ok(en[key] && fr[key], `${key} manquant`);
      assert.notEqual(en[key], fr[key]);
    }
    assert.equal(chatErrorKey("Failed to fetch"), "chatErrServer");
    assert.equal(chatErrorKey("question vide"), "chatErrServer");
  });

  it("coupure client un peu au-dessus du budget serveur d'Ultra (45 s)", () => {
    assert.equal(CHAT_TIMEOUT_MS, 45_000);
    assert.match(hook, /new AbortController\(\)/);
    assert.match(hook, /setTimeout\(\(\) => ctrl\.abort\(\), timeoutMs\)/);
    assert.match(hook, /signal: ctrl\.signal/);
    assert.match(hook, /clearTimeout\(timer\)/);
  });

  it("le détail brut reste en console ; la question échouée est marquée et peut être reposée", () => {
    assert.match(hook, /console\.warn\("\[logbook chat\]"/);
    assert.match(hook, /failed: true/);
    assert.match(hook, /const retry = useCallback/);
    assert.match(hook, /return useMemo\(/);
    assert.match(chat, /t\(chatErrorKey\(error\)\)/);
    assert.doesNotMatch(chat, /\{error\}/);
    assert.match(chat, /data-testid="logbook-chat-retry"/);
  });
});
