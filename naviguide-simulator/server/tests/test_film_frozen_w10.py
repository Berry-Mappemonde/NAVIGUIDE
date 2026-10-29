"""W10 : brut recalculé depuis le stock figé (29/10/2026) — sans Token Factory."""
from __future__ import annotations

import json
import re
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
import voyage_api
from climo_events import EQUATOR_BAND_DEG
from film_script import build_raw_from_moments

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ARCHIVE = FIXTURES / "official_store.tar.gz"
NOW_MS = int(datetime(2026, 10, 29, 11, 45, tzinfo=timezone.utc).timestamp() * 1000)

_ARRIVAL_COAST_FR = re.compile(
    r"le bateau longe (Mata-Utu|Dégrad des Cannes)\b", re.I,
)
_ARRIVAL_COAST_EN = re.compile(
    r"the boat skirts (Mata-Utu|D[ée]grad des Cannes)\b", re.I,
)
_AT_EQUATOR_FR = re.compile(r"\bà l['']équateur\b", re.I)
_AT_EQUATOR_EN = re.compile(r"\bat the equator\b", re.I)


def _load_frozen_stock() -> tuple[dict, dict, dict]:
    voyage_api._ROUTE_GEOJSON = FIXTURES / "official_store.route.geojson"
    voyage_api._OFFICIAL_BODY_CACHE = None
    if not ARCHIVE.is_file():
        pytest.skip("archive official_store.tar.gz absente")
    with tarfile.open(ARCHIVE, "r:gz") as tf:
        moments_doc = json.load(
            tf.extractfile("c4a0d2dc06cea61b_2026-05-15T08_00_00Z_2026-10-15_rg4/moments.json"),
        )
        climo_doc = json.load(
            tf.extractfile("c4a0d2dc06cea61b_2026-05-15T08_00_00Z_2026-09-27/climo.json"),
        )
    moments = moments_doc.get("payload") or moments_doc
    clock = (climo_doc.get("payload") or climo_doc)["clock"]
    journal = {"moments": moments.get("moments") or [], **(moments.get("journal") or {})}
    live = {
        "filmNm": 20000,
        "sailNm": 19800,
        "iso": "2026-10-29T11:45:00Z",
        "status": "live",
    }
    return clock, journal, live


@pytest.mark.parametrize("lang", ("fr", "en"))
def test_frozen_stock_raw_has_no_arrival_port_coast_echo(lang: str):
    clock, journal, live = _load_frozen_stock()
    plan = build_raw_from_moments(
        clock, clock.get("marks") or [], live, journal,
        lang=lang, seconds=0, now_ms=NOW_MS,
    )
    blob = " ".join(c.get("text") or "" for c in plan.get("chapters") or [])
    pat = _ARRIVAL_COAST_EN if lang == "en" else _ARRIVAL_COAST_FR
    assert not pat.search(blob), pat.search(blob).group(0) if pat.search(blob) else blob[:200]


@pytest.mark.parametrize("lang", ("fr", "en"))
def test_frozen_stock_raw_never_says_at_equator_outside_climo_band(lang: str):
    """« à l'équateur » / « at the equator » (pas « près de ») : R3, pas à 5° N."""
    clock, journal, live = _load_frozen_stock()
    plan = build_raw_from_moments(
        clock, clock.get("marks") or [], live, journal,
        lang=lang, seconds=0, now_ms=NOW_MS,
    )
    blob = " ".join(c.get("text") or "" for c in plan.get("chapters") or [])
    pat = _AT_EQUATOR_EN if lang == "en" else _AT_EQUATOR_FR
    assert not pat.search(blob), pat.search(blob).group(0)
    assert EQUATOR_BAND_DEG <= 2.0
