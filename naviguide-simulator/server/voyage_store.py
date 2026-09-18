"""Persistance voyage_{id}.json — même esprit que polar_data/."""
from __future__ import annotations

import json
import os
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
    vid = voyage["voyageId"]
    dest = _path(vid)
    tmp = dest.with_suffix(".tmp")
    payload = json.dumps(voyage, ensure_ascii=False, indent=2)
    with _LOCK:
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(dest)
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
