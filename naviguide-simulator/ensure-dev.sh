#!/usr/bin/env bash
# Démarre l’API (8010) et Vite (5174) en arrière-plan si besoin. Idempotent.
#   bash ensure-dev.sh              # démarrer les deux
#   bash ensure-dev.sh --open       # + ouvrir le navigateur
#   bash ensure-dev.sh --foreground # Vite au premier plan (terminal dédié)
#   bash ensure-dev.sh --quiet      # pas de messages (hooks Cursor)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

OPEN=0
FOREGROUND=0
QUIET=0
for arg in "$@"; do
  case "$arg" in
    --open) OPEN=1 ;;
    --foreground) FOREGROUND=1 ;;
    --quiet) QUIET=1 ;;
  esac
done

log() { [[ "$QUIET" -eq 1 ]] || echo "$*"; }

port_up() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

mkdir -p .dev

if ! command -v python3 >/dev/null || ! command -v npm >/dev/null; then
  [[ "$QUIET" -eq 1 ]] || echo "ensure-dev: python3 ou npm manquant" >&2
  exit 0
fi

if [[ ! -d .venv ]]; then
  log "==> venv Python (première fois)…"
  python3 -m venv .venv
  .venv/bin/pip install -q -r server/requirements.txt
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if [[ ! -d node_modules ]]; then
  log "==> npm install (première fois)…"
  npm install
fi

if ! port_up 8010; then
  log "==> API simulateur :8010"
  nohup uvicorn server.main:app --host 127.0.0.1 --port 8010 --reload \
    >> .dev/api.log 2>&1 &
  echo $! > .dev/api.pid
  for _ in $(seq 1 40); do
    port_up 8010 && break
    sleep 0.25
  done
fi

if [[ "$FOREGROUND" -eq 1 ]]; then
  log "==> Interface http://localhost:5174 (Ctrl+C arrête Vite ; API reste en arrière-plan)"
  if [[ "$OPEN" -eq 1 ]]; then
    (sleep 1.5 && open "http://localhost:5174") &
  fi
  export BROWSER=none
  exec npm run dev
fi

if ! port_up 5174; then
  log "==> Vite :5174"
  nohup env BROWSER=none npm run dev >> .dev/vite.log 2>&1 &
  echo $! > .dev/vite.pid
  for _ in $(seq 1 60); do
    port_up 5174 && break
    sleep 0.25
  done
fi

if [[ "$OPEN" -eq 1 ]] && port_up 5174; then
  opened=0
  for app in \
    "/Applications/Google Chrome.app" \
    "/Applications/Safari.app" \
    "/System/Applications/Safari.app" \
    "/Applications/Firefox.app"
  do
    if [[ -d "$app" ]] && /usr/bin/open -a "$app" "http://localhost:5174"; then
      opened=1
      break
    fi
  done
  if [[ "$opened" -eq 0 ]]; then
    /usr/bin/open "http://localhost:5174" || open "http://localhost:5174" || true
  fi
fi
