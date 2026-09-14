"""Graphe enrichi voile : portes de catamaran + décalage hors couloirs.

Ce n'est PAS un nouveau réseau mondial. On prend un moteur cargo
(searoute ou scgraph) et on :
1. insère des portes (vias) dans les zones connues (Torres, Mentawai, ±180°) ;
2. décale les longs segments océaniques hors des boîtes cargos, sauf
   dans les détroits où il faut passer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from .cargo import in_no_offset_zone, point_lane_weight
from .legs import LonLat
from .metrics import haversine_nm, path_length_nm, unwrap_lon

RouteFn = Callable[[LonLat, LonLat], list[list[float]]]


@dataclass(frozen=True)
class SailingGate:
    id: str
    vias: tuple[LonLat, ...]
    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float
    antimeridian: bool = False


GATES: tuple[SailingGate, ...] = (
    SailingGate(
        id="torres_gne_pow",
        vias=(
            # No via at 142.8°E: searoute would then connect it via the Coral Sea
            # (same class of bug as test_torres.py).
            (142.135679, -10.543294),  # WP itinéraire, Great North East Channel
            (141.90, -10.70),          # sortie Prince of Wales
        ),
        lon_min=141.0,
        lat_min=-12.5,
        lon_max=147.0,
        lat_max=-9.0,
    ),
    SailingGate(
        id="mentawai_west",
        vias=(
            (96.50, -1.20),  # ouest de Siberut — un seul via, pas un arc de 900 nm
        ),
        lon_min=88.0,
        lat_min=-10.0,
        lon_max=107.0,
        lat_max=8.0,
    ),
    SailingGate(
        id="antimeridian_pacific",
        vias=((180.0, -17.50),),
        lon_min=150.0,
        lat_min=-25.0,
        lon_max=-150.0,
        lat_max=-10.0,
        antimeridian=True,
    ),
)


def _in_gate_box(lon: float, lat: float, gate: SailingGate) -> bool:
    if gate.antimeridian:
        # Box straddling ±180°: lon > lon_min OR lon < lon_max (negative).
        lon_ok = lon >= gate.lon_min or lon <= gate.lon_max
        return lon_ok and gate.lat_min <= lat <= gate.lat_max
    return gate.lon_min <= lon <= gate.lon_max and gate.lat_min <= lat <= gate.lat_max


def _leg_crosses_antimeridian(start: LonLat, end: LonLat) -> bool:
    a, b = start[0], end[0]
    return abs(a - b) > 180 or (a > 150 and b < -150) or (a < -150 and b > 150)


def _along_track_fraction(start: LonLat, end: LonLat, via: LonLat) -> Optional[float]:
    """Projection du via sur A→B. None si trop loin de l'arc ou hors ]0, 1[."""
    ax, ay = start
    bx, by = end
    vx, vy = via
    bx = unwrap_lon(ax, bx)
    vx = unwrap_lon(ax, vx)
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom < 1e-12:
        return None
    t = ((vx - ax) * dx + (vy - ay) * dy) / denom
    if t < 0.02 or t > 0.99:
        return None
    px, py = ax + t * dx, ay + t * dy
    off_deg = math.hypot(vx - px, vy - py)
    if off_deg > 8.0:
        return None
    return t


def gates_for_leg(start: LonLat, end: LonLat) -> list[SailingGate]:
    """Portes dont au moins un via se projette sur A→B (ou antiméridien)."""
    hits: list[SailingGate] = []
    for gate in GATES:
        if gate.antimeridian:
            if _leg_crosses_antimeridian(start, end):
                hits.append(gate)
            continue
        if any(_along_track_fraction(start, end, via) is not None for via in gate.vias):
            hits.append(gate)
            continue
        if _in_gate_box(start[0], start[1], gate) or _in_gate_box(end[0], end[1], gate):
            hits.append(gate)
    return hits


