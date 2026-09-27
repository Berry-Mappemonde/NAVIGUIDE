#!/usr/bin/env python3
"""Remplit le stock du voyage officiel par le VRAI calcul (lot RF2) — dans un PROCESSUS à part (RC18).

Aucune donnée écrite en dur : une famille qui échoue reste « en préparation ».

    prepare_official_store.py                 # une passe (ensure-dev.sh --prod, avant d'ouvrir le navigateur)
    prepare_official_store.py --loop          # le remplisseur de l'API : périodique + réveil par fichier « nudge »

Pourquoi un processus : le calcul tient le GIL ; dans le processus de l'API il l'étouffait (27 sept. : 97 % CPU,
/clock en 7 s, POST /voyage coupé à 100 s). Ici il tourne en priorité basse, l'API ne fait que lire le stock.
Dos : disque (NAVIGUIDE_OFFICIAL_STORE_DIR) ou MongoDB si SIMULATOR_MONGO_URL est posé (VPS) — le même que l'API.
"""
from __future__ import annotations

import argparse
import os
import signal
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
os.environ["NAVIGUIDE_OFFICIAL_WORKER"] = "0"   # ce processus EST le remplisseur : pas de fil, pas d'enfant

LABELS = {
    "climo": "horloge / climatologie",
    "moments": "journal des moments",
    "film": "script du film",
    "eta": "ETA et fourchettes",
    "ici": "sacs « ici »",
    "plan_review": "revue du plan",
}

_STOP = False


def _say(msg: str) -> None:
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}", flush=True)


def _progress_printer(n: int):
    import official_store
    from official_store import COMPUTE_ORDER, READY

    def progress(family: str, status: str, detail: str = "") -> None:
        if family == "*":
            _say(f"  · {status} {detail}".rstrip())
            return
        label = LABELS.get(family, family)
        idx = COMPUTE_ORDER.index(family) + 1 if family in COMPUTE_ORDER else "?"
        mark = "prêt" if status == READY else ("déjà en stock" if status == "unchanged" else "en préparation")
        extra = f" — {detail}" if detail else ""
        _say(f"[{idx}/{n}] {label} … {mark}{extra}")

    return progress


def one_pass(*, force_film: bool = False) -> int:
    import official_store
    from official_store import COMPUTE_ORDER, READY

    n = len(COMPUTE_ORDER)
    t0 = time.monotonic()
    out = official_store.refresh_missing(progress=_progress_printer(n))
    if force_film:
        try:
            official_store.refresh_family("film", force=True)
            _say("[film] script recalculé (révision courante)")
        except Exception as exc:  # jamais fatal
            _say(f"[film] recalcul impossible : {exc}")
    families = (out or {}).get("families") or {}
    ready = sum(1 for v in families.values() if v.get("status") == READY)
    _say(f"passage terminé en {time.monotonic() - t0:.0f} s — {ready}/{n} familles prêtes")
    for name in COMPUTE_ORDER:
        st = (families.get(name) or {}).get("status") or "preparing"
        _say(f"  {LABELS[name]} : {st}")
    return ready


def _nudge_stamp(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def loop(period_s: float) -> int:
    import official_store

    pidfile = official_store.fill_pidfile()
    nudge = official_store.fill_nudgefile()
    try:
        pidfile.parent.mkdir(parents=True, exist_ok=True)
        me = Path(__file__).resolve()
        pidfile.write_text(f"{os.getpid()}\n{me}\n{me.stat().st_mtime_ns}\n", encoding="utf-8")
    except OSError:
        pass

    def _stop(signum, _frame):
        global _STOP
        _STOP = True
        _say(f"signal {signum} : arrêt après le passage en cours")

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    _say(f"remplisseur en boucle (pid {os.getpid()}, période {int(period_s)} s, réveil par {nudge.name})")
    last_nudge = _nudge_stamp(nudge)
    first = True
    while not _STOP:
        try:
            one_pass(force_film=first)
        except Exception as exc:  # le remplisseur ne meurt pas d'une exception
            _say(f"passage en erreur : {type(exc).__name__}: {exc}")
        first = False
        deadline = time.monotonic() + max(60.0, period_s)
        while not _STOP and time.monotonic() < deadline:
            time.sleep(5)
            stamp = _nudge_stamp(nudge)
            if stamp > last_nudge:
                last_nudge = stamp
                _say("réveil demandé par l'API")
                break
    try:
        if pidfile.exists() and pidfile.read_text(encoding="utf-8").split()[0] == str(os.getpid()):
            pidfile.unlink()
    except (OSError, IndexError):
        pass
    _say("remplisseur arrêté")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--loop", action="store_true", help="tourner en continu : une passe, puis toutes les --period s ou au réveil")
    ap.add_argument("--period", type=float, default=float(os.environ.get("NAVIGUIDE_OFFICIAL_STORE_PERIOD_S") or 6 * 3600))
    ap.add_argument("--nice", type=int, default=10, help="priorité basse (os.nice) ; 0 = priorité normale")
    args = ap.parse_args()

    if args.nice:
        try:
            os.nice(args.nice)
        except OSError:
            pass
    dest = Path(os.environ["NAVIGUIDE_OFFICIAL_STORE_DIR"])
    dest.mkdir(parents=True, exist_ok=True)
    _say(f"stock : {'MongoDB (SIMULATOR_MONGO_URL)' if os.environ.get('SIMULATOR_MONGO_URL') else dest}")
    _say("calcul réel — aucune donnée écrite en dur")

    import official_store
    official_store.reset_store()
    if args.loop:
        return loop(args.period)
    one_pass()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
