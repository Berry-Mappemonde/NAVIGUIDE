"""Texte / ancres / bulles : un index pointe toujours dans le texte qu'il décrit.

Production du 27/10 (film-raw, 13 chapitres) : leg-8 annonçait des bulles aux
caractères 117 et 205 d'un texte de 115 caractères ; leg-1, 2, 6, 11, 13, 14
avaient aussi des ancres ou des bulles au-delà de la fin. Cause : le texte est
retouché (fit_chapter_text, budget 150 s, sujet DC substitué, phrase de vol
ajoutée) APRÈS le calcul des index, sans les recalculer.

Fixture : les chapitres réellement composés par le moteur (main 36c11fe) sur
les GET publics de production, juste avant le premier budget.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import film_script as fs

FIX = Path(__file__).parent / "fixtures" / "film_reread_20261027"


def _chapters() -> list[dict]:
    data = json.loads((FIX / "fixture-chapters-before-budget.json").read_text(encoding="utf-8"))
    return copy.deepcopy(data["chapters"])


def _faults(chapters: list[dict]) -> list[str]:
    out: list[str] = []
    for ch in chapters:
        text = ch.get("text") or ""
        n = len(text)
        idx = [int(a.get("charIdx") or 0) for a in ch.get("anchors") or []]
        for i in idx:
            if not 0 <= i <= n:
                out.append(f"{ch['id']}: ancre {i} hors texte ({n} car.)")
        if idx != sorted(set(idx)):
            out.append(f"{ch['id']}: ancres non strictement croissantes {idx}")
        for ev in ch.get("events") or []:
            i = int(ev.get("charIdx") or 0)
            if not 0 <= i < max(1, n):
                out.append(f"{ch['id']}: bulle {ev.get('id')} à {i} hors texte ({n} car.)")
    return out


def _spoken_events(ch: dict) -> list[tuple[int, int]]:
    """(charIdx de la bulle, position où sa phrase est dite) pour les bulles dites."""
    text = ch.get("text") or ""
    rows = []
    for ev in ch.get("events") or []:
        fact = str(ev.get("fact") or "").strip()
        if len(fact) >= 20 and fact in text:
            rows.append((int(ev.get("charIdx") or 0), text.index(fact)))
    return rows


def _until_sentence_end(text: str, i: int) -> str:
    end = text.find(". ", i)
    return text[i:min(i + 20, end + 1 if end >= 0 else len(text))]


def test_fixture_reproduit_le_defaut_de_production():
    # Garde-fou : la fixture contient bien des index faux avant toute retouche.
    assert _faults(_chapters())


def test_budget_150s_garde_ancres_et_bulles_dans_le_texte():
    chapters = _chapters()
    fs._film_apply_char_budget(chapters, 150)
    assert _faults(chapters) == []


def test_bulle_dite_s_affiche_quand_sa_phrase_est_dite():
    chapters = _chapters()
    fs._film_apply_char_budget(chapters, 150)
    for ch in chapters:
        for got, said in _spoken_events(ch):
            assert got == said, (ch["id"], got, said, ch["text"])


def test_ancres_suivent_leur_phrase_apres_coupe():
    # Une ancre conservée désigne toujours le même début de phrase qu'avant la coupe.
    before = {c["id"]: c for c in _chapters()}
    chapters = _chapters()
    fs._film_apply_char_budget(chapters, 150)
    for ch in chapters:
        old = before[ch["id"]]
        old_text, new_text = old["text"], ch["text"]
        old_by_t: dict[str, set[str]] = {}
        for a in old.get("anchors") or []:
            i = int(a["charIdx"])
            if 0 <= i < len(old_text):
                old_by_t.setdefault(a["t"], set()).add(_until_sentence_end(old_text, i))
        for a in ch.get("anchors") or []:
            snippets = {sn for sn in old_by_t.get(a["t"], set()) if sn in new_text}
            i = int(a["charIdx"])
            if snippets and i < len(new_text):
                assert _until_sentence_end(new_text, i) in snippets, (ch["id"], a, snippets, new_text)


def test_sujet_dc_substitue_garde_les_index():
    chapters = _chapters()
    fs._film_apply_char_budget(chapters, 150)
    bag = json.loads((FIX / "fixture-dc-subjects.json").read_text(encoding="utf-8"))
    ids, bag = bag["filmChoice"], bag["dcSubjects"]
    out = fs.apply_chosen_subjects({"chapters": chapters}, ids, bag, 150)
    assert _faults(out["chapters"]) == []


def test_place_bulles_phrase_fusionnee_a_son_instant():
    # « Le 20 juin, les eaux marocaines. » a été fusionnée dans « La route passe
    # par… » : la bulle s'affiche quand le récit atteint le 20 juin, pas après la fin.
    ch = {
        "id": "x", "tA": "2026-06-09T00:00:00Z", "tB": "2026-07-14T00:00:00Z",
        "text": "Le 9 juin, départ. La route passe par Gibraltar. Arrivée à Fort-de-France le 14 juillet.",
        "anchors": [
            {"charIdx": 0, "t": "2026-06-09T00:00:00Z"},
            {"charIdx": 19, "t": "2026-06-19T00:00:00Z"},
            {"charIdx": 50, "t": "2026-07-14T00:00:00Z"},
        ],
        "events": [
            {"id": "z", "charIdx": 400, "kind": "zee", "fact": "Le 20 juin, les eaux marocaines.",
             "card": {"at": "2026-06-20T00:00:00Z"}},
            {"id": "s", "charIdx": 900, "kind": "stop", "fact": "Arrivée à Fort-de-France le 14 juillet.",
             "card": {"at": "2026-07-14T00:00:00Z"}},
        ],
    }
    fs._place_chapter_events(ch)
    got = {e["id"]: e["charIdx"] for e in ch["events"]}
    assert got["s"] == ch["text"].index("Arrivée")
    assert 19 < got["z"] < 50
