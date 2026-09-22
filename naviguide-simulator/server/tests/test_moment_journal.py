"""Lot R9a — journal des moments : diff, remplissage idempotent, until."""
from __future__ import annotations

import copy

from fastapi.testclient import TestClient

from moment import build_moment, load_official_mini
from moment_journal import (
    SCORE_ALERT_OFF,
    SCORE_ALERT_ON,
    SCORE_AMP,
    SCORE_ESCALE,
    SCORE_REGIME,
    SCORE_STATION,
    SCORE_ZEE,
    diff_moments,
    read_moments,
    warm_moments,
)
from voyage_clock import OFFICIAL_VOYAGE_ID
from voyage_store import save_voyage


def _fixture_voyage(voyage_id=None):
    voy = load_official_mini()
    voy["voyageId"] = voyage_id or voy["voyageId"]
    save_voyage(voy)
    return voy


def _moment(voy, pearl_idx, extra_pearl=None, extra_clock=None, extra_leg=None):
    pearl = copy.deepcopy(voy["pearls"][pearl_idx])
    if extra_pearl:
        pearl.update(extra_pearl)
    sail = float(pearl.get("sailNm") or 0)
    clock = copy.deepcopy(min(
        voy["clock"]["vertices"],
        key=lambda v: abs(float(v.get("sailNm") or 0) - sail),
    ))
    if extra_clock:
        clock.update(extra_clock)
    leg = copy.deepcopy(voy["legs"][0 if sail <= 3350 else 1])
    if extra_leg:
        leg.update(extra_leg)
    return build_moment(pearl, clock, leg, voy["skipper_thresholds"], lang="fr")


def test_diff_moments_scores_match_plan():
    voy = load_official_mini()
    base = _moment(voy, 0)
    escale = _moment(voy, 0, extra_leg={"to": "Fort-de-France (Martinique)", "from": "La Rochelle"})
    # Même perle, destination changée.
    other_leg = copy.deepcopy(escale)
    other_leg["leg"] = {**escale["leg"], "to": "Pointe-à-Pitre (Guadeloupe)"}
    kinds = {c["kind"]: c for c in diff_moments(escale, other_leg)}
    assert kinds["escale"]["score"] == SCORE_ESCALE

    alert_on = copy.deepcopy(base)
    alert_on["alerts"] = list(base.get("alerts") or []) + [{
        "id": "wind-test", "kind": "wind", "title": "Coup de vent", "fact": "Vent 36 kn ≥ 34 kn.",
    }]
    kinds = {c["kind"]: c for c in diff_moments(base, alert_on)}
    assert kinds["alert-on"]["score"] == SCORE_ALERT_ON

    kinds = {c["kind"]: c for c in diff_moments(alert_on, base)}
    assert kinds["alert-off"]["score"] == SCORE_ALERT_OFF

    zee = copy.deepcopy(base)
    zee["here"] = copy.deepcopy(base["here"])
    zee["here"]["zee"] = {"name": "Spanish EEZ", "mrgid": 5693, "entry": {"known": False, "ports": []}}
    kinds = {c["kind"]: c for c in diff_moments(base, zee)}
    assert kinds["zee-enter"]["score"] == SCORE_ZEE

    station = copy.deepcopy(base)
    station["around"] = list(base.get("around") or []) + [{
        "kind": "science", "title": "Station croisée", "fact": "Station PIRATA (8 nm)",
    }]
    kinds = {c["kind"]: c for c in diff_moments(base, station)}
    assert kinds["station"]["score"] == SCORE_STATION

    regime = copy.deepcopy(base)
    regime["leg"] = {**base["leg"], "regime": "forecast"}
    kinds = {c["kind"]: c for c in diff_moments(base, regime)}
    assert kinds["regime"]["score"] == SCORE_REGIME

    amp = copy.deepcopy(base)
    amp["here"] = copy.deepcopy(base["here"])
    amp["here"]["mpa"] = list(base["here"].get("mpa") or []) + [{
        "name": "Grand Cul-de-Sac Marin", "nm": 4.0, "site_id": "fr-amp-gcsm",
    }]
    kinds = {c["kind"]: c for c in diff_moments(base, amp)}
    assert kinds["amp"]["score"] == SCORE_AMP

    assert diff_moments(None, base) == []
    assert diff_moments({}, base) == []


