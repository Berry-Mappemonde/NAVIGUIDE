"""GRIB2 journalier autour du bateau (Saildocs). Pas un GRIB globe.

Le skipper dépose le fichier du jour (inbox ou POST). Fenêtre : ~200 nm
autour de la position actuelle, quelques jours, modèle nommé (GFS).
"""
from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from voyage_clock import OFFICIAL_VOYAGE_ID, parse_iso, to_iso

DAILY_RADIUS_NM = 200.0
DAILY_LEAD_HOURS = 72
DAILY_STEP_HOURS = 6
MAX_BBOX_LAT_SPAN = 12.0
MAX_BBOX_LON_SPAN = 20.0
GRIB_MISSING = "prévision du jour absente"

GRIB_DIR = Path(os.environ.get(
    "NAVIGUIDE_GRIB_DIR",
    str(Path(__file__).resolve().parent / "grib_data"),
))
INBOX_DIR = Path(os.environ.get(
    "NAVIGUIDE_SAILDOCS_INBOX",
    str(Path(__file__).resolve().parent / "saildocs_inbox"),
))


def utc_day(when: Optional[datetime] = None) -> str:
    dt = when or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")


def bbox_around(lat: float, lon: float, radius_nm: float = DAILY_RADIUS_NM) -> Tuple[float, float, float, float]:
    """(south, north, west, east) — couloir, pas le globe."""
    dlat = radius_nm / 60.0
    cos_lat = max(0.2, math.cos(math.radians(lat)))
    dlon = radius_nm / (60.0 * cos_lat)
    south = max(-90.0, lat - dlat)
    north = min(90.0, lat + dlat)
    west = lon - dlon
    east = lon + dlon
    return (round(south, 4), round(north, 4), round(west, 4), round(east, 4))


def lon_span(west: float, east: float) -> float:
    span = abs(east - west)
    if span > 180:
        span = 360 - span
    return span


def assert_corridor_not_globe(bbox: Tuple[float, float, float, float]) -> None:
    south, north, west, east = bbox
    if (north - south) > MAX_BBOX_LAT_SPAN:
        raise ValueError("bbox trop large : GRIB globe interdit")
    if lon_span(west, east) > MAX_BBOX_LON_SPAN:
        raise ValueError("bbox trop large : GRIB globe interdit")


def _hem_lat(v: float) -> str:
    return f"{abs(v):.1f}{'N' if v >= 0 else 'S'}"


def _hem_lon(v: float) -> str:
    return f"{abs(v):.1f}{'E' if v >= 0 else 'W'}"


def saildocs_query(
    lat: float,
    lon: float,
    *,
    radius_nm: float = DAILY_RADIUS_NM,
    model: str = "GFS",
    hours: int = DAILY_LEAD_HOURS,
    step: int = DAILY_STEP_HOURS,
) -> str:
    """Requête Saildocs skipper : vent autour du bateau, pas le monde."""
    south, north, west, east = bbox_around(lat, lon, radius_nm)
    assert_corridor_not_globe((south, north, west, east))
    window = f"0,{step}..{hours}"
    return (
        f"{model}:{_hem_lat(north)},{_hem_lat(south)},"
        f"{_hem_lon(west)},{_hem_lon(east)}|0.25,0.25|{window}|WIND"
    )


def grib_dir() -> Path:
    GRIB_DIR.mkdir(parents=True, exist_ok=True)
    return GRIB_DIR


def inbox_dir() -> Path:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    return INBOX_DIR


def _safe_id(voyage_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", voyage_id)


def daily_path(voyage_id: str, day: str) -> Path:
    return grib_dir() / f"{_safe_id(voyage_id)}_{day}.json"


def load_daily(voyage_id: str, day: Optional[str] = None) -> Optional[Dict[str, Any]]:
    dest = daily_path(voyage_id, day or utc_day())
    if not dest.exists():
        return None
    return json.loads(dest.read_text(encoding="utf-8"))


def save_daily(record: Dict[str, Any]) -> Dict[str, Any]:
    dest = daily_path(record["voyageId"], record["day"])
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(dest)
    return record


def knots_from_uv(u: float, v: float) -> Tuple[float, float]:
    speed_ms = math.hypot(u, v)
    knots = speed_ms * 1.943844
    # meteorological from-direction
    coming = (math.degrees(math.atan2(-u, -v)) + 360.0) % 360.0
    return round(knots, 2), round(coming, 1)


def wind_at_daily(record: Optional[dict], lat: float, lon: float, when: datetime) -> Optional[Dict[str, Any]]:
    if not record or record.get("status") != "ready":
        return None
    samples = record.get("samples") or []
    if not samples:
        return None
    when_iso = to_iso(when) if isinstance(when, datetime) else str(when)
    best = None
    best_d = None
    for s in samples:
        d = (float(s.get("lat") or 0) - lat) ** 2 + (float(s.get("lon") or 0) - lon) ** 2
        t = str(s.get("t") or s.get("iso") or "")
        if t and abs(parse_iso(t).timestamp() - parse_iso(when_iso).timestamp()) > 12 * 3600:
            continue
        if best_d is None or d < best_d:
            best_d = d
            best = s
    if best is None:
        best = samples[0]
    knots = best.get("windKnots")
    direction = best.get("dirFromDeg")
    if knots is None and best.get("u") is not None and best.get("v") is not None:
        knots, direction = knots_from_uv(float(best["u"]), float(best["v"]))
    if knots is None:
        return None
    return {
        "windKnots": float(knots),
        "dirFromDeg": float(direction) if direction is not None else None,
        "model": record.get("model") or "GFS",
        "kind": "forecast",
        "t": best.get("t"),
    }


def _parse_bbox(raw: Any, around: Optional[dict], radius_nm: float) -> Tuple[float, float, float, float]:
    if raw and len(raw) == 4:
        return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))
    if around and around.get("lat") is not None and around.get("lon") is not None:
        return bbox_around(float(around["lat"]), float(around["lon"]), radius_nm)
    raise ValueError("bbox ou around requis")


