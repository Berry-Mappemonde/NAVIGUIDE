#!/usr/bin/env bash
# Hook sessionStart : flag d’abord (même si le démarrage serveur est lent).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$REPO/.cursor/hooks/simulator-preview-lib.sh"

payload="$(preview_read_stdin || true)"
preview_log "sessionStart"
if preview_is_background "$payload"; then
  preview_log "sessionStart skip background"
  exit 0
fi
preview_reset_session_flags
if [[ -x "$REPO/naviguide-simulator/ensure-dev.sh" ]]; then
  bash "$REPO/naviguide-simulator/ensure-dev.sh" --quiet
fi
exit 0
