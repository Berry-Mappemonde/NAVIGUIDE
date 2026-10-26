import { memo, useCallback, useEffect, useRef, useState } from "react";
import { MessageSquare, Send } from "lucide-react";
import { useLang } from "../i18n/LangContext.jsx";
import { hasAdminSecret } from "../utils/adminSecret.js";
import { formatTimeUtc } from "../engine/journalFormat.js";
import { LlmSourceBadge } from "./LlmSourceBadge.jsx";

/**
 * Le chatbot du journal de bord, dans le panneau gauche : une
 * question sur toutes les données de l'application, une réponse citant les
 * faits du serveur, l'échange consigné au journal quand la clé admin est là.
 */
const AI_CHAT_NOTICE_KEY = "naviguide-ai-act-chat-notice-v1";

function aiNoticeDismissed() {
  try {
    return localStorage.getItem(AI_CHAT_NOTICE_KEY) === "1";
  } catch {
    return false;
  }
}

export const LogbookChat = memo(function LogbookChat({ messages = [], pending = false, error = null, onAsk }) {
  const { t } = useLang();
  const [draft, setDraft] = useState("");
  const [aiNoticeOff, setAiNoticeOff] = useState(aiNoticeDismissed);
  const [aiNoticeArmed, setAiNoticeArmed] = useState(false);
  const showAiNotice = !aiNoticeOff && (aiNoticeArmed || messages.length > 0);
  const listRef = useRef(null);
  const admin = hasAdminSecret();

  const dismissAiNotice = useCallback(() => {
    setAiNoticeOff(true);
    try {
      localStorage.setItem(AI_CHAT_NOTICE_KEY, "1");
    } catch {
      /* private mode: the notice stays closed for this view */
    }
  }, []);

  const onChatFocus = useCallback(() => {
    if (!aiNoticeDismissed()) setAiNoticeArmed(true);
  }, []);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages.length, pending]);

  const submit = (e) => {
    e?.preventDefault?.();
    const q = draft.trim();
    if (!q || pending) return;
    setDraft("");
    onAsk?.(q);
  };

  return (
    <div data-testid="logbook-chat" className="sim-box-chat rounded-lg border border-line-hairline bg-surface-raised/40 p-2 min-w-0">
      <div className="flex items-center gap-1.5 mb-1 flex-shrink-0">
        <MessageSquare size={12} className="text-text-muted" />
        <div className="text-[12px] font-semibold text-text-primary leading-snug">{t("logbookChatTitle")}</div>
        <span className="ml-auto text-[12px] text-text-muted">{admin ? t("logbookChatLogged") : t("logbookChatNotLogged")}</span>
      </div>
      <div
        data-testid="logbook-chat-reply"
        className="flex-1 min-h-0 rounded-md border border-line-hairline bg-surface-panel/55 px-1.5 py-1"
      >
        <div ref={listRef} className="h-full overflow-y-auto sidebar-scroll space-y-1 min-w-0" data-testid="logbook-chat-list">
          {messages.map((m, i) => (
            <div key={`${m.t}-${i}`} className={`text-[12px] leading-snug break-words [overflow-wrap:anywhere] ${m.role === "skipper" ? "text-text-primary" : "text-text-primary/90"}`}>
              <span className="text-[12px] text-text-muted mr-1">{formatTimeUtc(m.t)}</span>
              <span className="font-semibold mr-1">{m.role === "skipper" ? t("logbookChatYou") : t("logbookChatBot")}</span>
              {m.status === "failed"
                ? <span className="text-status-caution">{t("logbookChatFailed")}</span>
                : m.text}
              {m.role === "logbook" && m.status === "ready" ? (
                <span className="ml-1 text-[12px] text-text-muted">{m.logged ? "💬 " + t("logbookChatSaved") : t("logbookChatUnsaved")}</span>
              ) : null}
              {m.role === "logbook" && (m.source || m.engine) ? (
                <LlmSourceBadge source={m.source || m.engine} testId="chat-source" className="mt-0.5" />
              ) : null}
            </div>
          ))}
          {pending ? <p className="text-[12px] text-text-muted leading-snug">{t("logbookChatPending")}</p> : null}
          {error ? <p className="text-[12px] text-status-caution leading-snug">{error}</p> : null}
        </div>
      </div>
      {showAiNotice ? (
        <div
          data-testid="logbook-chat-ai-notice"
          className="mt-1.5 rounded-md border border-accent-line/45 bg-accent-soft px-2 py-1.5 text-xs leading-snug text-text-primary"
          role="note"
        >
          <p>{t("aiActChatNotice")}</p>
          <button
            type="button"
            data-testid="logbook-chat-ai-notice-dismiss"
            onClick={dismissAiNotice}
            className="mt-1 text-xs font-semibold text-text-primary underline underline-offset-2 hover:text-accent-text"
          >
            {t("aiActChatNoticeDismiss")}
          </button>
        </div>
      ) : null}
      <form onSubmit={submit} className="mt-1.5 flex items-center gap-1 flex-shrink-0">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onFocus={onChatFocus}
          placeholder={t("logbookChatPlaceholder")}
          maxLength={500}
          data-testid="logbook-chat-input"
          className="flex-1 min-w-0 h-7 rounded-md bg-surface-panel/70 border border-line-hairline px-2 text-[12px] text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-line/60"
        />
        <button
          type="submit"
          disabled={pending || !draft.trim()}
          title={t("logbookChatSend")}
          data-testid="logbook-chat-send"
          className="h-7 w-7 rounded-md bg-accent-fill hover:bg-accent-fill/85 disabled:opacity-40 flex items-center justify-center text-accent-on"
        >
          <Send size={12} />
        </button>
      </form>
    </div>
  );
});
