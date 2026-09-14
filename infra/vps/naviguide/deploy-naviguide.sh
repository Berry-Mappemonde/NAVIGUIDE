#!/usr/bin/env bash
# (Re)deploy NAVIGUIDE on the OVH VPS (www.naviguide.fr).
# Assumes: monorepo in ~/blue-intelligence-map, Node + nginx +
# certbot already installed (Blue Intelligence deploy). Idempotent.
#
# First deploy — after this script:
#   1. fill in ~/.config/naviguide/naviguide.env (NVIDIA_API_KEY /
#      OPENROUTER_API_KEY / ANTHROPIC_API_KEY — cascade LLM —, COPERNICUS_*)
#   2. sudo systemctl restart naviguide-api naviguide-orchestrator naviguide-polar
#   3. TLS: the Let's Encrypt live/naviguide.fr certificate (SAN apex + www) already
#      exists and is referenced by nginx-naviguide.conf; on a blank VPS:
#      sudo certbot --nginx -d www.naviguide.fr -d naviguide.fr
set -euo pipefail

APP="$HOME/blue-intelligence-map"
NAV="$APP/naviguide"
CONF_DIR="$HOME/.config/naviguide"
UV="$HOME/.local/bin/uv"
SKIP_FRONTEND_BUILD="${SKIP_FRONTEND_BUILD:-0}"
SKIP_PIP="${SKIP_PIP:-0}"

command -v "$UV" >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh

# ── Shared Python venv of the 3 NAVIGUIDE services ──────────────────────────────
cd "$NAV"
[ -d .venv ] || "$UV" venv --python 3.12 .venv
if [ "$SKIP_PIP" = "1" ] && [ -x .venv/bin/python ]; then
  echo "SKIP_PIP=1 — NAVIGUIDE venv unchanged"
else
  # scipy: required by polar_engine (polar interpolation), missing from requirements
  "$UV" pip install --python .venv/bin/python \
    -r naviguide-api/requirements.txt \
    -r naviguide_workspace/requirements.txt \
    scipy
fi

# ── Secrets (EnvironmentFile of the systemd units) ──────────────────────────────
mkdir -p "$CONF_DIR"
if [ ! -f "$CONF_DIR/naviguide.env" ]; then
  umask 077
  cp "$APP/infra/vps/naviguide/naviguide.env.example" "$CONF_DIR/naviguide.env"
  echo "⚠  $CONF_DIR/naviguide.env créé — renseigner les clés LLM (NVIDIA/OpenRouter/Anthropic) et COPERNICUS_*"
fi

# ── Frontend: production build (VITE_* → https://www.naviguide.fr) ───────────
cd "$NAV/naviguide-app"
if [ "$SKIP_FRONTEND_BUILD" = "1" ]; then
  if [ ! -f dist/index.html ]; then
    echo "SKIP_FRONTEND_BUILD=1 mais naviguide-app/dist/index.html est absent." >&2
    exit 1
  fi
  echo "SKIP_FRONTEND_BUILD=1 — bundle GitHub réutilisé"
else
  npm install --no-audit --no-fund
  npm run build
fi

# ── Services systemd ──────────────────────────────────────────────────────────
sudo cp "$APP"/infra/vps/naviguide/naviguide-api.service \
        "$APP"/infra/vps/naviguide/naviguide-orchestrator.service \
        "$APP"/infra/vps/naviguide/naviguide-polar.service \
        /etc/systemd/system/
sudo systemctl daemon-reload
for svc in naviguide-api naviguide-orchestrator naviguide-polar; do
  sudo systemctl enable "$svc" >/dev/null 2>&1 || true
  sudo systemctl restart "$svc"
done

# ── Frontend published outside /home (www-data must not walk the repo) ────
WWW_ROOT=/var/www/naviguide
sudo mkdir -p "$WWW_ROOT"
sudo rsync -a --delete "$NAV/naviguide-app/dist/" "$WWW_ROOT/"
sudo chown -R ubuntu:ubuntu "$WWW_ROOT"
sudo chmod -R a+rX "$WWW_ROOT"

# ── nginx: installed on the first pass only (certbot edits the file) ─
if [ ! -f /etc/nginx/sites-available/naviguide ]; then
  sudo cp "$APP/infra/vps/naviguide/nginx-naviguide.conf" /etc/nginx/sites-available/naviguide
  sudo ln -sf /etc/nginx/sites-available/naviguide /etc/nginx/sites-enabled/naviguide
fi
# Existing deploys: move the root out of the repo if it still uses the old path
if grep -q 'root /home/ubuntu/blue-intelligence-map/naviguide/naviguide-app/dist;' \
     /etc/nginx/sites-available/naviguide 2>/dev/null; then
  sudo sed -i 's|root /home/ubuntu/blue-intelligence-map/naviguide/naviguide-app/dist;|root /var/www/naviguide;|' \
    /etc/nginx/sites-available/naviguide
fi
# Execute bit on the repo path: useful if an nginx root still points at dist/
chmod o+x "$HOME" "$APP"
sudo nginx -t && sudo systemctl reload nginx

# ── Health (naviguide-api loads xarray/copernicusmarine: ~10 s at startup) ──
for svc in "9000:naviguide-api" "9008:orchestrator" "9004:polar-api"; do
  port="${svc%%:*}"; name="${svc##*:}"; code=000
  for _ in $(seq 1 15); do
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port/" || true)
    [ "$code" = "200" ] && break
    sleep 2
  done
  echo "  $name (:$port) → HTTP $code"
done
