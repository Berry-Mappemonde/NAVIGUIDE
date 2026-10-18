"""Métriques comparables entre moteurs (distance, terre, Corail, trafic)."""

from __future__ import annotations

import math
from typing import Callable, Optional, Sequence

from .cargo import anti_shipping_score, lane_hits

NM_PER_KM = 1.0 / 1.852

LandFn = Callable[[float, float], bool]


def haversine_nm(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Distance orthodromique en milles nautiques (sphère)."""
    r_nm = 3440.065
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * r_nm * math.asin(min(1.0, math.sqrt(a)))


def unwrap_lon(prev: float, lon: float) -> float:
    """Rend la longitude continue par rapport au point précédent."""
    while lon - prev > 180:
        lon -= 360
    while lon - prev < -180:
        lon += 360
    return lon


def path_length_nm(coords: Sequence[Sequence[float]]) -> float:
    if len(coords) < 2:
        return 0.0
    total = 0.0
    prev_lon, prev_lat = coords[0][0], coords[0][1]
    for pt in coords[1:]:
        lon = unwrap_lon(prev_lon, pt[0])
        total += haversine_nm(prev_lon, prev_lat, lon, pt[1])
        prev_lon, prev_lat = lon, pt[1]
    return round(total, 2)


def geodesic_nm(start: Sequence[float], end: Sequence[float]) -> float:
    return round(haversine_nm(start[0], start[1], end[0], end[1]), 2)


def coral_sea_points(coords: Sequence[Sequence[float]]) -> int:
    """Même heuristique que test_regression.py (lat > -14 et lon > 147)."""
    return sum(1 for p in coords if p[1] > -14 and p[0] > 147)


def antimeridian_jumps(coords: Sequence[Sequence[float]]) -> int:
    """Sauts |Δlon| > 180° entre deux points consécutifs (trait mal déroulé)."""
    if len(coords) < 2:
        return 0
    jumps = 0
    for a, b in zip(coords, coords[1:]):
        if abs(b[0] - a[0]) > 180:
            jumps += 1
    return jumps


def land_hits(
    coords: Sequence[Sequence[float]],
    is_land: Optional[LandFn],
) -> int:
    """Points intermédiaires sur terre. 0 si pas de masque disponible."""
    if is_land is None or len(coords) < 3:
        return 0
    hits = 0
    for lon, lat in coords[1:-1]:
        try:
            if is_land(lat, lon):
                hits += 1
        except Exception:
            continue
    return hits


def crosses_dateline(start: Sequence[float], end: Sequence[float]) -> bool:
    """Vrai si A et B sont de part et d'autre du 180e (Pacifique)."""
    lon1, lon2 = start[0], end[0]
    return abs(lon1 - lon2) > 180 or (lon1 > 150 and lon2 < -150) or (lon1 < -150 and lon2 > 150)


def measure(
    coords: Sequence[Sequence[float]],
    start: Sequence[float],
    end: Sequence[float],
    elapsed_ms: float,
    is_land: Optional[LandFn] = None,
) -> dict:
    """Dictionnaire de métriques pour une polyligne [lon, lat]."""
    length = path_length_nm(coords)
    direct = geodesic_nm(start, end)
    ratio = round(length / direct, 3) if direct > 0 else None
    return {
        "n_points": len(coords),
        "length_nm": length,
        "geodesic_nm": direct,
        "length_ratio": ratio,
        "elapsed_ms": round(elapsed_ms, 1),
        "coral_sea_pts": coral_sea_points(coords),
        "land_hits": land_hits(coords, is_land),
        "antimeridian_jumps": antimeridian_jumps(coords),
        "anti_shipping": anti_shipping_score(coords),
        "lanes": lane_hits(coords),
        "ok": bool(coords) and coral_sea_points(coords) == 0,
    }
