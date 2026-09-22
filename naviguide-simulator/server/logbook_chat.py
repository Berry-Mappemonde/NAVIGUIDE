"""Chatbot journal de bord (lot D, bascule L2 / U4).

Le skipper pose une question sur **toutes les données de l'application** —
position et vent au bateau (horloge + GRIB), ZEE, ports d'entrée, AMP, ports,
projets et fiches science autour, prochaine escale, polaire et ordres du
skipper (envoyés par le client), journal — et la réponse **cite un JSON de
faits construit ici**, jamais le monde. Cascade L1 :
`cascade_text(tier="write")`, ou `tier="fast"` si la question fait moins de
80 caractères et ne contient pas pourquoi / comment / why / how.

Pas de détection d'intention : **chaque échange est consigné** dans le
journal (`kind: chat` : horodatage, question, réponse, résumé) quand la clé
admin est là ; sans clé, la réponse est rendue sans consignation.

Un chiffre ne passe jamais par le LLM : toute phrase de la réponse qui porte
un nombre absent du contexte est retirée (`filter_numbers`, inchangé).
Chaque réponse porte `source`.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from admin_guard import is_admin, rate_limited
from story_cascade import TOKENFACTORY_BASE, _clean_text, cascade_text, nebius_key, tidy_story

log = logging.getLogger("naviguide-simulator.logbook")

router = APIRouter()

QUESTION_MAX = 500
CONTEXT_MAX_BYTES = 12_000
ANSWER_SENTENCES = 3
ANSWER_CHARS = 480
JOURNAL_TAIL = 20

_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[^\s])")
_WHY_RE = re.compile(r"(?i)(?<!\w)(pourquoi|comment|why|how)(?!\w)")
FAST_QUESTION_MAX = 80
WX_MEMORY = 200
_WX_WORDS = re.compile(
    r"(?i)(n[œoe]uds?|knots?|vent|wind|gale|coup de vent|rafale|hs|vague|mer|sea|houle|force)",
)
_SEA_WORDS = re.compile(r"(?i)(hs|vague|mer|sea|houle)")
EMBED_MODEL = "Qwen/Qwen3-Embedding-8B"
EMBED_MIN_COS = 0.25


# ── context ─────────────────────────────────────────────────────────────────

def _slim_places(items: Any, n: int = 4) -> list[dict]:
    out = []
    for it in items or []:
        if isinstance(it, dict) and it.get("name"):
            row = {"name": it["name"]}
            if isinstance(it.get("nm"), (int, float)):
                row["nm"] = round(float(it["nm"]), 1)
            out.append(row)
        if len(out) >= n:
            break
    return out


def _next_stop(clock: dict | None, now: datetime) -> Optional[dict]:
    if not clock:
        return None
    from voyage_clock import parse_iso  # noqa: PLC0415
    t0 = parse_iso(clock["t0"])
    for m in clock.get("marks") or []:
        if m.get("tHours") is None or not m.get("name"):
            continue
        from datetime import timedelta  # noqa: PLC0415
        eta = t0 + timedelta(hours=float(m["tHours"]))
        if eta > now:
            return {"name": m["name"], "eta": eta.isoformat().replace("+00:00", "Z"), "holdDays": round(float(m.get("holdHours") or 0) / 24)}
    return None


async def build_context(client_ctx: dict | None, now: datetime, http: httpx.AsyncClient | None = None) -> dict[str, Any]:
    """The facts the bot may cite. Nothing here comes from the model."""
    from voyage_api import _grib_around_from_live, _latest_official_grib, _now  # noqa: PLC0415
    from voyage_clock import OFFICIAL_VOYAGE_ID, sample_clock_at_time  # noqa: PLC0415
    from voyage_store import load_voyage  # noqa: PLC0415
    from saildocs import wind_at_daily  # noqa: PLC0415
    import voyage_journal as journal  # noqa: PLC0415

    ctx: dict[str, Any] = {"now": now.isoformat().replace("+00:00", "Z")}
    client_ctx = client_ctx if isinstance(client_ctx, dict) else {}
    view = str(client_ctx.get("view") or "suivre")[:12]
    ctx["view"] = view

    voy = load_voyage(OFFICIAL_VOYAGE_ID)
    clock = (voy or {}).get("clock")
    live = None
    if clock:
        sample = sample_clock_at_time(clock, now)
        if sample and sample.get("lat") is not None:
            at_quay = bool(sample.get("atQuay"))
            planned = sample.get("plannedKnots")
            if planned is None and not at_quay:
                planned = sample.get("speedKnots")
            boat_in = client_ctx.get("boat") if isinstance(client_ctx.get("boat"), dict) else None
            measured = boat_in.get("speedKnots") if boat_in is not None else None
            measured = float(measured) if isinstance(measured, (int, float)) else None
            regime = sample.get("regime") or sample.get("kind") or "climatology"
            # Lot C3 : en Suivre, une seule vitesse — celle de l'horloge (0 à quai).
            if at_quay:
                speed, basis = 0, "clock"
            elif view == "suivre":
                speed, basis = sample.get("speedKnots"), "clock"
            elif measured is not None:
                speed, basis = measured, "measured"
            else:
                speed, basis = sample.get("speedKnots"), "clock"
            live = {
                "lat": round(float(sample["lat"]), 3),
                "lon": round(float(sample["lon"]), 3),
                "sailNm": round(float(sample.get("sailNm") or 0)),
                "speedKnots": speed,
                "plannedKnots": planned,
                "atQuay": at_quay,
                "status": sample.get("status"),
                "basis": basis,
                "regime": regime,
            }
            try:
                around = _grib_around_from_live(voy, now)
                grib = _latest_official_grib(around, now)
                wind = wind_at_daily(grib, float(sample["lat"]), float(sample["lon"]), now)
                if wind:
                    live["wind"] = {k: wind.get(k) for k in ("windKnots", "dirFromDeg", "pressHpa", "rainMm", "hs", "model") if wind.get(k) is not None}
                    live["wind"]["kind"] = "forecast"
                else:
                    live["wind"] = {"kind": "absent"}
            except Exception as exc:
                live["wind"] = {"kind": "absent", "reason": type(exc).__name__}
    ctx["official"] = live
    ctx["nextStop"] = _next_stop(clock, now)

    # The boat the question is about: the official one, or the film boat the client sent.
    boat = client_ctx.get("boat") if isinstance(client_ctx.get("boat"), dict) else None
    lat = lon = None
    if boat and isinstance(boat.get("lat"), (int, float)) and isinstance(boat.get("lon"), (int, float)):
        lat, lon = float(boat["lat"]), float(boat["lon"])
        boat_out = {
            "lat": round(lat, 3),
            "lon": round(lon, 3),
            "basis": "simulation" if view != "suivre" else "clock",
            "iso": boat.get("iso"),
        }
        if view == "suivre" and live is not None and live.get("speedKnots") is not None:
            boat_out["speedKnots"] = float(live["speedKnots"])
            boat_out["atQuay"] = bool(live.get("atQuay"))
            if live.get("regime"):
                boat_out["regime"] = live["regime"]
        elif isinstance(boat.get("speedKnots"), (int, float)):
            boat_out["speedKnots"] = float(boat["speedKnots"])
            if boat.get("regime"):
                boat_out["regime"] = boat["regime"]
        ctx["boat"] = boat_out
    elif live:
        lat, lon = live["lat"], live["lon"]
        boat_out = {"lat": lat, "lon": lon, "basis": "clock"}
        if live.get("speedKnots") is not None:
            boat_out["speedKnots"] = float(live["speedKnots"])
        if live.get("regime"):
            boat_out["regime"] = live["regime"]
        boat_out["atQuay"] = bool(live.get("atQuay"))
        ctx["boat"] = boat_out

    if lat is not None:
        try:
            from ici_engine import fill_dossier  # noqa: PLC0415
            bag = await fill_dossier(lat, lon, 30.0, client=http, thin=True, rich=True)
            nearby = bag.get("nearby") or {}
            science = bag.get("science")
            ctx["around"] = {
                "zee": {k: (bag.get("zee") or {}).get(k) for k in ("name", "mrgid", "gold") if (bag.get("zee") or {}).get(k) is not None} or None,
                "portsOfEntry": _slim_places(bag.get("poe")),
                "protectedAreas": _slim_places(bag.get("amp")),
                "marinas": _slim_places(nearby.get("marinas")),
                "harbourMasters": _slim_places(nearby.get("capitaineries"), 2),
                "ports": _slim_places(nearby.get("wpi"), 3),
                "projects": _slim_places(bag.get("projects"), 3),
                "science": _slim_places(science.get("nearby") if isinstance(science, dict) else science, 3),
                "aidsToNavigation": _slim_places((bag.get("aton") or {}).get("nearby"), 3),
                "depthM": ((bag.get("emodnet") or {}).get("bathy") or {}).get("depth_m"),
            }
        except Exception as exc:
            ctx["around"] = {"reason": f"unavailable:{type(exc).__name__}"}

    tail = journal.latest(JOURNAL_TAIL, kinds=("stop", "grib", "note", "zee", "amp", "poe", "wx", "chat"))
    ctx["journal"] = [
        {k: e.get(k) for k in ("kind", "t", "event", "name", "text", "windKnots", "dirFromDeg", "hs", "summary") if e.get(k) is not None}
        for e in tail
    ]

    # What only the client knows: its polar, its skipper's orders, its view.
    for key in ("polar", "orders", "leg"):
        val = client_ctx.get(key)
        if isinstance(val, dict):
            ctx[key] = val
    return ctx


# ── mémoire journal (lot L6 / U13) : mots-clés d'abord, embeddings option ──

def embeddings_enabled() -> bool:
    return (os.environ.get("NAVIGUIDE_EMBEDDINGS") or "").strip() == "1"


def _slim_wx(entry: dict) -> dict[str, Any]:
    return {
        k: entry.get(k)
        for k in (
            "kind", "t", "event", "name", "windKnots", "maxWindKnots",
            "hs", "maxHs", "dirFromDeg", "hours", "level", "model", "basis",
        )
        if entry.get(k) is not None
    }


def _question_threshold(question: str) -> Optional[float]:
    nums: list[float] = []
    for m in _NUM_RE.findall(question or ""):
        try:
            nums.append(float(m.replace(",", ".")))
        except ValueError:
            continue
    return nums[0] if nums else None


def wx_keyword_hits(question: str, entries: list[dict] | None) -> list[dict]:
    """Faits wx déjà au journal. Aucun souvenir inventé.

    « avons-nous déjà eu plus de 35 nœuds ? » → les entrées dont
    `windKnots` / `maxWindKnots` ≥ 35. Sans seuil : les `gale` / `sea`.
    """
    q = question or ""
    thr = _question_threshold(q)
    if thr is None and not _WX_WORDS.search(q):
        return []
    sea_q = bool(_SEA_WORDS.search(q))
    out: list[dict] = []
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        wind = e.get("maxWindKnots") if e.get("maxWindKnots") is not None else e.get("windKnots")
        hs = e.get("maxHs") if e.get("maxHs") is not None else e.get("hs")
        if thr is not None:
            if sea_q:
                if isinstance(hs, (int, float)) and float(hs) >= thr:
                    out.append(_slim_wx(e))
            elif isinstance(wind, (int, float)) and float(wind) >= thr:
                out.append(_slim_wx(e))
        elif e.get("event") in {"gale", "sea"} or e.get("kind") == "wx":
            out.append(_slim_wx(e))
    return out[:8]


def _wx_embed_text(entry: dict) -> str:
    parts = [str(entry.get("kind") or "wx"), str(entry.get("event") or "")]
    for k in ("t", "windKnots", "maxWindKnots", "hs", "maxHs", "hours", "level", "model"):
        if entry.get(k) is not None:
            parts.append(f"{k}={entry[k]}")
    return " ".join(p for p in parts if p)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (na * nb)


async def _embed(texts: list[str], client: httpx.AsyncClient | None) -> list[list[float]]:
    key = nebius_key()
    if not key or not texts:
        return []
    url = f"{TOKENFACTORY_BASE}/embeddings"
    payload = {"model": EMBED_MODEL, "input": texts}
    own = client is None
    http = client or httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=8.0))
    try:
        r = await http.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
        if r.status_code >= 400:
            return []
        data = r.json()
        rows = data.get("data") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            return []
        out: list[list[float]] = []
        for row in sorted(rows, key=lambda x: int((x or {}).get("index") or 0)):
            emb = (row or {}).get("embedding")
            if isinstance(emb, list) and emb:
                out.append([float(v) for v in emb])
        return out
    except Exception:
        return []
    finally:
        if own:
            await http.aclose()


async def wx_embed_hits(
    question: str, entries: list[dict] | None, client: httpx.AsyncClient | None = None,
) -> list[dict]:
    """Qwen/Qwen3-Embedding-8B — seulement si NAVIGUIDE_EMBEDDINGS=1. Faits seuls."""
    items = [e for e in (entries or []) if isinstance(e, dict)]
    if not items or not (question or "").strip():
        return []
    vecs = await _embed([question] + [_wx_embed_text(e) for e in items], client)
    if len(vecs) != 1 + len(items):
        return []
    qv, evs = vecs[0], vecs[1:]
    ranked = sorted(
        ((_cosine(qv, ev), e) for e, ev in zip(items, evs)),
        key=lambda p: -p[0],
    )
    return [_slim_wx(e) for score, e in ranked if score >= EMBED_MIN_COS][:5]


async def similar_wx(
    question: str, entries: list[dict] | None, client: httpx.AsyncClient | None = None,
) -> list[dict]:
    """Mots-clés d'abord ; embeddings seulement si le drapeau est à 1 et rien trouvé."""
    hits = wx_keyword_hits(question, entries)
    if hits:
        return hits
    if embeddings_enabled():
        return await wx_embed_hits(question, entries, client)
    return []


