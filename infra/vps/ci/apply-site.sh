#!/usr/bin/env bash
# Applique un site déjà rsyncé. À lancer SUR le VPS.
# Usage : apply-site.sh blue-intelligence|naviguide|simulator
#
# FORCE_DEPLOY=1  — redémarre même si un run est en cours
# SKIP_FRONTEND_BUILD=1 (défaut) — exige un dist/build déjà là
# SHA=…           — commit GitHub, écrit dans l'état « déployé »
set -euo pipefail

SITE="${1:?usage: apply-site.sh blue-intelligence|naviguide|simulator}"
APP="${APP:-$HOME/blue-intelligence-map}"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/blue-intelligence-deploy"
FORCE="${FORCE_DEPLOY:-0}"
SKIP_FRONTEND_BUILD="${SKIP_FRONTEND_BUILD:-1}"
SHA="${SHA:-unknown}"
PROBE="$APP/infra/vps/ci/prod_jobs_busy.py"

mkdir -p "$STATE/pending" "$STATE/deployed"

hash_for() {
  case "$1" in
    blue-intelligence)
      sha256sum "$APP/backend/requirements.txt" | awk '{print $1}'
      ;;
    naviguide)
      cat "$APP/naviguide/naviguide-api/requirements.txt" \
          "$APP/naviguide/naviguide_workspace/requirements.txt" \
        | sha256sum | awk '{print $1}'
      ;;
    simulator)
      sha256sum "$APP/naviguide-simulator/server/requirements.txt" | awk '{print $1}'
      ;;
  esac
}

venv_ok() {
  case "$1" in
    blue-intelligence) [ -x "$APP/backend/.venv/bin/python" ] ;;
    naviguide)         [ -x "$APP/naviguide/.venv/bin/python" ] ;;
    simulator)         [ -x "$APP/naviguide-simulator/.venv/bin/python" ] ;;
  esac
}

need_pip=0
new_hash="$(hash_for "$SITE")"
old_hash=""
[ -f "$STATE/pip-$SITE.sha256" ] && old_hash="$(cat "$STATE/pip-$SITE.sha256")"
if ! venv_ok "$SITE"; then
  need_pip=1
elif [ -n "$old_hash" ] && [ "$old_hash" != "$new_hash" ]; then
  need_pip=1
fi
# Premier passage CI : le venv prod existe, pas encore d'empreinte → pas de pip.

queue_pending() {
  cat > "$STATE/pending/$SITE" <<EOF
SHA=$SHA
NEED_PIP=$need_pip
QUEUED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
  echo "Reporté : $SITE (SHA=$SHA) — un run d'enrichissement occupe encore uvicorn, ou la sonde a échoué."
  echo "Le rattrapage GitHub (toutes les 20 min) réessaiera. Forcer : FORCE_DEPLOY=1"
}

probe_code=0
if [ ! -f "$PROBE" ]; then
  echo "Sonde introuvable ($PROBE) — abort." >&2
  exit 1
fi
if python3 "$PROBE" --base-url http://127.0.0.1:8001; then
  probe_code=0
else
  probe_code=$?
fi

must_wait=0
if [ "$FORCE" != "1" ]; then
  if [ "$SITE" = "blue-intelligence" ]; then
    # Tout restart de blue-intelligence tue les runs en mémoire.
    if [ "$probe_code" -eq 10 ] || [ "$probe_code" -eq 1 ]; then
      must_wait=1
    fi
  else
    # NAVIGUIDE / simulateur : OK pendant un Complet si on ne lance pas pip/npm.
    if [ "$need_pip" -eq 1 ] && [ "$probe_code" -eq 10 ]; then
      must_wait=1
    fi
    if [ "$need_pip" -eq 1 ] && [ "$probe_code" -eq 1 ]; then
      must_wait=1
    fi
  fi
fi

if [ "$must_wait" -eq 1 ]; then
  queue_pending
  exit 0
fi

export SKIP_FRONTEND_BUILD
if [ "$need_pip" -eq 0 ]; then
  export SKIP_PIP=1
else
  export SKIP_PIP=0
fi

echo "→ apply $SITE SKIP_FRONTEND_BUILD=$SKIP_FRONTEND_BUILD SKIP_PIP=$SKIP_PIP FORCE=$FORCE SHA=$SHA"

case "$SITE" in
  blue-intelligence)
    bash "$APP/infra/vps/deploy-app.sh"
    ;;
  naviguide)
    bash "$APP/infra/vps/naviguide/deploy-naviguide.sh"
    ;;
  simulator)
    bash "$APP/infra/vps/naviguide/deploy-simulator.sh"
    ;;
  *)
    echo "site inconnu: $SITE" >&2
    exit 1
    ;;
esac

printf '%s\n' "$new_hash" > "$STATE/pip-$SITE.sha256"
printf '%s\n' "$SHA" > "$STATE/deployed/$SITE"
rm -f "$STATE/pending/$SITE"
echo "Déployé : $SITE SHA=$SHA"
