"""Lot R10b — advise : décalage de date, cascade, score, déterminisme, route."""
from __future__ import annotations

import copy
import json
import time
from datetime import date, datetime, timedelta, timezone

from story_cascade import _numbers, filter_numbers

from moment import load_official_mini
from plan_advisor import (
    SHIFT_DAYS,
    WEIGHT_EXTRA_NM,
    WEIGHT_SHIFT_PER_DAY,
    advise,
    clear_advice_jobs,
    request_advice,
    score_of,
    shift_plan,
)
from plan_alerts import clear_plan_cache, evaluate_plan
from voyage_clock import OFFICIAL_VOYAGE_ID

NOW = "2026-09-22T12:00:00Z"
TH = {"galeKt": 34, "hsAlertM": 3.0}

NOUMEA_POINTS = [
    {"lat": -22.27, "lon": 166.45},
    {"lat": -21.9, "lon": 165.4},
    {"lat": -21.6, "lon": 164.4},
]
DZAOUDZI_POINTS = [
    {"lat": -12.78, "lon": 45.26},
    {"lat": -13.0, "lon": 44.8},
    {"lat": -13.2, "lon": 44.4},
]
CAPE_POINTS = [
    {"lat": -33.92, "lon": 18.42},
    {"lat": -34.1, "lon": 18.0},
]
BISCAY_POINTS = [
    {"lat": 46.15, "lon": -1.16},
    {"lat": 45.8, "lon": -2.0},
]


def setup_function():
    clear_plan_cache()
    clear_advice_jobs()


def _leg(idx, frm, to, depart, arrive, hold, points):
    return {
        "idx": idx, "from": frm, "to": to,
        "depart": depart, "arrive": arrive,
        "departIso": f"{depart}T08:00:00Z",
        "arriveIso": f"{arrive}T08:00:00Z",
        "holdDays": hold, "kn": 8.0,
        "points": copy.deepcopy(points),
    }


def _noumea_chain():
    """Nouméa 1er oct. → Dzaoudzi (+5 j à quai) → Le Cap (+3 j)."""
    return {
        "legs": [
            _leg(0, "Nouméa", "Dzaoudzi", "2026-10-01", "2026-10-02", 5, NOUMEA_POINTS),
            _leg(1, "Dzaoudzi", "Le Cap", "2026-10-07", "2026-10-09", 3, DZAOUDZI_POINTS),
            _leg(2, "Le Cap", "Sainte-Hélène", "2026-10-12", "2026-10-13", 2, CAPE_POINTS),
        ],
        "skipper_thresholds": TH,
    }


def _official_with_leg3():
    """Deux jambes figées + une courte + Nouméa en idx 3, puis une suivante."""
    return {
        "voyageId": OFFICIAL_VOYAGE_ID,
        "t0": "2026-05-15T08:00:00Z",
        "official": True,
        "skipper_thresholds": TH,
        "legs": [
            _leg(0, "La Rochelle", "Fort-de-France (Martinique)", "2026-05-15", "2026-06-02", 3, BISCAY_POINTS),
            _leg(1, "Fort-de-France (Martinique)", "Pointe-à-Pitre (Guadeloupe)", "2026-06-05", "2026-06-07", 2, BISCAY_POINTS),
            _leg(2, "Pointe-à-Pitre (Guadeloupe)", "Portsmouth", "2026-06-09", "2026-06-11", 2, BISCAY_POINTS),
            _leg(3, "Nouméa", "Dzaoudzi", "2026-10-01", "2026-10-02", 5, NOUMEA_POINTS),
            _leg(4, "Dzaoudzi", "Le Cap", "2026-10-07", "2026-10-09", 3, DZAOUDZI_POINTS),
        ],
    }


def _hold_gap(plan, i):
    a = datetime.fromisoformat(plan["legs"][i]["arrive"]).replace(tzinfo=timezone.utc)
    b = datetime.fromisoformat(plan["legs"][i + 1]["depart"]).replace(tzinfo=timezone.utc)
    return (b.date() - a.date()).days