# ── answer ──────────────────────────────────────────────────────────────────

def chat_tier(question: str) -> str:
    """write by default; Lightning (`fast`) for a short factual question (lot L2)."""
    q = " ".join((question or "").split())
    if len(q) < FAST_QUESTION_MAX and not _WHY_RE.search(q):
        return "fast"
    return "write"


def _prompt(question: str, ctx: dict, lang: str) -> tuple[str, str]:
    en = (lang or "fr").lower().startswith("en")
    system = (
        "You are the logbook of the Berry-Mappemonde sailing expedition. Answer the skipper's question in at most "
        "THREE plain sentences, using ONLY the JSON of facts provided (positions, wind, zones, ports, areas, journal, "
        "polar, skipper's orders). Every figure you write must appear in the JSON, with its unit. If the JSON does not "
        "hold the answer, say so in one sentence. No title, no list, no bold, nothing about tools or models. Thinking OFF."
        if en else
        "Tu es le journal de bord de l’expédition à la voile Berry-Mappemonde. Réponds à la question du skipper en "
        "TROIS phrases simples au plus, à partir du SEUL JSON de faits fourni (positions, vent, zones, ports, aires, "
        "journal, polaire, ordres du skipper). Chaque chiffre que tu écris doit figurer dans le JSON, avec son unité. "
        "Si le JSON ne contient pas la réponse, dis-le en une phrase. Ni titre, ni liste, ni gras, rien sur les outils "
        "ou les modèles. Thinking OFF."
    )
    user = f"{'Question' if en else 'Question'} : {question}\nJSON :\n{json.dumps(ctx, ensure_ascii=False, default=str)}"
    return system, user


