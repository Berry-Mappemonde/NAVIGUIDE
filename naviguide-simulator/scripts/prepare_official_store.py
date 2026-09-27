#!/usr/bin/env python3
"""Remplit le stock DISQUE du voyage officiel par le VRAI calcul (lot RF2).

Aucune donnée écrite en dur : une famille qui échoue reste « en préparation ».
À lancer avant d'ouvrir le navigateur (ensure-dev.sh --prod).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
sys.path.insert(0, str(SERVER))

os.environ.setdefault(
    "NAVIGUIDE_OFFICIAL_STORE_DIR",
    str(Path.home() / ".cache" / "naviguide" / "voyage-store"),
)
os.environ["NAVIGUIDE_OFFICIAL_WORKER"] = "0"
os.environ.pop("SIMULATOR_MONGO_URL", None)

LABELS = {
    "climo": "horloge / climatologie",
    "moments": "journal des moments",
    "film": "script du film",
    "eta": "ETA et fourchettes",
    "ici": "sacs « ici »",
    "plan_review": "revue du plan",
}


def main() -> int:
    dest = Path(os.environ["NAVIGUIDE_OFFICIAL_STORE_DIR"])
    dest.mkdir(parents=True, exist_ok=True)
    print(f"stock disque : {dest}", flush=True)
    print("calcul réel — aucune donnée écrite en dur", flush=True)

    import official_store
    from official_store import COMPUTE_ORDER, READY

    t0 = time.monotonic()
    n = len(COMPUTE_ORDER)

    def progress(family: str, status: str, detail: str = "") -> None:
        if family == "*":
            print(f"  · {status} {detail}".rstrip(), flush=True)
            return
        label = LABELS.get(family, family)
        idx = COMPUTE_ORDER.index(family) + 1 if family in COMPUTE_ORDER else "?"
        mark = "prêt" if status == READY else ("déjà en stock" if status == "unchanged" else "en préparation")
        extra = f" — {detail}" if detail else ""
        print(f"[{idx}/{n}] {label} … {mark}{extra}", flush=True)

    official_store.reset_store()
    out = official_store.refresh_missing(progress=progress)
    families = (out or {}).get("families") or {}
    ready = sum(1 for v in families.values() if v.get("status") == READY)
    elapsed = time.monotonic() - t0
    print(f"terminé en {elapsed:.0f} s — {ready}/{n} familles prêtes", flush=True)
    for name in COMPUTE_ORDER:
        st = (families.get(name) or {}).get("status") or "preparing"
        print(f"  {LABELS[name]} : {st}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
