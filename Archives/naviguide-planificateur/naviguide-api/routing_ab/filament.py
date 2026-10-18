"""Décalage par rapport au *fil* cargo, pas par rapport à un grand rectangle.

En pleine mer : on pousse le trait de ``offset_nm`` perpendiculairement
à l'autoroute searoute. Près d'une terre ou dans un détroit : on ne touche pas.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from .cargo import in_no_offset_zone
from .enriched import _bearing, _destination
from .metrics import haversine_nm, unwrap_lon

LandFn = Optional[Callable[[float, float], bool]]


def dist_to_filament_nm(lon: float, lat: float, filament: Sequence[Sequence[float]]) -> float:
    """Distance au fil : plus proche sommet (suffisant pour un couloir océan)."""
    if not filament:
        return 0.0
    return min(haversine_nm(lon, lat, p[0], p[1]) for p in filament)


def mean_dist_to_filament_nm(
    coords: Sequence[Sequence[float]],
    filament: Sequence[Sequence[float]],
) -> float:
    if not coords or not filament:
        return 0.0
    vals = [dist_to_filament_nm(p[0], p[1], filament) for p in coords]
    return round(sum(vals) / len(vals), 2)


def _near_land(lon: float, lat: float, is_land, radius_deg: float = 0.35) -> bool:
    if is_land is None:
        return False
    for dlat in (-radius_deg, 0.0, radius_deg):
        for dlon in (-radius_deg, 0.0, radius_deg):
            try:
                if is_land(lat + dlat, lon + dlon):
                    return True
            except Exception:
                continue
    return False


def offset_from_filament(
    cargo: Sequence[Sequence[float]],
    offset_nm: float = 20.0,
    keep_ends_frac: float = 0.18,
    is_land=None,
) -> list[list[float]]:
    """Pousse le milieu océanique 20 nm à côté du fil cargo."""
    pts = [list(p[:2]) for p in cargo]
    n = len(pts)
    if n < 4:
        return pts
    start_i = max(1, int(n * keep_ends_frac))
    end_i = min(n - 1, int(n * (1.0 - keep_ends_frac)))
    if end_i - start_i < 2:
        return pts

    br = _bearing(pts[start_i], pts[end_i - 1])
    # Side: try both, keep the one that stays at sea most often.
    best = pts
    best_water = -1
    for sign in (90, -90):
        trial = [list(p) for p in pts]
        water = 0
        for k in range(start_i, end_i):
            lon, lat = pts[k]
            if in_no_offset_zone(lon, lat) or _near_land(lon, lat, is_land):
                continue
            trial[k] = list(_destination(lon, lat, br + sign, offset_nm))
            if is_land is None or not _near_land(trial[k][0], trial[k][1], is_land):
                water += 1
        if water > best_water:
            best_water = water
            best = trial
    return best


def unwrap_path(coords: Sequence[Sequence[float]]) -> list[list[float]]:
    if not coords:
        return []
    out = [list(coords[0][:2])]
    for pt in coords[1:]:
        lon = unwrap_lon(out[-1][0], pt[0])
        out.append([lon, pt[1]])
    return out
