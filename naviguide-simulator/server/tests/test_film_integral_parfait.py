"""Film intégral au « now » réel (29/10/2026) : deux défauts vérifiables du brut.

1. « à l'équateur » dit à 4,95° N (Dégrad des Cannes, Cayenne) et à 5,0° N
   (Pacifique, après Panama) : le bateau n'a pas coupé l'équateur.
2. « Le 27 octobre, le bateau longe Mata-Utu. […] Arrivée à Mata-Utu » et
   « le bateau longe Dégrad des Cannes […] amarré à la marina de Dégrad des
   Cannes » : on ne longe pas le port où l'on arrive.
"""
import asyncio
import re
from datetime import datetime, timezone

from climo_events import EQUATOR_BAND_DEG, _place_phrase
from film_script import build_raw_from_moments
from tests.test_film_script import CLOCK, JOURNAL, LIVE, MOMENTS, _rg6_review
import film_script as fs
from film_script import _coast_is_arrival, spoken_sea_days


def test_equator_only_near_the_line():
    assert EQUATOR_BAND_DEG <= 2.0
    assert _place_phrase(0.4, -50.0, "fr") == "près de l'équateur"
    assert _place_phrase(0.4, -50.0, "fr", prev_lat=-1.0) == "à l'équateur"
    assert _place_phrase(-1.9, -30.0, "en") == "near the equator"
    for lat, lon in ((4.95, -52.35), (5.0, -86.33), (-4.9, -100.0), (3.0, -40.0)):
        assert "équateur" not in _place_phrase(lat, lon, "fr"), (lat, lon)
        assert "equator" not in _place_phrase(lat, lon, "en"), (lat, lon)


def _coast(name):
    return {"kind": "coast", "title": name, "fact": name, "ports": [name]}


def test_coast_naming_destination_is_dropped():
    assert _coast_is_arrival(_coast("Mata-Utu"), "Mata-Utu (Wallis-et-Futuna)", [], None, "fr")
    assert _coast_is_arrival(_coast("Mata-Utu"), "Mata-Utu", [], None, "en")


def test_coast_naming_arrival_marina_is_dropped():
    marina = {"kind": "marina", "title": "Dégrad des Cannes", "fact": "Dégrad des Cannes",
              "lat": 4.85, "lon": -52.27}
    dest = {"name": "Cayenne (Guyane)", "lat": 4.93, "lon": -52.33}
    assert _coast_is_arrival(_coast("Dégrad des Cannes"), "Cayenne (Guyane)", [marina], dest, "fr")


def test_other_coasts_are_kept():
    assert not _coast_is_arrival(_coast("Pago Pago"), "Mata-Utu (Wallis-et-Futuna)", [], None, "fr")
    assert not _coast_is_arrival(_coast("Paramaribo"), "Cayenne (Guyane)", [], {"name": "Cayenne (Guyane)"}, "fr")
    assert not _coast_is_arrival(_coast("Saint-Denis"), "Saint-Gilles (La Réunion)", [], None, "fr")


def test_w11_pierre_is_not_saint_pierre_arrival_echo():
    """W11 : « Pierre » (côte) ≠ arrivée à Saint-Pierre (repli distance ≤ 12 nm)."""
    dest = {"name": "Saint-Pierre (Saint-Pierre-et-Miquelon)", "lat": 46.78, "lon": -56.18}
    assert not _coast_is_arrival(
        {"kind": "coast", "title": "Pierre", "fact": "Pierre", "lat": 46.5, "lon": -56.0},
        "Saint-Pierre (Saint-Pierre-et-Miquelon)", [], dest, "fr",
    )


def test_w11_spoken_sea_days_zero_is_empty():
    assert spoken_sea_days(0, "fr") == ""
    assert spoken_sea_days(0, "en") == ""


def test_w10_build_raw_oct29_no_longe_arrival_or_equator_outside_band():
    """W10 : brut regénéré au now 29/10/2026 (hors ligne, stock CLOCK/JOURNAL)."""
    now_ms = int(datetime(2026, 10, 29, 14, 30, tzinfo=timezone.utc).timestamp() * 1000)
    for lang in ("fr", "en"):
        plan = build_raw_from_moments(
            CLOCK, CLOCK["marks"], LIVE, {**JOURNAL, **MOMENTS},
            lang=lang, seconds=0, now_ms=now_ms, review=_rg6_review(),
        )
        blob = "\n".join(str(ch.get("text") or "") for ch in plan.get("chapters") or [])
        assert blob.strip(), lang
        assert not re.search(r"longe\s+Mata[- ]Utu", blob, re.I), blob[:400]
        assert not re.search(r"longe\s+D[ée]grad", blob, re.I), blob[:400]
        if lang == "fr":
            assert not re.search(r"longe\s+Pierre\b", blob, re.I), blob[:400]
        else:
            assert not re.search(r"along\s+Pierre\b", blob, re.I), blob[:400]


def test_short_hop_is_not_a_day_at_sea():
    # Gustavia → Marigot : 41 milles à 8 nœuds = 0,2 jour.
    assert spoken_sea_days(0.2, "fr") == "moins d'un jour de mer"
    assert spoken_sea_days(0.2, "en") == "less than a day at sea"
    assert spoken_sea_days(0.9, "fr") == "un jour de mer"
    assert spoken_sea_days(1.0, "en") == "one day at sea"