def vias_for_leg(start: LonLat, end: LonLat) -> list[LonLat]:
    """Vias ordonnés le long de A→B, sans doubler un bout déjà égal à A ou B."""
    chosen: list[tuple[float, LonLat]] = []
    seen: set[LonLat] = set()
    for gate in gates_for_leg(start, end):
        for via in gate.vias:
            if via == start or via == end:
                continue
            frac = _along_track_fraction(start, end, via)
            if frac is None:
                continue
            if via in seen:
                continue
            seen.add(via)
            chosen.append((frac, via))
    chosen.sort(key=lambda item: item[0])
    return [via for _frac, via in chosen]


def stitch_via_route(route_fn: RouteFn, start: LonLat, end: LonLat) -> list[list[float]]:
    """Enchaîne le moteur cargo sur start → vias → end."""
    waypoints = [start, *vias_for_leg(start, end), end]
    coords: list[list[float]] = []
    for a, b in zip(waypoints, waypoints[1:]):
        part = route_fn(a, b)
        if not part:
            raise RuntimeError(f"sous-route vide {a} → {b}")
        if not coords:
            coords = [list(p[:2]) for p in part]
        else:
            coords.extend(list(p[:2]) for p in part[1:])
    return coords


def _destination(lon: float, lat: float, bearing_deg: float, dist_nm: float) -> LonLat:
    r_nm = 3440.065
    d = dist_nm / r_nm
    br = math.radians(bearing_deg)
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(br)
    )
    lon2 = lon1 + math.atan2(
        math.sin(br) * math.sin(d) * math.cos(lat1),
        math.cos(d) - math.sin(lat1) * math.sin(lat2),
    )
    return ((math.degrees(lon2) + 540) % 360 - 180, math.degrees(lat2))


def _bearing(a: Sequence[float], b: Sequence[float]) -> float:
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2 = math.radians(unwrap_lon(a[0], b[0]))
    lat2 = math.radians(b[1])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def offset_from_cargo(
    coords: Sequence[Sequence[float]],
    offset_nm: float = 30.0,
    min_run_nm: float = 180.0,
) -> list[list[float]]:
    """Décale une course océanique entière hors d'un couloir, pas point par point."""
    if len(coords) < 3:
        return [list(p[:2]) for p in coords]

    pts = [list(p[:2]) for p in coords]
    n = len(pts)
    i = 1
    while i < n - 1:
        lon, lat = pts[i]
        if in_no_offset_zone(lon, lat) or point_lane_weight(lon, lat) < 0.35:
            i += 1
            continue
        j = i
        run_nm = 0.0
        while j < n - 1:
            lon2, lat2 = pts[j]
            if in_no_offset_zone(lon2, lat2) or point_lane_weight(lon2, lat2) < 0.35:
                break
            run_nm += haversine_nm(pts[j - 1][0], pts[j - 1][1], lon2, lat2)
            j += 1
        if run_nm >= min_run_nm and j - i >= 2:
            br = _bearing(pts[i], pts[j - 1])
            left_w = 0.0
            right_w = 0.0
            samples = 0
            for k in range(i, j):
                left = _destination(pts[k][0], pts[k][1], br + 90, offset_nm)
                right = _destination(pts[k][0], pts[k][1], br - 90, offset_nm)
                left_w += point_lane_weight(*left)
                right_w += point_lane_weight(*right)
                samples += 1
            sign = 90 if left_w <= right_w else -90
            for k in range(i, j):
                pts[k] = list(_destination(pts[k][0], pts[k][1], br + sign, offset_nm))
            i = j
        else:
            i += 1
    return pts


MAX_VIA_RATIO = 1.35


def enriched_route(route_fn: RouteFn, start: LonLat, end: LonLat) -> list[list[float]]:
    cargo = [list(p[:2]) for p in route_fn(start, end)]
    if not vias_for_leg(start, end):
        return offset_from_cargo(cargo)
    stitched = stitch_via_route(route_fn, start, end)
    cargo_nm = path_length_nm(cargo)
    stitched_nm = path_length_nm(stitched)
    if cargo_nm > 0 and stitched_nm > cargo_nm * MAX_VIA_RATIO:
        chosen = cargo
    else:
        chosen = stitched
    return offset_from_cargo(chosen)
