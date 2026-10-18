#!/usr/bin/env python3
"""Recalcule moments (ancres côte) et film officiel après déploiement RG10 / RG14.

Ne supprime pas le stock existant : `refresh_family(..., force=True)` remplace
les familles concernées par une nouvelle révision (MOMENTS_REV / FILM_SCRIPT_REV).

Usage (poste de recette, même stock que l'API 8010) :

    cd naviguide-simulator
    export NAVIGUIDE_OFFICIAL_STORE_DIR="${NAVIGUIDE_OFFICIAL_STORE_DIR:-$HOME/.cache/naviguide/voyage-store}"
    python3 scripts/reanchor_official_moments.py

Production (VPS, service naviguide-simulator, Mongo ou disque selon l'env) :

    sudo -u naviguide bash -lc '
      cd /opt/naviguide/Blue-Intelligence/naviguide-simulator
      source /etc/naviguide/simulator.env 2>/dev/null || true
      python3 scripts/reanchor_official_moments.py
    '
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
sys.path.insert(0, str(SERVER))

os.environ.setdefault(
    "NAVIGUIDE_OFFICIAL_STORE_DIR",
    str(Path.home() / ".cache" / "naviguide" / "voyage-store"),
)
os.environ["NAVIGUIDE_OFFICIAL_WORKER"] = "0"


def _realign_clock_mark_isos() -> int:
    """Recolle les iso/lat/lon des marques d'horloge sur le passage géographique (hub)."""
    import official_store
    from film_script import _align_quay_stop_to_passage

    hit = official_store.get("climo") or official_store.stored_clock()
    if not isinstance(hit, dict):
        print("  climo/horloge : absent", flush=True)
        return 0
    payload = hit.get("payload") if isinstance(hit.get("payload"), dict) else hit
    clock = payload.get("clock") if isinstance(payload.get("clock"), dict) else payload
    marks = list(clock.get("marks") or [])
    if not marks:
        print("  horloge : pas de marques", flush=True)
        return 0
    aligned = [_align_quay_stop_to_passage(m, clock) for m in marks]
    if aligned == marks:
        print("  horloge : marques déjà cohérentes", flush=True)
        return 0
    clock = {**clock, "marks": aligned}
    if "clock" in payload:
        payload = {**payload, "clock": clock}
    else:
        payload = clock
    official_store.put("climo", payload, status=official_store.READY)
    print(f"  horloge : {sum(1 for a, b in zip(aligned, marks) if a != b)} marque(s) recollée(s)", flush=True)
    return 0


def main() -> int:
    import official_store

    official_store.reset_store()
    dest = Path(os.environ["NAVIGUIDE_OFFICIAL_STORE_DIR"])
    print(f"stock : {dest}", flush=True)
    _realign_clock_mark_isos()
    for family in ("moments", "film"):
        official_store.refresh_family(family, force=True)
        hit = official_store.get(family)
        status = (hit or {}).get("status") or "?"
        print(f"  {family} : {status}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
