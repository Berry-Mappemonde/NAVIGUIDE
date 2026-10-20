from copy import deepcopy

import pytest
from geographiclib.geodesic import Geodesic

import route_engine
from route_engine import (
    _LAND_MASK_AVAILABLE,
    _NE_TREE,
    _has_nearby_ocean,
    _is_land_hires,
    _segment_enters,
    avoid_zones,
    route_open_hits,
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


def test_avoid_zones_leaves_a_forbidden_box():
    def inside(lat, lon):
        return 45.0 < lat < 45.2 and -8.0 < lon < -7.5

    straight = [[-8.5, 45.1], [-7.0, 45.1]]
    assert _segment_enters(straight[0][0], straight[0][1], straight[1][0], straight[1][1], inside)
    out = avoid_zones(straight, inside)
    assert len(out) >= 3
    for a, b in zip(out, out[1:]):
        assert not _segment_enters(a[0], a[1], b[0], b[1], inside)


def test_avoid_zones_pulls_a_vertex_out_of_the_box():
    def inside(lat, lon):
        return 45.0 < lat < 45.2 and -8.0 < lon < -7.5

    # Le sommet du milieu est dans l'aire. Le sortir, puis contourner.
    line = [[-8.6, 45.1], [-7.75, 45.1], [-6.9, 45.1]]
    assert inside(line[1][1], line[1][0])
    out = avoid_zones(line, inside)
    assert out[0] == line[0]
    assert out[-1] == line[-1]
    for lon, lat in out[1:-1]:
        assert not inside(lat, lon)
    for a, b in zip(out, out[1:]):
        assert not _segment_enters(a[0], a[1], b[0], b[1], inside)


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


def _straight_searoute(start, end, timeout_s=None):
    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [[start[0], start[1]], [end[0], end[1]]],
        },
        "properties": {},
    }


def _drop_route_cache(start, end):
    route_engine._route_cache.pop(route_engine._route_cache_key(start, end), None)


def test_route_open_hits_counts_area_and_land():
    def inside(lat, lon):
        return 45.0 < lat < 45.2 and -8.0 < lon < -7.5

    # Atlantique, sous le palier de densification : le segment coupe la boîte.
    box = [[-8.2, 45.1], [-7.4, 45.1]]
    assert _segment_enters(box[0][0], box[0][1], box[1][0], box[1][1], inside)
    hits = route_open_hits(box, inside)
    assert len(hits) == 1
    assert hits[0]["area"] is True
    assert hits[0]["land"] is False

    # Péninsule ibérique : terre, pas d'aire.
    iberia = [[-9.0, 40.0], [-1.0, 40.0]]
    land_hits = route_open_hits(iberia, None)
    assert land_hits
    assert all(hit["land"] for hit in land_hits)
    assert not any(hit["area"] for hit in land_hits)


def test_constraint_open_when_detour_cannot_leave_the_box(monkeypatch):
    """Détour impossible : _detour_clear rend [b], le segment reste dans la boîte."""
    def inside(lat, lon):
        return 45.0 < lat < 45.2 and -8.0 < lon < -7.5

    monkeypatch.setattr("amp_nogo.load_forbidden_nogo", lambda *a, **k: [{"id": "box"}])

    def fake_fn(items, *, escape_points=None):
        return inside

    monkeypatch.setattr("amp_nogo.amp_nogo_fn", fake_fn)
    monkeypatch.setattr(route_engine, "_detour_clear", lambda a, b, _inside: [b])
    monkeypatch.setattr(route_engine, "_invoke_searoute", _straight_searoute)

    seen = []
    real_avoid = route_engine.avoid_zones

    def spy(coords, inside_fn=None, max_iterations=4):
        seen.append(inside_fn)
        return real_avoid(coords, inside_fn, max_iterations)

    monkeypatch.setattr(route_engine, "avoid_zones", spy)

    start, end = (-8.2, 45.1), (-7.4, 45.1)
    _drop_route_cache(start, end)
    route = searoute_with_exact_end(start, end)

    assert route is not None
    assert seen and all(fn is inside for fn in seen)
    coords = route["geometry"]["coordinates"]
    assert len(coords) >= 2
    hits = route_open_hits(coords, inside)
    assert len([hit for hit in hits if hit["area"]]) >= 1
    assert route["properties"]["constraintStatus"] == "open"
    assert "ampStatus" not in route["properties"]


@pytest.mark.parametrize("loader", ["empty", "down"])
def test_missing_catalog_marks_amp_unavailable_and_keeps_the_land_line(monkeypatch, loader):
    if loader == "empty":
        monkeypatch.setattr("amp_nogo.load_forbidden_nogo", lambda *a, **k: [])
        start, end = (-40.0, 30.0), (-39.3, 30.0)
    else:
        def boom(*_a, **_k):
            raise RuntimeError("catalogue en panne")

        monkeypatch.setattr("amp_nogo.load_forbidden_nogo", boom)
        start, end = (-40.0, 10.0), (-39.3, 10.0)

    monkeypatch.setattr(route_engine, "_invoke_searoute", _straight_searoute)
    land_calls = {"n": 0}
    real_land = route_engine.avoid_land

    def spy_land(coords, max_iterations=8, deadline=None):
        land_calls["n"] += 1
        return real_land(coords, max_iterations=max_iterations, deadline=deadline)

    monkeypatch.setattr(route_engine, "avoid_land", spy_land)
    _drop_route_cache(start, end)
    route = searoute_with_exact_end(start, end)

    assert route is not None
    coords = route["geometry"]["coordinates"]
    assert len(coords) >= 2
    assert coords[0][0] == pytest.approx(start[0])
    assert coords[-1][0] == pytest.approx(end[0])
    assert land_calls["n"] >= 1
    assert route["properties"]["ampStatus"] == "unavailable"
    assert "constraintStatus" not in route["properties"]