def ingest_daily(
    voyage_id: str,
    payload: Dict[str, Any],
    *,
    around: Optional[dict] = None,
) -> Dict[str, Any]:
    day = payload.get("day") or utc_day()
    radius = float(payload.get("radiusNm") or DAILY_RADIUS_NM)
    if radius > DAILY_RADIUS_NM * 1.5:
        raise ValueError("rayon trop large : pas un GRIB globe")
    here = around or payload.get("around")
    bbox = _parse_bbox(payload.get("bbox"), here, radius)
    assert_corridor_not_globe(bbox)
    model = str(payload.get("model") or "GFS")
    query = payload.get("query")
    if not query and here:
        query = saildocs_query(float(here["lat"]), float(here["lon"]), radius_nm=radius, model=model)
    record = {
        "voyageId": voyage_id,
        "day": day,
        "status": "ready",
        "model": model,
        "source": payload.get("source") or "saildocs",
        "issued": payload.get("issued") or to_iso(datetime.now(timezone.utc)),
        "bbox": list(bbox),
        "radiusNm": radius,
        "around": here,
        "query": query,
        "samples": payload.get("samples") or [],
        "warning": None,
    }
    return save_daily(record)


def absent_payload(voyage_id: str, day: Optional[str] = None, around: Optional[dict] = None) -> Dict[str, Any]:
    here = around or {}
    query = None
    bbox = None
    if here.get("lat") is not None and here.get("lon") is not None:
        bbox = list(bbox_around(float(here["lat"]), float(here["lon"])))
        query = saildocs_query(float(here["lat"]), float(here["lon"]))
    return {
        "voyageId": voyage_id,
        "day": day or utc_day(),
        "status": "absent",
        "model": None,
        "source": "saildocs",
        "bbox": bbox,
        "radiusNm": DAILY_RADIUS_NM,
        "around": here or None,
        "query": query,
        "samples": [],
        "warning": GRIB_MISSING,
    }


def public_grib(record: Optional[dict], voyage_id: str = OFFICIAL_VOYAGE_ID,
                around: Optional[dict] = None, when: Optional[datetime] = None) -> Dict[str, Any]:
    day = utc_day(when)
    if not record:
        body = absent_payload(voyage_id, day, around)
    else:
        body = {
            "voyageId": record.get("voyageId", voyage_id),
            "day": record.get("day", day),
            "status": record.get("status") or "ready",
            "model": record.get("model"),
            "source": record.get("source") or "saildocs",
            "issued": record.get("issued"),
            "bbox": record.get("bbox"),
            "radiusNm": record.get("radiusNm") or DAILY_RADIUS_NM,
            "around": record.get("around") or around,
            "query": record.get("query"),
            "warning": record.get("warning"),
        }
    wind = None
    if around and record and around.get("lat") is not None and around.get("lon") is not None:
        wind = wind_at_daily(
            record,
            float(around["lat"]),
            float(around["lon"]),
            when or datetime.now(timezone.utc),
        )
    body["wind"] = wind
    if body["status"] != "ready":
        body["warning"] = GRIB_MISSING
    return body


def scan_inbox(voyage_id: str, day: Optional[str] = None, around: Optional[dict] = None) -> Optional[Dict[str, Any]]:
    """Lit un JSON Saildocs du jour dans l’inbox (YYYYMMDD*.json)."""
    d = day or utc_day()
    stamp = d.replace("-", "")
    folder = inbox_dir()
    matches: List[Path] = sorted(folder.glob(f"{stamp}*.json"))
    if not matches:
        matches = sorted(folder.glob(f"*{stamp}*.json"))
    for path in matches:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if around and not payload.get("around"):
            payload["around"] = around
        try:
            return ingest_daily(voyage_id, payload, around=payload.get("around") or around)
        except ValueError:
            continue
    return None