def _numbers(text: str) -> set[str]:
    out = set()
    for m in _NUM_RE.findall(text or ""):
        try:
            out.add(format(float(m.replace(",", ".")), "g"))  # "03" == "3", "14,2" == "14.2"
        except ValueError:
            continue
    return out


def filter_numbers(answer: str, ctx: dict) -> tuple[str, int]:
    """Drop every sentence carrying a number absent from the context (a year
    or a time in the context counts). Returns (text, dropped)."""
    allowed = _numbers(json.dumps(ctx, ensure_ascii=False, default=str))
    # Dates split into parts: 2026-05-15T08:00 → 2026, 05, 15, 08, 00 are all present already via _NUM_RE.
    kept, dropped = [], 0
    for s in _SENT_SPLIT_RE.split(answer or ""):
        s = s.strip()
        if not s:
            continue
        nums = _numbers(s)
        if nums and not nums.issubset(allowed):
            dropped += 1
            continue
        kept.append(s)
    return " ".join(kept), dropped


def summarize(question: str, answer: str) -> str:
    q = " ".join((question or "").split())[:90]
    first = _SENT_SPLIT_RE.split(answer or "")[0].strip() if answer else ""
    return f"{q} → {first[:160]}".strip(" →")


async def answer_question(question: str, lang: str, client_ctx: dict | None, now: datetime,
                          http: httpx.AsyncClient | None = None) -> dict[str, Any]:
    ctx = await build_context(client_ctx, now, http)
    try:
        import voyage_journal as journal  # noqa: PLC0415
        wx_all = journal.latest(WX_MEMORY, kinds=("wx",))
    except Exception:
        wx_all = [e for e in (ctx.get("journal") or []) if isinstance(e, dict) and e.get("kind") == "wx"]
    memory = await similar_wx(question, wx_all, http)
    if memory:
        ctx["memory"] = memory
    system, user = _prompt(question, ctx, lang)
    try:
        raw, source = await cascade_text(system, user, http, tier=chat_tier(question))
    except Exception as exc:
        return {"status": "failed", "reason": str(exc)[:160], "answer": None, "engine": None, "source": None, "context": ctx}
    tidy = tidy_story(raw, None, max_sentences=ANSWER_SENTENCES, max_chars=ANSWER_CHARS)
    text, dropped = filter_numbers(tidy, ctx)
    text = _clean_text(text)
    if not text:
        text = ("Le journal n’a pas cette information dans ses données." if not (lang or "fr").startswith("en")
                else "The logbook does not hold that information in its data.")
        source = "rules"
    return {"status": "ready", "answer": text, "engine": source, "source": source, "droppedSentences": dropped, "context": ctx}


