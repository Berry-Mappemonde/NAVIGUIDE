#!/usr/bin/env bash
# Marque qu’une édition a touché naviguide-simulator/ (lu par le hook stop).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
FLAG="$REPO/naviguide-simulator/.dev/open-browser-on-stop"
mkdir -p "$(dirname "$FLAG")"

python3 - "$FLAG" <<'PY'
import json, sys
from pathlib import Path

flag = Path(sys.argv[1])
try:
    data = json.loads(sys.stdin.read() or "{}")
except json.JSONDecodeError:
    sys.exit(0)

needle = "naviguide-simulator/"

def strings(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)
    elif isinstance(obj, str):
        yield obj

for s in strings(data):
    norm = s.replace("\\", "/")
    if needle in norm or norm.startswith("naviguide-simulator"):
        flag.write_text("1")
        break
PY

exit 0