def test_weights_are_fixed_constants():
    assert SHIFT_DAYS == (-21, -14, -7, 0, 7, 14, 21)
    assert WEIGHT_SHIFT_PER_DAY == 0.3
    assert WEIGHT_EXTRA_NM == 0.02
    assert score_of(10, 7, 41) == 10 + 0.3 * 7 + 0.02 * 41


def test_best_score_is_at_most_current_plan():
    plan = _noumea_chain()
    out = advise(plan, 0, now=NOW)
    current = score_of(evaluate_plan(plan, now=NOW)["total"], 0, 0)
    assert out["best"]["score"] <= current
    assert out["weights"] == {"shiftPerDay": 0.3, "extraNm": 0.02}
    assert out["best"]["shiftDays"] in SHIFT_DAYS
    assert len(out["alternatives"]) <= 3
    assert all(a["score"] >= out["best"]["score"] for a in out["alternatives"])


def test_cascade_shifts_every_following_stop_by_the_same_days():
    plan = _noumea_chain()
    days = 7
    shifted = shift_plan(plan, 0, days)
    out = advise(plan, 0, now=NOW)
    # On vérifie la mécanique sur un décalage connu, pas seulement le meilleur.
    for i, (was, now) in enumerate(zip(plan["legs"], shifted["legs"])):
        assert now["holdDays"] == was["holdDays"]
        was_arr = date.fromisoformat(was["arrive"])
        now_arr = date.fromisoformat(now["arrive"])
        was_dep = date.fromisoformat(was["depart"])
        now_dep = date.fromisoformat(now["depart"])
        assert (now_arr - was_arr).days == days
        assert (now_dep - was_dep).days == days
    cascade = out["best"]["cascade"]
    assert [c["stop"] for c in cascade] == ["Dzaoudzi", "Le Cap", "Sainte-Hélène"]
    shift = out["best"]["shiftDays"]
    for row, was in zip(cascade, plan["legs"]):
        assert date.fromisoformat(row["now"]) - date.fromisoformat(row["was"]) == timedelta(days=shift)


def test_days_at_dock_are_preserved():
    plan = _noumea_chain()
    assert _hold_gap(plan, 0) == 5
    assert _hold_gap(plan, 1) == 3
    for days in SHIFT_DAYS:
        shifted = shift_plan(plan, 0, days)
        assert [lg["holdDays"] for lg in shifted["legs"]] == [5, 3, 2]
        assert _hold_gap(shifted, 0) == 5
        assert _hold_gap(shifted, 1) == 3
    later = shift_plan(plan, 1, -14)
    assert later["legs"][0]["depart"] == "2026-10-01"
    assert later["legs"][0]["holdDays"] == 5
    assert _hold_gap(later, 0) == 5 - 14
    assert later["legs"][1]["holdDays"] == 3
    assert later["legs"][2]["holdDays"] == 2
    assert _hold_gap(later, 1) == 3


def test_two_calls_return_the_same_payload():
    plan = _noumea_chain()
    a = advise(plan, 0, now=NOW)
    b = advise(plan, 0, now=NOW)
    assert a == b
    assert a["best"]["sentence"] == b["best"]["sentence"]
    assert a["best"]["cascade"] == b["best"]["cascade"]


def test_sentence_numbers_all_live_in_facts():
    plan = _noumea_chain()
    out = advise(plan, 0, now=NOW)
    for cand in [out["best"], *out["alternatives"]]:
        blob = json.dumps(cand["facts"], ensure_ascii=False)
        nums = _numbers(cand["sentence"])
        assert nums, cand["sentence"]
        assert nums.issubset(_numbers(blob)), (nums - _numbers(blob), cand["sentence"])
        cleaned, dropped = filter_numbers(cand["sentence"], cand["facts"])
        assert dropped == 0
        assert cleaned
        assert "Nouméa" in cand["sentence"]
        assert str(abs(cand["shiftDays"])) in cand["sentence"] or cand["shiftDays"] == 0
        assert str(cand["alertsBefore"]) in cand["sentence"] or str(cand["alertsAfter"]) in cand["sentence"]


