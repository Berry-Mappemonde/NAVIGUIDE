from climatology_atlas import climatology_block, reset_atlas_cache, wind_from_point
from climatology_zones import zone_wind_at


def test_wind_from_point_keeps_kind_and_doi():
    payload = {
        "kind": "climatology",
        "period": "1980-2020",
        "doi": {"wind": "10.48670/moi-00183"},
        "wind_atlas": {"most_likely": {"speed_knots": 16.2, "dir_deg": 55}},
        "wave": {"hs_p50_m": 1.4, "hs_p90_m": 2.8},
        "current": {"speed_knots": 0.4, "direction_to_deg": 270},
        "cyclone": {"nearby": 1, "crossings_if_leg": {"count": 2}},
    }
    w = wind_from_point(payload)
    assert w["kind"] == "climatology"
    assert w["source"] == "atlas"
    assert w["speedKnots"] == 16.2
    assert w["hsP90"] == 2.8
    assert w["currentKn"] == 0.4
    assert w["doi"]["wind"] == "10.48670/moi-00183"
    assert wind_from_point({"kind": "forecast"}) is None
    assert wind_from_point({"kind": "climatology"}) is None


def test_climatology_block_zone_if_api_dead(monkeypatch):
    reset_atlas_cache()

    def boom(*_a, **_k):
        return None

    monkeypatch.setattr("climatology_atlas.fetch_atlas_point", boom)
    monkeypatch.setattr("climatology_atlas.fetch_atlas_crossings", boom)
    block = climatology_block(15.0, -25.0, 6)
    assert block["kind"] == "climatology"
    assert block["source"] == "zone_fallback"
    zone = zone_wind_at(15.0, -25.0, 6)
    assert block["wind"]["speedKnots"] == zone["speedKnots"]
    assert block["point"] is None


def test_climatology_block_atlas_when_point_answers(monkeypatch):
    reset_atlas_cache()
    payload = {
        "kind": "climatology",
        "month": 6,
        "period": "1980-2020",
        "doi": {"wind": "10.48670/moi-00183"},
        "wind_atlas": {"most_likely": {"speed_knots": 16.2, "dir_deg": 55}},
        "wave": {"hs_p50_m": 1.4, "hs_p90_m": 2.8},
        "current": {"speed_knots": 0.4},
        "cyclone": {"nearby": 0},
    }

    monkeypatch.setattr("climatology_atlas.fetch_atlas_point", lambda *a, **k: payload)
    monkeypatch.setattr(
        "climatology_atlas.fetch_atlas_crossings",
        lambda *a, **k: {"count": 2, "kind": "climatology"},
    )
    block = climatology_block(15.0, -25.0, 6, dest_lat=14.6, dest_lon=-61.0)
    assert block["source"] == "atlas"
    assert block["point"]["wind_atlas"]["most_likely"]["speed_knots"] == 16.2
    assert block["crossings"]["count"] == 2
    assert block["point"]["wave"]["hs_p90_m"] == 2.8
    assert block["kind"] == "climatology"
