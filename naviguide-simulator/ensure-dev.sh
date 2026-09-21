#!/usr/bin/env bash
# Démarre l’API (8010) et l’interface (5174) en arrière-plan si besoin. Idempotent.
#   bash ensure-dev.sh              # démarrer les deux (Vite en mode dev)
#   bash ensure-dev.sh --open       # + ouvrir le navigateur
#   bash ensure-dev.sh --foreground # Vite au premier plan (terminal dédié)
#   bash ensure-dev.sh --quiet      # pas de messages (hooks Cursor)
#   bash ensure-dev.sh --prod       # poste de recette : build de prod + `vite preview`,
#                                   # API et interface de CE checkout (remplace celles
#                                   # d’un autre checkout qui tiendraient les ports)
#
# Clés : le fichier ~/.config/naviguide/simulator.env (ou $NAVIGUIDE_ENV_FILE) est
# chargé dans l’environnement de l’API — même fichier, même contenu que celui du
# service naviguide-simulator sur le VPS. Jamais dans le dépôt.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

OPEN=0
FOREGROUND=0
QUIET=0
PROD=0
for arg in "$@"; do
  case "$arg" in
    --open) OPEN=1 ;;
    --foreground) FOREGROUND=1 ;;
    --quiet) QUIET=1 ;;
    --prod) PROD=1 ;;
  esac
done

log() { [[ "$QUIET" -eq 1 ]] || echo "$*"; }

port_up() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

# PID(s) qui écoutent sur un port (vide si personne).
listener_pids() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | sort -u || true
}

# Dossier de travail d’un processus (vide si inconnu).
proc_cwd() {
  lsof -a -p "$1" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1 || true
}

# Arrête ce qui écoute sur un port, seulement si c’est un de nos serveurs
# (uvicorn et son processus rechargeur, vite / node, python lancé depuis un
# checkout naviguide-simulator) : jamais un autre programme.
stop_listener() {
  local port="$1" what="$2" pid cmd cwd
  for pid in $(listener_pids "$port"); do
    cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    cwd="$(proc_cwd "$pid")"
    if [[ "$cmd" == *uvicorn* || "$cmd" == *vite* || "$cmd" == *node* || "$cmd" == *multiprocessing* || ( "$cmd" == *python* && "$cwd" == */naviguide-simulator ) ]]; then
      log "==> $what :$port déjà tenu par le PID $pid ($cwd) — arrêt"
      kill "$pid" 2>/dev/null || true
    else
      log "!! $what :$port est tenu par un autre programme ($cmd) — non arrêté"
    fi
  done
  for _ in $(seq 1 20); do
    port_up "$port" || return 0
    sleep 0.25
  done
  for pid in $(listener_pids "$port"); do kill -9 "$pid" 2>/dev/null || true; done
  sleep 0.5
}

# ── Clés : un seul fichier, hors dépôt ────────────────────────────────────────
ENV_FILE="${NAVIGUIDE_ENV_FILE:-$HOME/.config/naviguide/simulator.env}"
KEY_NAMES=""
if [[ -f "$ENV_FILE" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] || continue
    export "$line"
    case "$line" in *API_KEY=*|*PASSWORD=*|*SECRET=*) KEY_NAMES="$KEY_NAMES ${line%%=*}" ;; esac
  done < "$ENV_FILE"
  log "==> clés chargées depuis $ENV_FILE :${KEY_NAMES:- (aucune clé)}"
else
  log "!! $ENV_FILE absent : l’API tourne sans clé (récit « règles », chat et juge éteints)."
  log "   Créer le fichier : mkdir -p ~/.config/naviguide && nano ~/.config/naviguide/simulator.env"
fi

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

# ── API :8010 ─────────────────────────────────────────────────────────────────
start_api() {
  local reload="$1"
  log "==> API simulateur :8010 ($ROOT)"
  # shellcheck disable=SC2086
  nohup uvicorn server.main:app --host 127.0.0.1 --port 8010 $reload \
    >> .dev/api.log 2>&1 &
  echo $! > .dev/api.pid
  for _ in $(seq 1 80); do
    port_up 8010 && break
    sleep 0.25
  done
}

if [[ "$PROD" -eq 1 ]]; then
  # Recette : l’API doit être celle de CE checkout, avec les clés d’aujourd’hui.
  stop_listener 8010 "API"
  start_api ""
elif ! port_up 8010; then
  start_api "--reload"
else
  for pid in $(listener_pids 8010); do
    cwd="$(proc_cwd "$pid")"
    [[ -n "$cwd" && "$cwd" != "$ROOT" ]] && log "!! API :8010 déjà lancée depuis $cwd (pas $ROOT) — bash ensure-dev.sh --prod pour la remplacer"
  done
fi

# ── Interface :5174 ───────────────────────────────────────────────────────────
if [[ "$PROD" -eq 1 ]]; then
  log "==> build de prod (npm run build)…"
  if ! npm run build >> .dev/build.log 2>&1; then
    echo "ensure-dev: le build de prod a échoué — voir $ROOT/.dev/build.log" >&2
    exit 1
  fi
  stop_listener 5174 "Interface"
  log "==> Interface :5174 (vite preview, build de prod)"
  nohup npx vite preview --host 127.0.0.1 --port 5174 --strictPort >> .dev/vite.log 2>&1 &
  echo $! > .dev/vite.pid
  for _ in $(seq 1 60); do
    port_up 5174 && break
    sleep 0.25
  done
elif [[ "$FOREGROUND" -eq 1 ]]; then
  log "==> Interface http://localhost:5174 (Ctrl+C arrête Vite ; API reste en arrière-plan)"
  if [[ "$OPEN" -eq 1 ]]; then
    (sleep 1.5 && open "http://localhost:5174") &
  fi
  export BROWSER=none
  exec npm run dev
elif ! port_up 5174; then
  log "==> Vite :5174"
  nohup env BROWSER=none npm run dev >> .dev/vite.log 2>&1 &
  echo $! > .dev/vite.pid
  for _ in $(seq 1 60); do
    port_up 5174 && break
    sleep 0.25
  done
fi

# ── Santé ─────────────────────────────────────────────────────────────────────
health() {
  local url="$1" tries="$2"
  for _ in $(seq 1 "$tries"); do
    curl -fsS -m 5 -o /dev/null "$url" 2>/dev/null && return 0
    sleep 1
  done
  return 1
}
API_OK=0; UI_OK=0
health "http://127.0.0.1:8010/ici/warm/status" 60 && API_OK=1
health "http://127.0.0.1:5174/" 30 && UI_OK=1
BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
[[ "$BRANCH" == "HEAD" ]] && BRANCH="$(git -C "$ROOT" describe --all --always 2>/dev/null || echo '?')"
if [[ "$QUIET" -eq 0 ]]; then
  echo "── poste ───────────────────────────────────────────────"
  echo "checkout   : $ROOT ($BRANCH)"
  echo "API :8010  : $([[ $API_OK -eq 1 ]] && echo OK || echo "PAS DE RÉPONSE — voir .dev/api.log") — clés :${KEY_NAMES:- aucune}"
  echo "UI  :5174  : $([[ $UI_OK -eq 1 ]] && echo OK || echo "PAS DE RÉPONSE — voir .dev/vite.log") — $([[ $PROD -eq 1 ]] && echo 'build de prod (vite preview)' || echo 'mode dev (vite)')"
  echo "────────────────────────────────────────────────────────"
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

[[ "$API_OK" -eq 1 && "$UI_OK" -eq 1 ]] || [[ "$PROD" -eq 0 ]]
