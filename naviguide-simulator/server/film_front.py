"""Lecture du film et de l'horloge, hors de la file du briefing.

Le processus :8010 est occupé par /ici. Ces deux lectures sont un snapshot
déjà rangé : elles répondent sur :8011, donc le bouton du film n'attend pas.
"""
from __future__ import annotations

import inspect
import logging
import sys
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import Response

_DIR = Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

import official_store  # noqa: E402

log = logging.getLogger("naviguide-film-front")
app = FastAPI()


def _serve_film(lang: str, seconds: int, style: str) -> dict:
    sig = inspect.signature(official_store.serve_film)
    kwargs = {"lang": lang, "seconds": seconds}
    if "style" in sig.parameters:
        kwargs["style"] = style
    return official_store.serve_film(**kwargs)


@app.get("/voyage/official/film")
def get_official_film(
    lang: str = Query("fr"),
    seconds: int = Query(0, ge=0, le=300),
    style: str = Query("raw"),
):
    try:
        out = _serve_film(lang, seconds, style)
    except Exception as exc:
        log.exception("GET /voyage/official/film")
        official_store.nudge_fill_process()
        return official_store.preparing_payload("film", {
            "chapters": [], "source": "rules", "chars": 0,
            "targetSeconds": seconds, "hasWritten": False,
            "reason": f"film indisponible: {exc}",
        })
    if out.get("status") == official_store.PREPARING:
        official_store.nudge_fill_process()
    return out


@app.get("/voyage/official/clock")
def get_official_clock():
    try:
        raw = official_store.serve_clock_bytes()
    except Exception as exc:
        log.exception("GET /voyage/official/clock")
        official_store.nudge_fill_process()
        return official_store.preparing_payload("climo", {
            "reason": f"horloge indisponible: {exc}",
        })
    if raw:
        return Response(content=raw, media_type="application/json")
    official_store.nudge_fill_process()
    return official_store.preparing_payload("climo", {
        "reason": "horloge officielle en préparation",
    })
