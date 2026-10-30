import { useCallback, useMemo, useRef, useState } from "react";
import { adminHeaders } from "../utils/adminSecret.js";
import { CHAT_TIMEOUT_MS, chatErrorCode } from "./logbookChatErrors.js";

const API_URL = import.meta.env.VITE_API_URL ?? "";
const HISTORY_MAX = 30;

/**
 * Chatbot journal de bord. `ask(question)` posts to /logbook/chat with
 * the facts only the client knows (`contextFn()` → view, boat of the film,
 * polar, skipper's orders). The server answers from its own facts and logs
 * the exchange when the admin key travels with the request. Never blocks
 * Play; one question in flight at a time.
 *
 * #104 : coupure à CHAT_TIMEOUT_MS ; `error` est un code (logbookChatErrors.js), jamais le texte
 * brut ; la question restée sans réponse porte `failed: true` et `retry(message)` la repose.
 */
export function useLogbookChat({ lang = "fr", contextFn = null, timeoutMs = CHAT_TIMEOUT_MS } = {}) {
  const [messages, setMessages] = useState([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const inFlight = useRef(false);

  const ask = useCallback(async (question, opts = {}) => {
    const q = String(question || "").trim();
    if (!q || inFlight.current) return null;
    inFlight.current = true;
    setPending(true);
    setError(null);
    const t = new Date().toISOString();
    const asked = { role: "skipper", text: q, t };
    setMessages((prev) => [...prev, asked].slice(-HISTORY_MAX));
    let context = null;
    try {
      context = typeof contextFn === "function" ? contextFn() : null;
    } catch {
      context = null;
    }
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      let r;
      try {
        r = await fetch(`${API_URL}/logbook/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...adminHeaders() },
          body: JSON.stringify({ question: q, lang, context }),
          signal: ctrl.signal,
        });
      } catch (err) {
        const aborted = err?.name === "AbortError";
        throw Object.assign(new Error(err?.message || "fetch"), { code: chatErrorCode({ aborted, network: !aborted }) });
      }
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        throw Object.assign(new Error(body?.detail || `HTTP ${r.status}`), { code: chatErrorCode({ status: r.status }) });
      }
      const reply = {
        role: "logbook",
        text: body.answer || "",
        status: body.status,
        reason: body.reason || null,
        logged: Boolean(body.logged),
        engine: body.engine || null,
        source: body.source || body.engine || null,
        t: body.t || new Date().toISOString(),
      };
      setMessages((prev) => [...prev, reply].slice(-HISTORY_MAX));
      return reply;
    } catch (err) {
      const code = err?.code || "server";
      console.warn("[logbook chat]", code, err?.message);
      setError(code);
      setMessages((prev) => prev.map((m) => (m === asked ? { ...m, failed: true, error: code } : m)));
      return null;
    } finally {
      clearTimeout(timer);
      inFlight.current = false;
      setPending(false);
    }
  }, [lang, contextFn, timeoutMs]);

  // Repose une question restée sans réponse : elle quitte l'historique et repart comme neuve.
  const retry = useCallback((message) => {
    if (!message?.failed || inFlight.current) return null;
    setMessages((prev) => prev.filter((m) => m !== message));
    return ask(message.text);
  }, [ask]);

  const clear = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  // Objet stable entre deux rendus : memo(Sidebar) ne se relance plus pour rien.
  return useMemo(
    () => ({ messages, pending, error, ask, retry, clear }),
    [messages, pending, error, ask, retry, clear],
  );
}
