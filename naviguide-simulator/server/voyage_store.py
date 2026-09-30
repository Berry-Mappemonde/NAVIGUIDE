"""Persistance voyage_{id}.json — même esprit que polar_data/."""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, Optional

_DIR = Path(os.environ.get(
    "NAVIGUIDE_VOYAGE_DIR",
    str(Path(__file__).resolve().parent / "voyage_data"),
))
_LOCK = threading.Lock()


def voyage_dir() -> Path:
    _DIR.mkdir(parents=True, exist_ok=True)
    return _DIR


def _path(voyage_id: str) -> Path:
    safe = voyage_id.replace("/", "_").replace("\\", "_").replace(" ", "_")
    return voyage_dir() / f"voyage_{safe}.json"


def save_voyage(voyage: Dict[str, Any]) -> Dict[str, Any]:
    """Écriture atomique : fichier temporaire à nom UNIQUE puis renommage.

    29 sept. 20:07 : deux remplisseurs (processus distincts, `_LOCK` ne les voit pas) ont écrit le même
    `voyage_….tmp` au changement de jour ; chacun avait ouvert le fichier avant que l'autre n'écrive, le plus
    court a recouvert le début du plus long, la fin de l'ancien est restée — « Extra data » à la lecture,
    /voyage/official en 500 toute la soirée. Avec un nom par écrivain (pid + aléa), le dernier renommage gagne,
    entier ; jamais un mélange."""
    vid = voyage["voyageId"]
    dest = _path(vid)
    payload = json.dumps(voyage, ensure_ascii=False, indent=2)
    with _LOCK:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{dest.stem}.", suffix=".tmp", dir=str(dest.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp_name, dest)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    return voyage


def load_voyage(voyage_id: str) -> Optional[Dict[str, Any]]:
    dest = _path(voyage_id)
    if not dest.exists():
        return None
    with _LOCK:
        return json.loads(dest.read_text(encoding="utf-8"))


def update_voyage(voyage_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
    voy = load_voyage(voyage_id)
    if voy is None:
        return None
    voy.update(fields)
    return save_voyage(voy)


def purge_stale_voyages(
    max_age_days: float,
    keep: Optional[set] = None,
    now: Optional[float] = None,
    on_removed=None,
) -> int:
    """Supprime les voyages de Simulation plus vieux que `max_age_days` (mtime
    du fichier). Jamais les ids de `keep` ni un voyage `official`. `on_removed(vid)`
    laisse l'appelant effacer ce qui va avec (cube de prévision). Retourne le
    nombre de voyages supprimés."""
    import time

    keep = set(keep or ())
    cutoff = (time.time() if now is None else now) - float(max_age_days) * 86400.0
    removed: list[str] = []
    root = voyage_dir()
    with _LOCK:
        for path in root.glob("voyage_*.json"):
            try:
                vid = path.stem[len("voyage_"):]
                if vid in keep or path.stat().st_mtime > cutoff:
                    continue
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("official") or data.get("voyageId") in keep:
                    continue
                path.unlink(missing_ok=True)
                removed.append(data.get("voyageId") or vid)
            except Exception:
                continue
    if on_removed:
        for vid in removed:
            try:
                on_removed(vid)
            except Exception:
                pass
    return len(removed)