# ── endpoint ────────────────────────────────────────────────────────────────

class ChatIn(BaseModel):
    question: str
    lang: Optional[str] = "fr"
    context: Optional[dict] = None


_chat_limited = rate_limited("logbook-chat", 6, 60.0, global_limit=60)


@router.post("/logbook/chat", dependencies=[Depends(_chat_limited)])
async def post_logbook_chat(body: ChatIn, request: Request):
    """Une question au journal de bord ; consignée (kind chat) quand la clé admin est là."""
    q = " ".join((body.question or "").split())
    if not q:
        raise HTTPException(400, "question vide")
    if len(q) > QUESTION_MAX:
        raise HTTPException(413, f"question trop longue (> {QUESTION_MAX} caractères)")
    if body.context is not None and len(json.dumps(body.context, default=str)) > CONTEXT_MAX_BYTES:
        raise HTTPException(413, "contexte trop volumineux")
    now = datetime.now(timezone.utc)
    out = await answer_question(q, body.lang or "fr", body.context, now)
    logged = False
    entry = None
    if out["status"] == "ready" and is_admin(request):
        import voyage_journal as journal  # noqa: PLC0415
        try:
            entry = journal.add_chat(q, out["answer"], summarize(q, out["answer"]), now, lang=body.lang or "fr", engine=out.get("engine"))
            logged = True
        except Exception as exc:  # the journal never breaks an answer
            log.warning("journal chat : %s", exc)
    return {
        "status": out["status"],
        "answer": out.get("answer"),
        "reason": out.get("reason"),
        "engine": out.get("engine"),
        "source": out.get("source") or out.get("engine"),
        "logged": logged,
        "entry": entry,
        "t": now.isoformat().replace("+00:00", "Z"),
        "facts": {k: out["context"].get(k) for k in ("official", "boat", "nextStop", "memory") if out["context"].get(k) is not None},
    }
