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
