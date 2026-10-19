#!/usr/bin/env bash
# Copie le code d'un site vers le VPS (sans --delete dangereux à la racine).
# Usage : rsync-to-vps.sh simulator   (site live naviguide.fr)
# Env : VPS_HOST, VPS_SSH_IDENTITY, REMOTE_APP
set -euo pipefail

SITE="${1:?usage: rsync-to-vps.sh simulator}"
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
VPS="${VPS_HOST:?VPS_HOST manquant}"
REMOTE="${REMOTE_APP:-/home/naviguide/naviguide}"
IDENTITY="${VPS_SSH_IDENTITY:?VPS_SSH_IDENTITY manquant}"

RSH=(ssh -i "$IDENTITY" -o BatchMode=yes -o IdentitiesOnly=yes -o ConnectTimeout=20)

remote() {
  "${RSH[@]}" "$VPS" "$@"
}

rsync_to() {
  rsync -az --omit-dir-times -e "${RSH[*]}" "$@"
}

echo "→ rsync $SITE → $VPS:$REMOTE"
remote "mkdir -p $REMOTE/infra/vps/ci $REMOTE/infra/vps/naviguide $REMOTE/naviguide-simulator"

# Toujours envoyer la sonde et apply-*.sh (rattrapage + premier déploiement).
rsync_to "$ROOT/infra/vps/ci/" "$VPS:$REMOTE/infra/vps/ci/"
remote "chmod +x $REMOTE/infra/vps/ci/*.sh $REMOTE/infra/vps/ci/*.py || true"

case "$SITE" in
  simulator)
    rsync_to --delete \
      --exclude node_modules \
      --exclude .venv \
      --exclude .pytest_cache \
      --exclude __pycache__ \
      --exclude .env \
      --exclude server/polar_data/ \
      --exclude server/voyage_data/ \
      --exclude server/grib_data/ \
      --exclude server/forecast_cache/ \
      --exclude server/saildocs_inbox/ \
      "$ROOT/naviguide-simulator/" "$VPS:$REMOTE/naviguide-simulator/"
    rsync_to \
      "$ROOT/infra/vps/naviguide/nginx-simulator.conf" \
      "$ROOT/infra/vps/naviguide/nginx-simulator-limits.conf" \
      "$ROOT/infra/vps/naviguide/nginx-simulator-443-redirects.conf" \
      "$ROOT/infra/vps/naviguide/naviguide-simulator.service" \
      "$ROOT/infra/vps/naviguide/naviguide-film-front.service" \
      "$ROOT/infra/vps/naviguide/deploy-simulator.sh" \
      "$ROOT/infra/vps/naviguide/simulator.env.example" \
      "$ROOT/infra/vps/naviguide/publish-simulator-from-mac.sh" \
      "$VPS:$REMOTE/infra/vps/naviguide/"
    # Cache nginx climatologie BI (installé par deploy-simulator.sh).
    rsync_to \
      "$ROOT/infra/vps/nginx-bi-climatology-cache.conf" \
      "$ROOT/infra/vps/nginx-snippet-bi-climatology.conf" \
      "$VPS:$REMOTE/infra/vps/"
    ;;
  *)
    echo "site inconnu: $SITE" >&2
    exit 1
    ;;
esac

# nginx / www-data doivent pouvoir traverser le dossier personnel et le dépôt.
remote "chmod o+x \"\$HOME\" $REMOTE"

echo "rsync $SITE OK"