def test_fixture_pearls_collapse_to_fewer_moments():
    voy = _fixture_voyage()
    n = len(voy["pearls"])
    assert n == 12
    first = warm_moments(voy["voyageId"])
    rows = read_moments(voy["voyageId"])
    m = first["count"]
    assert m == len(rows)
    assert 1 <= m < n
    seqs = [row["seq"] for row in rows]
    assert seqs == list(range(m))
    assert rows[0]["changes"] == []
    for row in rows[1:]:
        assert row["changes"], f"seq {row['seq']} sans changes"
        for change in row["changes"]:
            assert change["kind"] and change["title"] and change["fact"]
            assert change["score"] in (1, 2, 3)
    replay = warm_moments(voy["voyageId"])
    again = read_moments(voy["voyageId"])
    assert replay["count"] == m == len(again)
    assert [row["signature"] for row in again] == [row["signature"] for row in rows]


def test_changed_signature_updates_the_line():
    voy = _fixture_voyage()
    warm_moments(voy["voyageId"])
    before = {row["seq"]: row["signature"] for row in read_moments(voy["voyageId"])}
    voy["pearls"][0]["zee"] = {
        "name": "Spanish Exclusive Economic Zone",
        "mrgid": 5693,
        "gold": False,
    }
    voy["pearls"][0]["poe"] = []
    save_voyage(voy)
    warm_moments(voy["voyageId"])
    after = read_moments(voy["voyageId"])
    assert after[0]["signature"] != before[0]
    assert after[0]["moment"]["here"]["zee"]["mrgid"] == 5693
    assert [row["seq"] for row in after] == list(range(len(after)))


def test_read_moments_until_cuts():
    voy = _fixture_voyage()
    warm_moments(voy["voyageId"])
    all_rows = read_moments(voy["voyageId"])
    assert len(all_rows) >= 2
    cut = all_rows[len(all_rows) // 2]["t"]
    sliced = read_moments(voy["voyageId"], until=cut)
    assert 1 <= len(sliced) < len(all_rows)
    assert all(row["t"] <= cut or row["t"][:10] <= cut[:10] for row in sliced)
    assert sliced[-1]["seq"] < all_rows[-1]["seq"]
    day = all_rows[0]["t"][:10]
    by_day = read_moments(voy["voyageId"], until=day)
    assert by_day
    assert all(row["t"].startswith(day) or row["t"][:10] <= day for row in by_day)


def test_status_and_get_expose_moments():
    voy = _fixture_voyage(OFFICIAL_VOYAGE_ID)
    n = warm_moments(OFFICIAL_VOYAGE_ID)["count"]
    assert n >= 1
    import ici_warm
    st = ici_warm.status()
    assert st["moments"] == n
    assert st["store"]["moments"] == n

    from main import app
    client = TestClient(app)
    res = client.get("/voyage/official/moments")
    assert res.status_code == 200
    body = res.json()
    assert body["voyageId"] == OFFICIAL_VOYAGE_ID
    assert body["count"] == n
    assert len(body["moments"]) == n
    until = body["moments"][0]["t"]
    cut = client.get("/voyage/official/moments", params={"until": until})
    assert cut.status_code == 200
    assert 1 <= cut.json()["count"] <= n
    status = client.get("/ici/warm/status")
    assert status.status_code == 200
    assert status.json()["moments"] == n


def test_startup_does_not_block_on_moments(monkeypatch):
    calls = []
    monkeypatch.setenv("NAVIGUIDE_ICI_WARM", "0")
    import ici_warm
    monkeypatch.setattr("moment_journal.warm_moments", lambda *_a, **_k: calls.append(1) or {"count": 0})
    assert ici_warm.start_background() is False
    assert calls == []
    assert ici_warm.status()["status"] == "disabled"


def test_kick_official_moments_returns_without_waiting(monkeypatch):
    import voyage_api
    _fixture_voyage(OFFICIAL_VOYAGE_ID)
    started = []

    def fake_kick(*_a, **_k):
        started.append(True)
        return True

    monkeypatch.setattr(voyage_api.get_pipeline(), "kick", fake_kick)
    assert voyage_api._kick_official_moments() is True
    assert started == [True]
