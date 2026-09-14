#!/usr/bin/env bash
# Prépare la clé SSH du secret GitHub (à lancer sur le runner).
# Variables : VPS_SSH_KEY (obligatoire), VPS_HOST (défaut ubuntu@135.125.226.16)
set -euo pipefail

if [ -z "${VPS_SSH_KEY:-}" ]; then
  echo "Secret VPS_SSH_KEY manquant (Settings → Secrets and variables → Actions)." >&2
  exit 1
fi

VPS_HOST="${VPS_HOST:-ubuntu@135.125.226.16}"
HOST="${VPS_HOST##*@}"
KEY_FILE="${HOME}/.ssh/github-deploy-vps"

mkdir -p "${HOME}/.ssh"
chmod 700 "${HOME}/.ssh"
# Le secret peut arriver sans saut de ligne final.
printf '%s\n' "$VPS_SSH_KEY" > "$KEY_FILE"
chmod 600 "$KEY_FILE"

touch "${HOME}/.ssh/known_hosts"
if ! ssh-keyscan -T 20 "$HOST" >> "${HOME}/.ssh/known_hosts" 2>/tmp/keyscan.err; then
  echo "ssh-keyscan $HOST a échoué :" >&2
  cat /tmp/keyscan.err >&2
  exit 1
fi

{
  echo "VPS_HOST=$VPS_HOST"
  echo "VPS_SSH_IDENTITY=$KEY_FILE"
  echo "REMOTE_APP=/home/ubuntu/blue-intelligence-map"
} >> "${GITHUB_ENV:-/dev/stdout}"

echo "SSH prêt pour $VPS_HOST"
