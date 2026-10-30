/**
 * Erreurs de transport du chat du journal (#104). Le serveur borne ses appels LLM (25 s, 45 s pour
 * Ultra) mais nginx laisse 600 s à /logbook : le client coupe à 45 s, un peu au-dessus du pire cas
 * serveur. L'écran ne montre jamais le texte brut (« Failed to fetch », « HTTP 504 », « question
 * vide » en français dans l'interface anglaise) : un code, traduit par chatErrorKey ; le détail
 * part en console.
 */
export const CHAT_TIMEOUT_MS = 45_000;

/** Code d'erreur d'un échec : timeout | network | busy | server | tooLong | empty. */
export function chatErrorCode({ status = null, aborted = false, network = false } = {}) {
  if (aborted) return "timeout";
  if (network) return "network";
  const s = Number(status);
  if (s === 400) return "empty";
  if (s === 413 || s === 422) return "tooLong";
  if (s === 429) return "busy";
  if (s === 504 || s === 408) return "timeout";
  return "server";
}

const KEYS = {
  timeout: "chatErrTimeout",
  network: "chatErrNetwork",
  busy: "chatErrBusy",
  server: "chatErrServer",
  tooLong: "chatErrTooLong",
  empty: "chatErrEmpty",
};

/** Clé i18n d'un code ; un code inconnu (ou un ancien message brut) → erreur serveur générique. */
export function chatErrorKey(code) {
  return KEYS[code] || KEYS.server;
}
