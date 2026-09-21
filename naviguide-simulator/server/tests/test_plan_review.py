"""Revue de plan par règles (lot K) : jambes, ZEE / ports d'entrée des perles, drapeaux honnêtes.

Lot L5 : commentaire U7 — faux LLM, aucun chiffre nouveau, cache par hash.
"""
import asyncio
from datetime import timedelta

import ici_engine
import ici_warm
import plan_review
import voyage_store
from ici_engine import thin_cache_key
from tests.test_voyage_journal import PUBLIC, T0, _freeze, _official, client  # noqa: F401
from voyage_clock import OFFICIAL_VOYAGE_ID

_LEGS = [{
    "from": "La Rochelle", "to": "Fort-de-France (Martinique)",
    "legNm": 3350, "daysAtSea": 14, "holdDays": 3,
    "ampCount": 1, "pearls": {"known": 10, "unknown": 4},
    "zees": [{"name": "French Exclusive Economic Zone", "gold": True, "poe": ["La Pallice"]}],
    "flags": [{"kind": "formalities", "names": ["Somewhere Exclusive Economic Zone"]}],
}]


def test_review_reads_calendar_and_pearls_without_inventing(client, monkeypatch):
    ici_engine.reset_caches()
    now = T0 + timedelta(days=10)
    _freeze(monkeypatch, now)
    client.put("/voyage/official", json=_official())
    voy = voyage_store.load_voyage(OFFICIAL_VOYAGE_ID)
    legs = plan_review.legs_from_clock(voy["clock"], "La Rochelle")
    assert len(legs) == 1
    leg = legs[0]
    assert leg["from"] == "La Rochelle" and leg["to"] == "Fort-de-France (Martinique)"
    assert leg["legNm"] == 3350 and leg["daysAtSea"] > 10
    # Warm half the pearls: French Gold EEZ with a port, then a zone without Gold nor port.
    pearls = ici_warm.sample_route_nm(voy["points"])
    fr = {"name": "French Exclusive Economic Zone", "mrgid": 5677, "gold": True}
    xx = {"name": "Somewhere Exclusive Economic Zone", "mrgid": 9999, "gold": False}
    for i, p in enumerate(pearls):
        if i >= len(pearls) // 2:
            break
        bag = {"zee": fr if i < 10 else xx, "poe": [{"name": "La Rochelle - La Pallice", "nm": 1.0}] if i < 10 else [], "amp": [], "sources": {"bi": "ok"}}
        ici_engine.thin_cache_put(thin_cache_key(p["lat"], p["lon"], 30.0), bag)
    out = plan_review.review_official(voy, now)
    leg = out["legs"][0]
    assert leg["pearls"]["known"] > 0 and leg["pearls"]["unknown"] > 0, "unknown pearls are counted, not guessed"
    names = {z["name"] for z in leg["zees"]}
    assert names == {"French Exclusive Economic Zone", "Somewhere Exclusive Economic Zone"}
    fr_z = next(z for z in leg["zees"] if z["mrgid"] == 5677)
    assert fr_z["gold"] is True and fr_z["poe"] == ["La Rochelle - La Pallice"]
    kinds = [f["kind"] for f in leg["flags"]]
    assert "formalities" in kinds, kinds
    assert next(f for f in leg["flags"] if f["kind"] == "formalities")["names"] == ["Somewhere Exclusive Economic Zone"]
    assert "no-rest" not in kinds, "3 days alongside at Fort-de-France"
    body = client.get("/voyage/official/plan-review", headers=PUBLIC).json()
    assert body["legs"][0]["to"] == "Fort-de-France (Martinique)"
    assert body["pearlsUnknown"] == leg["pearls"]["unknown"]


def test_season_reads_the_atlas_cache_and_never_counts_zone_fallback(monkeypatch):
    import climatology_atlas as atlas
    clock = {"t0": "2026-05-15T08:00:00Z", "vertices": [
        {"tHours": 0, "sailNm": 0, "lat": 46.15, "lon": -1.16}, {"tHours": 50, "sailNm": 400, "lat": 44.0, "lon": -6.0},
        {"tHours": 100, "sailNm": 800, "lat": 40.0, "lon": -10.0},
    ]}
    leg = {"fromNm": 0, "toNm": 800, "month": 6}
    calls = []

    def fake(lat, lon, month, client=None):
        calls.append((lat, lon, month))
        if lat > 45:
            return {"source": "zone_fallback", "kind": "climatology"}
        return {"source": "atlas", "kind": "climatology", "point": {"rose": {"gale_pct": 17.5}, "cyclone": {"nearby": 2}}}

    monkeypatch.setattr(atlas, "atlas_wind_at", fake)
    s = plan_review.season_for_leg(clock, leg)
    assert s["cells"] == 2 and s["missing"] == 1, s
    assert s["galePct"] == 17.5 and s["cyclones"] == 2 and s["source"] == "atlas"
    assert all(m == 6 for _la, _lo, m in calls)
    # Out of budget: nothing read, nothing invented.
    import time
    late = plan_review.season_for_leg(clock, leg, budget_deadline=time.monotonic() - 1)
    assert late["cells"] == 0 and late["galePct"] is None


def test_comment_plan_write_tier_filter_and_cache(monkeypatch):
    calls = []

    async def fake_cascade(system, user, client=None, **kw):
        calls.append(kw)
        return (
            "Je changerais le repos à Fort-de-France (3 jours). "
            "La jambe fait 3350 nm. J'ajouterais 99 kn de vent.",
            "nemotron-super",
        )

    first = asyncio.run(plan_review.comment_plan(_LEGS, cascade=fake_cascade))
    assert first["source"] == "nemotron-super"
    assert first["cached"] is False
    assert "3350" in first["text"] and "3" in first["text"]
    assert "99" not in first["text"], "aucun chiffre inventé par le LLM"
    assert first["text"].count(".") <= 4

    again = asyncio.run(plan_review.comment_plan(_LEGS, cascade=fake_cascade))
    assert again["cached"] is True
    assert again["text"] == first["text"]
    assert len(calls) == 1, "cache par hash du tableau"

    other = [{**_LEGS[0], "legNm": 2000}]
    third = asyncio.run(plan_review.comment_plan(other, cascade=fake_cascade))
    assert third["cached"] is False
    assert len(calls) == 2


def test_comment_fallback_uses_only_table_numbers():
    facts = plan_review.table_facts(_LEGS)
    text = plan_review.comment_fallback(facts)
    assert "3350" in text and "14" in text
    assert "99" not in text
    assert len([s for s in text.split(".") if s.strip()]) <= 4


def test_plan_review_http_exposes_comment_source(client, monkeypatch):
    async def fake_comment(legs, **kw):
        return {"text": "Je changerais le repos (3 jours).", "source": "rules", "cached": False}

    monkeypatch.setattr(plan_review, "comment_plan", fake_comment)
    now = T0 + timedelta(days=10)
    _freeze(monkeypatch, now)
    client.put("/voyage/official", json=_official())
    body = client.get("/voyage/official/plan-review", headers=PUBLIC).json()
    assert "comment" in body
    assert body["comment"]["source"] == "rules"
    assert "99" not in (body["comment"].get("text") or "")
