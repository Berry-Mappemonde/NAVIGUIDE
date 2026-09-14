#!/usr/bin/env bash
# Run on the Mac, from anywhere:
#   bash infra/vps/naviguide/publish-simulator-from-mac.sh
#
# 1) builds the site (npm) on the Mac — avoids npm on the VPS (8 GB)
# 2) copies only the simulator + these infra files (not Blue Intelligence)
# 3) runs deploy-simulator.sh on the VPS (venv, separate nginx, certificate)
#
# Prerequisites: you already connect over SSH (same key as usual).
# Optional variables:
#   NAVIGUIDE_VPS=ubuntu@135.125.226.16
#   NAVIGUIDE_SSH_IDENTITY=/chemin/vers/cle_privee
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
VPS="${NAVIGUIDE_VPS:-ubuntu@135.125.226.16}"
REMOTE_APP="/home/ubuntu/blue-intelligence-map"
SIM="$ROOT/naviguide-simulator"
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=15)
if [ -n "${NAVIGUIDE_SSH_IDENTITY:-}" ]; then
  SSH_OPTS+=(-i "$NAVIGUIDE_SSH_IDENTITY" -o IdentitiesOnly=yes)
fi
RSH=(ssh "${SSH_OPTS[@]}")

cd "$ROOT"
if [ ! -f "$SIM/package.json" ]; then
  echo "naviguide-simulator/package.json introuvable (racine du dépôt ?)" >&2
  exit 1
fi

echo "→ Test SSH $VPS …"
"${RSH[@]}" "$VPS" 'echo OK; hostname'

echo "→ Build Vite sur le Mac (http://localhost n'est pas publié)…"
cd "$SIM"
if [ ! -d node_modules ]; then
  npm install --no-audit --no-fund
fi
npm run build
test -f dist/index.html

echo "→ Copie du simulateur (sans node_modules / .venv)…"
"${RSH[@]}" "$VPS" "mkdir -p $REMOTE_APP/naviguide-simulator $REMOTE_APP/infra/vps/naviguide"
rsync -az --delete -e "${RSH[*]}" \
  --exclude node_modules \
  --exclude .venv \
  --exclude .pytest_cache \
  --exclude __pycache__ \
  --exclude .env \
  --exclude server/polar_data/*.json \
  "$SIM/" "$VPS:$REMOTE_APP/naviguide-simulator/"

echo "→ Copie des fichiers infra simulateur…"
rsync -az -e "${RSH[*]}" \
  "$ROOT/infra/vps/naviguide/nginx-simulator.conf" \
  "$ROOT/infra/vps/naviguide/naviguide-simulator.service" \
  "$ROOT/infra/vps/naviguide/deploy-simulator.sh" \
  "$ROOT/infra/vps/naviguide/simulator.env.example" \
  "$ROOT/infra/vps/naviguide/publish-simulator-from-mac.sh" \
  "$VPS:$REMOTE_APP/infra/vps/naviguide/"

echo "→ Déploiement sur le VPS…"
"${RSH[@]}" "$VPS" "bash $REMOTE_APP/infra/vps/naviguide/deploy-simulator.sh"

echo
echo "Ouvre https://simulator.naviguide.fr  (www.naviguide.fr ne doit pas changer)"
echo "Journaux : ssh $VPS 'sudo journalctl -u naviguide-simulator -n 50 --no-pager'"
