from datetime import datetime, timezone

import pytest

from saildocs import (
    GRIB_MISSING,
    MAX_BBOX_LAT_SPAN,
    assert_corridor_not_globe,
    bbox_around,
    ingest_daily,
    saildocs_query,
    utc_day,
    wind_at_daily,
)


def test_bbox_is_corridor_not_globe():
    box = bbox_around(46.15, -1.16, 200)
    south, north, west, east = box
    assert north - south < MAX_BBOX_LAT_SPAN
    assert abs(east - west) < 20
    assert_corridor_not_globe(box)
    with pytest.raises(ValueError, match="globe"):
        assert_corridor_not_globe((-80, 80, -180, 180))


def test_saildocs_query_around_boat():
    q = saildocs_query(46.15, -1.16)
    assert q.startswith("GFS:")
    assert "WIND" in q
    assert "180W" not in q
    assert "90N" not in q


def test_ingest_and_sample(tmp_path, monkeypatch):
    monkeypatch.setattr("saildocs.GRIB_DIR", tmp_path)
    when = datetime(2026, 9, 15, 8, tzinfo=timezone.utc)
    rec = ingest_daily(
        "berry-mappemonde-2026-officiel",
        {
            "model": "GFS",
            "day": utc_day(when),
            "around": {"lat": 46.15, "lon": -1.16},
            "samples": [{
                "lat": 46.15,
                "lon": -1.16,
                "t": "2026-09-15T08:00:00Z",
                "windKnots": 14,
                "dirFromDeg": 270,
            }],
        },
    )
    assert rec["status"] == "ready"
    assert rec["model"] == "GFS"
    wind = wind_at_daily(rec, 46.15, -1.16, when)
    assert wind["windKnots"] == 14
    assert wind["model"] == "GFS"


def test_globe_ingest_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("saildocs.GRIB_DIR", tmp_path)
    with pytest.raises(ValueError, match="globe"):
        ingest_daily(
            "berry-mappemonde-2026-officiel",
            {"bbox": [-80, 80, -180, 180], "model": "GFS", "samples": []},
        )


def test_missing_label():
    assert GRIB_MISSING == "prévision du jour absente"
