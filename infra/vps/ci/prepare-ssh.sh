#!/usr/bin/env bash
# Prépare la clé SSH du secret GitHub (à lancer sur le runner).
# Variables : VPS_SSH_KEY et VPS_HOST, tous deux obligatoires.
# VPS_HOST = naviguide@13.140.164.185. Pas de défaut : un secret vide
# ne doit pas déployer sur l'OVH.
set -euo pipefail

if [ -z "${VPS_SSH_KEY:-}" ]; then
  echo "Secret VPS_SSH_KEY manquant (Settings → Secrets and variables → Actions)." >&2
  exit 1
fi

if [ -z "${VPS_HOST:-}" ]; then
  echo "Secret VPS_HOST manquant. Valeur attendue : naviguide@13.140.164.185." >&2
  exit 1
fi
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
  echo "REMOTE_APP=/home/naviguide/naviguide"
} >> "${GITHUB_ENV:-/dev/stdout}"

echo "SSH prêt pour $VPS_HOST"
