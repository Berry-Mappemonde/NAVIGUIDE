"""Sous-processus : calcule une route searoute et écrit du GeoJSON sur stdout.

Sert à comparer searoute 1.4 et 1.6 sans mélanger deux versions dans
le même interpréteur.
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: searoute_worker.py '[lon,lat]' '[lon,lat]'", file=sys.stderr)
        return 2
    start = json.loads(sys.argv[1])
    end = json.loads(sys.argv[2])
    import searoute as sr  # noqa: WPS433 — import local volontaire (venv dédié)

    route = sr.searoute((float(start[0]), float(start[1])), (float(end[0]), float(end[1])))
    json.dump(route, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
