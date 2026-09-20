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
