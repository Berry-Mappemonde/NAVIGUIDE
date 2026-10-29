"""Version 150 s au « now » réel (29/10/2026) : la barre suit la date dite.

Le 2:30 coupe des phrases d'eaux (« Puis, les eaux capverdiennes. ») dont
l'ancre restait dans la liste. Le repli « 12 premiers caractères » de
_locate_spoken la posait sur une autre phrase restée (« Puis, les eaux
françaises. ») : la barre disait 26 juin pour une phrase du 4 juin, et la
relecture refusait le rédigé (« date »).
"""
import film_script as fs
from film_script import _anchor_dates_regress, _locate_spoken, chapter_anchors

DAY = 86_400_000
T0 = 1_780_531_200_000  # 2026-06-04T00:00:00Z


def _iso_day(iso: str) -> str:
    return iso[:10]


def test_prefix_fallback_needs_the_same_sentence():
    text = "Le 4 juin, départ vers Fort-de-France. Puis, les eaux françaises. Le 6 juin, les eaux italiennes."
    assert _locate_spoken(text, "Puis, les eaux capverdiennes.") < 0
    assert _locate_spoken(text, "Puis, les eaux françaises.") == text.index("Puis, les eaux françaises.")


def test_prefix_fallback_still_finds_a_trimmed_sentence():
    text = "Le 4 juin, départ vers Fort-de-France : 5 153 milles. Arrivée le 14 juillet."
    spoken = "Le 4 juin, départ vers Fort-de-France : 5 153 milles, une quarantaine de jours de mer."
    assert _locate_spoken(text, spoken) == 0


def test_cut_sentence_does_not_steal_a_kept_anchor():
    text = (
        "Le 4 juin, départ vers Fort-de-France. Puis, les eaux françaises. "
        "Le 6 juin, les eaux italiennes. Arrivée à Fort-de-France le 14 juillet."
    )
    anchored = [
        ("Le 4 juin, départ vers Fort-de-France.", T0, {"role": "depart"}),
        ("Puis, les eaux françaises.", T0, {"kind": "zee-enter", "place": "France"}),
        ("Le 6 juin, les eaux italiennes.", T0 + 2 * DAY, {"kind": "zee-enter", "place": "Italie"}),
        ("Puis, les eaux capverdiennes.", T0 + 22 * DAY, {"kind": "zee-enter", "place": "Cap-Vert"}),
        ("Arrivée à Fort-de-France le 14 juillet.", T0 + 40 * DAY, {"role": "arrive"}),
    ]
    anchors = chapter_anchors(text, anchored, T0, T0 + 40 * DAY, "fr")
    by_place = {a.get("place"): _iso_day(a["t"]) for a in anchors if a.get("place")}
    assert by_place.get("France") == "2026-06-04"
    assert by_place.get("Italie") == "2026-06-06"
    assert "Cap-Vert" not in by_place
    chapter = {"text": text, "anchors": anchors}
    assert not _anchor_dates_regress([chapter], "fr")
    assert fs.nemotron_reread_report(text, [], lang="fr", chapters=[chapter]).get("faults", []).count("date") == 0
