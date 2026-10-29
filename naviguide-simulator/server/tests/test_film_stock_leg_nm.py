"""L1 / F3 : le stock figé (brut 150 s et rédigé intégral) aligne les milles par jambe.

Calcul et comparaison locaux uniquement — aucun appel Token Factory.
"""
from __future__ import annotations

import json
import pathlib
import re

FIX = pathlib.Path(__file__).parent / "fixtures"
RAW_150 = FIX / "film_150_raw_2026-10-29.json"
WRITTEN = FIX / "film_integral_written_2026-10-29.json"

_FR_NM = re.compile(r"(\d[\d \u00a0]*\d|\d)\s+milles")
_EN_NM = re.compile(r"([\d,]+)\s+miles")


def _first_leg_nm(text: str, *, lang: str) -> str | None:
    if not text:
        return None
    m = (_EN_NM if lang == "en" else _FR_NM).search(text)
    if not m:
        return None
    raw = m.group(1).replace("\u00a0", " ").replace(",", "")
    return re.sub(r"\s+", " ", raw.strip())


def _chapters_by_id(plan: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for ch in plan.get("chapters") or []:
        if isinstance(ch, dict) and ch.get("id"):
            out[str(ch["id"])] = ch
    return out


def test_frozen_raw_150_and_written_integral_share_leg_nm_by_chapter():
    raw = json.loads(RAW_150.read_text(encoding="utf-8"))
    written = json.loads(WRITTEN.read_text(encoding="utf-8"))
    raw_by_id = _chapters_by_id(raw)
    fr_written = _chapters_by_id(written["fr"])
    en_written = _chapters_by_id(written["en"])

    shared = sorted(set(raw_by_id) & set(fr_written))
    assert shared, "aucun chapitre commun entre brut 150 et rédigé intégral"

    mismatches: list[str] = []
    for cid in shared:
        r_nm = _first_leg_nm(raw_by_id[cid].get("text") or "", lang="fr")
        w_nm = _first_leg_nm(fr_written[cid].get("text") or "", lang="fr")
        if r_nm is None and w_nm is None:
            continue
        if r_nm != w_nm:
            mismatches.append(f"{cid}: brut={r_nm!r} rédigé={w_nm!r}")
    assert not mismatches, "\n".join(mismatches)


def _norm_digits(label: str | None) -> str:
    return re.sub(r"[\s,\u00a0]", "", label or "")


def test_written_fr_and_en_share_mile_labels_on_halifax_and_papeete_legs():
    written = json.loads(WRITTEN.read_text(encoding="utf-8"))
    fr = _chapters_by_id(written["fr"])
    en = _chapters_by_id(written["en"])
    for cid in ("leg-7", "leg-8", "leg-10"):
        fr_nm = _first_leg_nm(fr[cid]["text"], lang="fr")
        en_nm = _first_leg_nm(en[cid]["text"], lang="en")
        assert _norm_digits(fr_nm) == _norm_digits(en_nm)
        if cid in ("leg-7", "leg-8"):
            assert _norm_digits(fr_nm) == "497"
        if cid == "leg-10":
            assert _norm_digits(fr_nm) == "6511"


def test_opening_nm_label_matches_chapter_metrics_halifax_hop():
    """Brut recalculé : legNm plan-review = libellé parlé dans le texte."""
    from datetime import datetime, timezone

    from film_script import _opening_nm_label, build_raw_script, chapter_metrics
    from tests.test_film_script import _halifax_hop_marks
    from voyage_clock import OFFICIAL_T0

    marks = _halifax_hop_marks()
    clock = {
        "t0": OFFICIAL_T0,
        "marks": marks,
        "vertices": [
            {"iso": "2026-08-12T03:59:04Z", "lat": 44.65, "lon": -63.57, "vehicle": "plane", "filmNm": 8780.6263},
            {"iso": "2026-08-15T08:59:54Z", "lat": 46.78, "lon": -56.18, "vehicle": "side", "filmNm": 9160.2308},
        ],
    }
    review = {"legs": [{
        "from": "Halifax (Nouvelle-Écosse)",
        "to": "Saint-Pierre (Saint-Pierre-et-Miquelon)",
        "legNm": 497,
        "daysAtSea": 2.6,
        "plannedKnots": 8,
    }]}
    now_ms = int(datetime(2026, 8, 20, tzinfo=timezone.utc).timestamp() * 1000)
    plan = build_raw_script(
        clock, marks, {"iso": "2026-08-20T00:00:00Z"}, None,
        lang="fr", seconds=150, now_ms=now_ms, review=review,
    )
    hop = next(
        c for c in plan["chapters"]
        if "Halifax" in (c.get("fromName") or "") and "Saint-Pierre" in (c.get("toName") or "")
    )
    w = hop.get("window") or {}
    leg_nm = chapter_metrics({**w, "fromName": hop.get("fromName"), "toName": hop.get("toName")}, review)["legNm"]
    assert leg_nm == 497
    label = _opening_nm_label(leg_nm, "fr")
    assert label in (hop.get("text") or "")
