from datetime import datetime, timezone

from climatology_zones import zone_wind_at
from isochrone import is_path_clear, run_leg_isochrone


def _const_wind(speed=16.0, direc=90.0):
    def fn(lat, lon, t):
        return {
            "speedKnots": speed,
            "dirFromDeg": direc,
            "kind": "forecast",
            "hs": 1.0,
            "model": "synthetic-test",
        }
    return fn


def test_iberia_land_crossing_blocked():
    # Ouest Portugal → intérieur péninsule
    assert is_path_clear(38.0, -10.5, 38.0, -10.0)
    assert not is_path_clear(38.0, -10.5, 38.0, -6.0)


def test_short_leg_arrives_or_splices():
    t0 = datetime(2026, 6, 15, 8, tzinfo=timezone.utc)
    searoute = [(46.15, -1.16), (46.10, -2.0), (46.00, -3.2)]
    out = run_leg_isochrone(
        46.15, -1.16, 46.00, -3.2, t0,
        wind_fn=_const_wind(),
        polar_raw=None,
        time_step_h=6,
        heading_step_deg=10,
        max_steps=20,
        arrival_radius_nm=50,
        searoute_coords=searoute,
    )
    assert out["status"] in ("arrived", "spliced")
    coords = out["draft_geojson"]["geometry"]["coordinates"]
    assert len(coords) >= 2
    assert "forecast" in out["kind_mix"] or "climatology" in out["kind_mix"]


def test_wave_nogo_discards_step():
    def wind(lat, lon, t):
        return {"speedKnots": 16, "dirFromDeg": 90, "kind": "forecast", "hs": 4.0}

    def nogo(lat, lon, t):
        return True

    out = run_leg_isochrone(
        46.15, -1.16, 46.00, -3.2,
        datetime(2026, 6, 15, 8, tzinfo=timezone.utc),
        wind_fn=wind,
        wave_nogo_fn=nogo,
        max_steps=8,
        searoute_coords=[(46.15, -1.16), (46.00, -3.2)],
    )
    assert out["status"] in ("failed", "spliced")


def test_zone_june_not_used_as_forecast_label():
    z = zone_wind_at(46.15, -1.16, 6)
    assert z["kind"] == "climatology"
