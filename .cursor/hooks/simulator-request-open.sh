#!/usr/bin/env bash
# Hook beforeSubmitPrompt : ouvrir si l’utilisateur demande l’appli locale.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$REPO/.cursor/hooks/simulator-preview-lib.sh"

payload="$(preview_read_stdin || true)"
preview_log "beforeSubmitPrompt"
if preview_prompt_asks_open "$payload"; then
  preview_log "beforeSubmitPrompt ask-match"
  preview_mark_ask
  preview_open_browser force
else
  preview_log "beforeSubmitPrompt no-match"
fi
printf '%s\n' '{"continue":true}'
exit 0
