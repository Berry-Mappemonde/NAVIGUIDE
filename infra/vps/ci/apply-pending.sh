#!/usr/bin/env bash
# Reprend les déploiements reportés (à lancer SUR le VPS).
set -euo pipefail

APP="${APP:-$HOME/blue-intelligence-map}"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/blue-intelligence-deploy"
APPLY="$APP/infra/vps/ci/apply-site.sh"

mkdir -p "$STATE/pending"
any=0
for site in blue-intelligence naviguide simulator; do
  pending="$STATE/pending/$site"
  [ -f "$pending" ] || continue
  any=1
  SHA="$(awk -F= '/^SHA=/{print substr($0,5); exit}' "$pending")"
  echo "→ pending $site SHA=${SHA:-?} (fichier $pending)"
  SHA="$SHA" SKIP_FRONTEND_BUILD=1 bash "$APPLY" "$site"
done

if [ "$any" -eq 0 ]; then
  echo "Aucun déploiement en attente."
fi
