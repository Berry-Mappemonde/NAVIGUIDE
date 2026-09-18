#!/usr/bin/env bash
# afterAgentResponse / stop : 1re réponse de session, demande, ou edit.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$REPO/.cursor/hooks/simulator-preview-lib.sh"

payload="$(preview_read_stdin || true)"
preview_log "open-browser"
if preview_is_background "$payload"; then
  preview_log "open-browser skip background"
  exit 0
fi
preview_open_browser
exit 0
