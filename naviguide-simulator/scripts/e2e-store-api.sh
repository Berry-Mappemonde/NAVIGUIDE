#!/usr/bin/env bash
# Démarre l'API hors ligne sur le stock figé (lot RF11).
# Dépliage de server/tests/fixtures/official_store.tar.gz puis uvicorn.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVE="$ROOT/server/tests/fixtures/official_store.tar.gz"
PORT="${NAVIGUIDE_API_PORT:-8010}"
WORKDIR="${NAVIGUIDE_E2E_STORE_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/naviguide-e2e-store-XXXXXX")}"
STORE="$WORKDIR/store"
VOYAGES="$WORKDIR/voyages"
mkdir -p "$STORE" "$VOYAGES"
if [[ ! -f "$ARCHIVE" ]]; then
  echo "archive absente : $ARCHIVE" >&2
  exit 1
fi
tar -xzf "$ARCHIVE" -C "$STORE"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="${NAVIGUIDE_PYTHON:-python3}"
fi
export NAVIGUIDE_OFFLINE=1
export NAVIGUIDE_OFFICIAL_STORE_DIR="$STORE"
export NAVIGUIDE_OFFICIAL_WORKER=0
export NAVIGUIDE_VOYAGE_DIR="$VOYAGES"
export NAVIGUIDE_ICI_WARM=0
export NAVIGUIDE_HINDCAST=0
export NAVIGUIDE_FORECAST_BACKEND=synthetic
export NAVIGUIDE_ZEE_LOCAL=0
export NAVIGUIDE_SEED_OFFICIAL=1
export HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:9}"
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:9}"
export ALL_PROXY="${ALL_PROXY:-http://127.0.0.1:9}"
export NO_PROXY="${NO_PROXY:-127.0.0.1,localhost}"
unset SIMULATOR_MONGO_URL || true
cd "$ROOT"
exec "$PY" -m uvicorn server.main:app --host 127.0.0.1 --port "$PORT"
