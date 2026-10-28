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


# --- Faute `date` : « Le 23 mai, une bouée » dans le chapitre Halifax → Saint-Pierre ---
# En production, leg-8 (13–17 août) commence par la phrase de la bouée du 23 mai.
# Son ouverture d'origine est reconstruite au format de `_side_opening_sentence`,
# avec la date de son ancre charIdx 0 (2026-08-14T23:50:23Z). Le reste vient des GET.
LEG8_OPENING = (
    "Le 14 août, à Halifax (Nouvelle-Écosse), l'équipage embarque sur "
    "un second voilier pour Saint-Pierre (Saint-Pierre-et-Miquelon)."
)
BUOY_PHRASE = "Le 23 mai, une bouée."


def _film_before_subjects():
    film = _load("fixture-film.json")
    chapters = [dict(ch) for ch in film["chapters"]]
    leg8 = next(ch for ch in chapters if ch["id"] == "leg-8")
    assert leg8["text"].startswith(BUOY_PHRASE)
    leg8["text"] = leg8["text"].replace(BUOY_PHRASE, LEG8_OPENING, 1)
    return chapters


def _chosen(chapters):
    from film_script import apply_chosen_subjects, film_choice_bag

    dc = _load("fixture-dc-subjects.json")
    bag = film_choice_bag(dc["dcSubjects"])
    return apply_chosen_subjects({"chapters": chapters}, dc["filmChoice"], bag, 150)


def test_dated_subject_stays_in_its_time_window():
    out = _chosen(_film_before_subjects())
    leg8 = next(ch for ch in out["chapters"] if ch["id"] == "leg-8")
    # L'ouverture du second bateau n'est pas une redite remplaçable.
    assert leg8["text"].startswith(LEG8_OPENING), leg8["text"]
    # Une bouée du 23 mai ne se place que dans un chapitre qui couvre le 23 mai.
    for ch in out["chapters"]:
        if BUOY_PHRASE in (ch.get("text") or ""):
            assert ch["tA"] <= "2026-05-23T13:27:42Z" <= ch["tB"], ch["id"]


def test_real_official_film_rereads_without_fault(monkeypatch):
    chapters = _chosen(_film_before_subjects())["chapters"]
    _film, stops = _prod_stops(monkeypatch)
    blob = " ".join(ch.get("text") or "" for ch in chapters)
    report = nemotron_reread_report(blob, stops, lang="fr", chapters=chapters)
    assert report["faults"] == [], report
    assert report["ok"] is True