def test_sentence_names_leg_shift_alerts_and_cascade():
    plan = _noumea_chain()
    out = advise(plan, 0, now=NOW)
    text = out["best"]["sentence"]
    assert "Nouméa" in text
    assert "alertes" in text
    if out["best"]["shiftDays"] > 0:
        assert "reculent" in text
    elif out["best"]["shiftDays"] < 0:
        assert "avancent" in text
    else:
        assert "aucun décalage" in text
    assert "escales suivantes" in text


def test_frozen_leg_only_keeps_zero_shift():
    voy = load_official_mini()
    out = advise(voy, 0, now=NOW)
    assert out["best"]["shiftDays"] == 0
    assert out["alternatives"] == []


def test_request_advice_pending_then_done():
    plan = _noumea_chain()
    first = request_advice(plan, 0, now=NOW)
    assert first["status"] == "pending"
    assert first["weights"]["shiftPerDay"] == 0.3
    body = first
    for _ in range(80):
        body = request_advice(plan, 0, now=NOW)
        if body.get("status") == "done":
            break
        time.sleep(0.05)
    assert body["status"] == "done"
    assert body["best"]["score"] <= score_of(evaluate_plan(plan, now=NOW)["total"], 0, 0)
    again = request_advice(plan, 0, now=NOW)
    assert again == body


def test_rewrite_drops_llm_figures_absent_from_facts(monkeypatch):
    import voyage_api

    plan = _noumea_chain()
    payload = advise(plan, 0, now=NOW)
    gabarit = payload["best"]["sentence"]

    async def fake_cascade(system, user, client, **kwargs):
        return "Partir dans 99 jours avec 42 alertes.", "nemotron-lightning"

    monkeypatch.setattr("story_cascade.cascade_text", fake_cascade)
    out = voyage_api._rewrite_plan_advice(copy.deepcopy(payload))
    assert "99" not in out["best"]["sentence"]
    assert "42" not in out["best"]["sentence"]
    assert out["best"]["sentence"] == gabarit
    nums = _numbers(out["best"]["sentence"])
    assert nums.issubset(_numbers(json.dumps(out["best"]["facts"], ensure_ascii=False)))


def test_advice_route_pending_done_and_filter_numbers(monkeypatch):
    import voyage_api
    import voyage_store
    from fastapi.testclient import TestClient
    from main import app

    voyage_store.save_voyage(_official_with_leg3())
    monkeypatch.setattr(voyage_api, "_now", lambda: datetime(2026, 9, 22, 12, tzinfo=timezone.utc))

    async def fake_cascade(system, user, client, **kwargs):
        return "Partir dans 99 jours avec 42 alertes.", "nemotron-lightning"

    monkeypatch.setattr("story_cascade.cascade_text", fake_cascade)
    client = TestClient(app)
    first = client.get("/voyage/official/advice?leg=3")
    assert first.status_code == 200
    assert first.json()["status"] in ("pending", "done")
    body = first.json()
    for _ in range(80):
        if body.get("status") == "done":
            break
        time.sleep(0.05)
        body = client.get("/voyage/official/advice?leg=3").json()
    assert body["status"] == "done"
    assert body["leg"] == 3
    assert body["best"]["cascade"]
    assert body["best"]["cascade"][0]["stop"] == "Dzaoudzi"
    assert body["weights"] == {"shiftPerDay": 0.3, "extraNm": 0.02}
    nums = _numbers(body["best"]["sentence"])
    assert nums.issubset(_numbers(json.dumps(body["best"]["facts"], ensure_ascii=False)))
    assert "99" not in body["best"]["sentence"]
    assert "42" not in body["best"]["sentence"]
    missing = client.get("/voyage/official/advice?leg=9")
    assert missing.status_code == 400
