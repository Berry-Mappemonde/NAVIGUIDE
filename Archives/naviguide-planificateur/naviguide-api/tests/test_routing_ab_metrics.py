"""Métriques du banc A/B — sans réseau, sans searoute."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routing_ab.cargo import anti_shipping_score
from routing_ab.metrics import (
    antimeridian_jumps,
    coral_sea_points,
    geodesic_nm,
    haversine_nm,
    land_hits,
    measure,
    path_length_nm,
    unwrap_lon,
)


def test_haversine_known_distance():
    # La Rochelle → roughly 0 nm
    assert haversine_nm(-1.167, 46.1541, -1.167, 46.1541) == 0
    # ~1 degree of latitude ≈ 60 nm
    d = haversine_nm(0, 0, 0, 1)
    assert 59 < d < 61


def test_unwrap_lon_dateline():
    assert unwrap_lon(179.0, -179.0) == 181.0
    assert unwrap_lon(-179.0, 179.0) == -181.0


def test_path_length_unwraps_dateline():
    coords = [[179.5, -17.0], [-179.5, -17.0]]
    nm = path_length_nm(coords)
    assert nm < 130  # ~120 nm, not 12 000


def test_coral_sea_heuristic():
    assert coral_sea_points([[150.0, -12.0]]) == 1
    assert coral_sea_points([[142.0, -10.7]]) == 0


def test_antimeridian_jumps():
    assert antimeridian_jumps([[179.0, 0], [-179.0, 0]]) == 1
    assert antimeridian_jumps([[10.0, 0], [11.0, 0]]) == 0


def test_land_hits_uses_callback():
    coords = [[0, 0], [1, 1], [2, 2]]
    assert land_hits(coords, lambda lat, lon: lat == 1) == 1
    assert land_hits(coords, None) == 0


def test_anti_shipping_quiet_vs_busy():
    quiet = [[-30.0, 0.0], [-35.0, 2.0]]
    busy = [[0.5, 51.0], [1.0, 51.2]]  # Pas-de-Calais
    assert anti_shipping_score(quiet) > anti_shipping_score(busy)
    assert anti_shipping_score(quiet) == 1.0


def test_measure_ok_flag():
    start, end = (0.0, 0.0), (1.0, 0.0)
    coords = [[0.0, 0.0], [0.5, 0.0], [1.0, 0.0]]
    m = measure(coords, start, end, 12.3)
    assert m["ok"] is True
    assert m["n_points"] == 3
    assert m["geodesic_nm"] == geodesic_nm(start, end)
    assert m["length_ratio"] >= 1.0
