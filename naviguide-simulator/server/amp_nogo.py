"""AMP interdites (entry=1 ou speed=1) comme zones no-go de l'isochrone.

Le catalogue monde des interdites est petit (~50). On le charge une fois
depuis GET /amp/nogo. Si l'API ne répond pas, aucun extra no-go (rien d'inventé).
Un parc qui contient déjà le départ ou l'arrivée n'est pas bloqué : on peut en sortir.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Iterable

import httpx

from amp_traffic import geom_bbox, is_forbidden_pleasure, point_in_geom

log = logging.getLogger("naviguide-simulator.amp_nogo")

_NOGO_TTL = 3600.0
_nogo_cache: dict[str, Any] = {"ts": 0.0, "items": None}


def _bi_base() -> str:
    return (os.getenv("BI_API_URL") or "https://blueintelligence.online/api").rstrip("/")


def _item_from_feature(feat: dict) -> dict | None:
    geom = feat.get("geometry") if isinstance(feat, dict) else None
    if not isinstance(geom, dict) or geom.get("type") not in ("Polygon", "MultiPolygon"):
        return None
    props = feat.get("properties") or {}
    if not is_forbidden_pleasure(props.get("entry"), props.get("speed")):
        return None
    box = geom_bbox(geom)
    if not box:
        return None
    sid = str(props.get("site_id") or props.get("id") or feat.get("id") or "").strip()
    return {"id": sid or None, "geom": geom, "bbox": box, "name": props.get("name")}


def load_forbidden_nogo(*, fetch_fn=None, ttl: float = _NOGO_TTL) -> list[dict]:
    now = time.time()
    if _nogo_cache["items"] is not None and now - float(_nogo_cache["ts"] or 0) < ttl:
        return _nogo_cache["items"]
    fetch = fetch_fn or _fetch_nogo
    try:
        data = fetch()
    except Exception as exc:
        log.warning("AMP nogo indisponible : %s", exc)
        if _nogo_cache["items"] is None:
            _nogo_cache["ts"] = now
            _nogo_cache["items"] = []
        return list(_nogo_cache["items"] or [])
    items = []
    for feat in (data.get("features") if isinstance(data, dict) else None) or []:
        item = _item_from_feature(feat)
        if item:
            items.append(item)
    _nogo_cache["ts"] = now
    _nogo_cache["items"] = items
    return items


def _fetch_nogo() -> dict:
    url = f"{_bi_base()}/amp/nogo"
    r = httpx.get(url, timeout=20.0, headers={"Accept": "application/json"})
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, dict) else {"features": []}


def reset_nogo_cache() -> None:
    _nogo_cache["ts"] = 0.0
    _nogo_cache["items"] = None


def _in_bbox(lon: float, lat: float, box: tuple[float, float, float, float]) -> bool:
    return box[0] <= lon <= box[2] and box[1] <= lat <= box[3]


def ids_containing(items: list[dict], points: Iterable[tuple[float, float]]) -> set:
    found: set = set()
    for lat, lon in points:
        try:
            la, lo = float(lat), float(lon)
        except (TypeError, ValueError):
            continue
        for item in items:
            if item.get("id") and _in_bbox(lo, la, item["bbox"]) and point_in_geom(lo, la, item["geom"]):
                found.add(item["id"])
    return found


def amp_nogo_fn(
    items: list[dict] | None,
    *,
    escape_points: Iterable[tuple[float, float]] | None = None,
) -> Callable:
    """True = ce pas tombe dans une AMP interdite (hors parcs déjà occupés)."""
    pool = list(items or [])
    skip = ids_containing(pool, escape_points or ())
    active = [it for it in pool if not it.get("id") or it["id"] not in skip]

    def fn(lat: float, lon: float, _t=None) -> bool:
        try:
            la, lo = float(lat), float(lon)
        except (TypeError, ValueError):
            return False
        for item in active:
            if _in_bbox(lo, la, item["bbox"]) and point_in_geom(lo, la, item["geom"]):
                return True
        return False

    return fn