def test_reread_knows_halifax_from_chapters_when_voyage_marks_lack_it(monkeypatch):
    """Le voyage officiel n'a Halifax ni dans marks ni dans clock.marks : la relecture
    simulée ne doit pas rejeter le film pour « absent » sur l'arrivée à Halifax."""
    import voyage_store

    marks = [{"name": n} for n in (
        "Saint-Maur (Berry, Indre)", "La Rochelle", "Ajaccio (Corse)",
        "Fort-de-France (Martinique)", "Pointe-à-Pitre (Guadeloupe)",
        "Gustavia (Saint-Barthélemy)", "Marigot (Saint-Martin)", "Cayenne (Guyane)",
        "Saint-Pierre (Saint-Pierre-et-Miquelon)", "Papeete (Polynésie française)",
    )]
    monkeypatch.setattr(voyage_store, "load_voyage", lambda _vid: {"marks": marks, "clock": {"marks": marks[2:]}})
    plan = {"chapters": [
        {"fromName": "Cayenne (Guyane)", "toName": "Halifax (Nouvelle-Écosse)"},
        {"fromName": "Halifax (Nouvelle-Écosse)", "toName": "Saint-Pierre (Saint-Pierre-et-Miquelon)"},
    ]}
    rows = fs._route_stops_for_reread(plan)
    names = [r.get("name") for r in rows]
    assert names.index("Halifax (Nouvelle-Écosse)") == names.index("Cayenne (Guyane)") + 1
    text = ("Le 23 août, à Saint-Pierre (Saint-Pierre-et-Miquelon), l'équipage reprend le second "
            "voilier pour Halifax (Nouvelle-Écosse). Arrivée à Halifax (Nouvelle-Écosse) le 28 août.")
    assert not fs._absent_places(text, rows)


def test_r2_arrival_harbor_failure_is_logged_not_silent(caplog, monkeypatch):
    import logging

    def _boom(*_a, **_k):
        raise ValueError("simulated harbor lookup failure")

    caplog.set_level(logging.WARNING)
    monkeypatch.setattr(fs, "_arrival_harbor", _boom)
    dest = {"name": "Mata-Utu", "lat": -13.2, "lon": -176.2}
    assert fs._coast_is_arrival(
        {"kind": "coast", "title": "Pago Pago", "fact": "Pago Pago"},
        "Mata-Utu (Wallis-et-Futuna)", [], dest, "fr",
    ) is False
    assert any("_arrival_harbor failed" in r.message for r in caplog.records)


def test_r4_insert_missing_air_at_head_when_no_anchor():
    rows = [{"name": "La Rochelle"}, {"name": "Ajaccio (Corse)"}]
    clock = [{"name": "Halifax (Nouvelle-Écosse)", "filmNm": 8780.0}]
    out = fs._insert_missing_air(rows, clock)
    assert out[0]["name"] == "Halifax (Nouvelle-Écosse)"
    assert [r["name"] for r in out[1:]] == ["La Rochelle", "Ajaccio (Corse)"]


def test_write_film_chain_never_calls_translate_written_plan(monkeypatch):
    async def _trap(*_a, **_k):
        raise AssertionError("translate_written_plan must not run in production chain")

    monkeypatch.setattr(fs, "translate_written_plan", _trap)
    monkeypatch.setattr(fs, "film_ultra_open", lambda: False)

    async def _fake_write(_plan, *, lang, cascade, seconds):
        text = (_plan.get("chapters") or [{}])[0].get("text") or "x"
        ch = {"id": "a", "text": text, "source": fs.WRITTEN_SOURCE}
        return (
            {"chapters": [ch], "source": fs.WRITTEN_SOURCE, "targetSeconds": 150},
            {"rewritten": 1, "source": fs.WRITTEN_SOURCE},
        )

    async def _ok_reread(*_a, **_k):
        return True, {"source": "rules"}

    monkeypatch.setattr(fs, "write_stored_plan", _fake_write)
    monkeypatch.setattr(fs, "reread_before_store", _ok_reread)

    fr_raw = {"targetSeconds": 150, "chapters": [{"id": "a", "text": "Le 1er juin, départ vers Ajaccio."}]}
    en_raw = {"targetSeconds": 150, "chapters": [{"id": "a", "text": "On June 1, departure for Ajaccio."}]}
    fr_plan, en_plan, stats = asyncio.run(
        fs.write_film_chain(fr_raw, seconds=150, en_raw=en_raw, cascade=lambda *_a, **_k: ""),
    )
    assert fr_plan and en_plan
    assert stats.get("lightning") == 1


def test_en_upcoming_stops_sentence_is_not_an_invented_name():
    """« Upcoming stops: … » (fin de l'intégral au now réel) ne retombe pas en français."""
    src = ("Aujourd'hui, le bateau est à Mata-Utu (Wallis-et-Futuna). "
           "Les escales à venir : Nouméa, Dzaoudzi, Tromelin, Saint-Gilles, Europa, La Rochelle.")
    en = ("Today, the boat is at Mata-Utu (Wallis and Futuna). "
          "Upcoming stops: Nouméa, Dzaoudzi, Tromelin, Saint-Gilles, Europa, La Rochelle.")
    facts = {"places": ["Mata-Utu (Wallis-et-Futuna)", "Nouméa", "Dzaoudzi", "Tromelin",
                        "Saint-Gilles", "Europa", "La Rochelle"],
             "en_names": sorted(n.title() for n in fs._en_translation_names(en, src))}
    guarded, rewritten, fallen = fs.apply_written_guard(src, en, facts, lang="en")
    assert fallen == 0 and rewritten == 2
    assert "escales à venir" not in guarded
