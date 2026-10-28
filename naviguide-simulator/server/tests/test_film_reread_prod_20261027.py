"""Régression : le contrôle de relecture rejette le film officiel réel pour `skip`.

Données : extraits des GET publics de production du 27/10/2026
(/voyage/official/film?style=raw, /voyage/official/clock, /voyage/official).
"""
import json
from pathlib import Path

import voyage_store
from film_script import _route_stops_for_reread, _skip_pairs, nemotron_reread_report

FIX = Path(__file__).parent / "fixtures" / "film_reread_20261027"


def _load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def _prod_stops(monkeypatch):
    film = _load("fixture-film.json")
    voy = {
        "marks": _load("fixture-voyage-marks.json")["marks"],
        "clock": {"marks": _load("fixture-clock.json")["marks"]},
    }
    monkeypatch.setattr(voyage_store, "load_voyage", lambda _vid: voy)
    return film, _route_stops_for_reread(film)


def test_real_official_film_is_not_rejected_for_skip(monkeypatch):
    film, stops = _prod_stops(monkeypatch)
    chapters = film["chapters"]
    blob = " ".join(ch.get("text") or "" for ch in chapters)
    report = nemotron_reread_report(blob, stops, lang="fr", chapters=chapters)
    # Avant correctif : `quitté Saint-Maur` (leg-0) s'apparie à `pour Halifax`
    # (leg-7), 1 192 caractères plus loin, et toute la route devient « omise ».
    assert "skip" not in report["faults"], report


def test_real_intermediate_stop_is_still_detected(monkeypatch):
    _film, stops = _prod_stops(monkeypatch)
    assert _skip_pairs("Le navire a quitté La Rochelle pour Fort-de-France.", stops)
    assert not _skip_pairs("Le navire a quitté Ajaccio pour Fort-de-France.", stops)
