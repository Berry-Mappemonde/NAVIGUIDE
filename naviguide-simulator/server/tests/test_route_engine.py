from copy import deepcopy

import pytest
from geographiclib.geodesic import Geodesic

from route_engine import (
    _LAND_MASK_AVAILABLE,
    _NE_TREE,
    _has_nearby_ocean,
    _is_land_hires,
    searoute_with_exact_end,
    unwrap_path,
    wrap_lon,
)
from shipping_lanes import attach_anti_shipping

BRISBANE = (153.4, -27.0)
SAN_FRANCISCO = (-122.4, 37.7)
SAN_FRANCISCO_UNFOLDED = (236.84, 37.7)


def test_wrap_lon_unfolded_san_francisco():
    assert abs(wrap_lon(236.84) + 123.16) < 1e-2
    assert -180.0 <= wrap_lon(236.84) <= 180.0
    assert wrap_lon(-122.4) == pytest.approx(-122.4)
    assert wrap_lon(wrap_lon(513.4)) == pytest.approx(153.4)


def test_unwrap_path_continuous_pacific():
    coords = [[153.4, -27.0], [179.0, 0.0], [-179.0, 10.0], [-122.4, 37.7]]
    out = unwrap_path(coords, 153.4)
    lons = [c[0] for c in out]
    for a, b in zip(lons, lons[1:]):
        assert abs(b - a) <= 180
    assert lons[-1] > 180
    assert all(c[1] <= 50 for c in out)


def test_short_offshore_leg():
    # La Rochelle → ~20 nm au large (ouest)
    route = searoute_with_exact_end((-1.167, 46.1541), (-1.7, 46.25))
    assert route is not None
    coords = route["geometry"]["coordinates"]
    assert len(coords) >= 2


def _path_nm(coords):
    geod = Geodesic.WGS84
    total = 0.0
    for a, b in zip(coords, coords[1:]):
        total += geod.Inverse(a[1], a[0], b[1], b[0])["s12"] / 1852.0
    return total


def _assert_transpac(coords):
    assert coords and len(coords) >= 2
    for lon, lat in coords:
        assert lat <= 50.0, f"sommet au nord de 50°N : {lat},{lon}"
        wlon = wrap_lon(lon)
        if (_LAND_MASK_AVAILABLE or _NE_TREE is not None) and _is_land_hires(lat, wlon):
            assert _has_nearby_ocean(lat, wlon, radius_deg=2.5), (
                f"sommet inland : {lat},{wlon}"
            )
    assert _path_nm(coords) < 7500


def test_brisbane_san_francisco_pacific():
    route = searoute_with_exact_end(BRISBANE, SAN_FRANCISCO)
    assert route is not None
    _assert_transpac(route["geometry"]["coordinates"])


def test_brisbane_san_francisco_unfolded_lon():
    route = searoute_with_exact_end(BRISBANE, SAN_FRANCISCO_UNFOLDED)
    assert route is not None
    coords = unwrap_path(route["geometry"]["coordinates"], BRISBANE[0])
    _assert_transpac(coords)
    lons = [c[0] for c in coords]
    for a, b in zip(lons, lons[1:]):
        assert abs(b - a) <= 180


def test_berry_corridors_named_geometry_unchanged():
    samples = [
        ([[-5.5, 36.0], [-5.8, 36.1], [-6.2, 36.0]], "Gibraltar"),
        ([[48.0, 13.0], [50.0, 13.2], [54.0, 13.5]], "Gulf of Aden"),
        ([[101.0, 3.0], [102.0, 4.0], [108.0, 3.5]], "Malacca"),
    ]
    for coords, name in samples:
        route = {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": deepcopy(coords)},
            "properties": {},
        }
        before = deepcopy(route["geometry"]["coordinates"])
        attach_anti_shipping(route)
        assert route["geometry"]["coordinates"] == before
        pack = route["properties"]["antiShipping"]
        assert pack["score"] < 1, name
        assert name in pack["lanes"], pack["lanes"]


def test_searoute_gibraltar_exposes_antishipping_without_moving_the_line():
    route = searoute_with_exact_end((-5.8, 36.05), (-5.2, 35.95))
    assert route is not None
    coords = route["geometry"]["coordinates"]
    before = deepcopy(coords)
    attach_anti_shipping(route)
    assert route["geometry"]["coordinates"] == before
    pack = (route.get("properties") or {}).get("antiShipping") or {}
    assert pack.get("score") is not None and pack["score"] < 1
    assert "Gibraltar" in (pack.get("lanes") or [])
