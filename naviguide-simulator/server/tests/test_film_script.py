"""Lot F3 — script du film : longueur, balises, aucun nombre nouveau, cache, sélection."""
import asyncio
from datetime import datetime, timezone

import pearl_store
import story_cache
from film_script import (
    CONNECTORS,
    FILM_MAX_CHARS,
    FILM_WRITE_MAX,
    FILM_WRITE_MIN,
    build_film_response,
    build_raw_script,
    connector_at,
    film_candidates,
    film_facts,
    journal_fingerprint,
    last_stop_id,
    select_film_events,
    written_is_valid,
)
from tests.test_voyage_journal import PUBLIC, _official
from voyage_clock import OFFICIAL_T0

CLOCK = {
    "t0": "2026-05-15T08:00:00Z",
    "marks": [
        {"name": "Saint-Maur (Berry, Indre)", "nm": 0, "filmNm": 0, "iso": "2026-05-15T08:00:00Z", "holdHours": 0, "lat": 46.8, "lon": 1.6},
        {"name": "La Rochelle", "nm": 0, "filmNm": 122, "iso": "2026-05-15T12:00:00Z", "holdHours": 72, "lat": 46.15, "lon": -1.16},
        {"name": "Ajaccio (Corse)", "nm": 1820, "filmNm": 1942, "iso": "2026-05-24T12:51:00Z", "holdHours": 72, "lat": 41.9, "lon": 8.7},
        {"name": "Fort-de-France (Martinique)", "nm": 6973, "filmNm": 7095, "iso": "2026-06-23T08:34:00Z", "holdHours": 72, "lat": 14.6, "lon": -61.0},
        {"name": "Nouméa (Nouvelle-Calédonie)", "nm": 19055, "filmNm": 19177, "iso": "2026-09-17T22:48:00Z", "holdHours": 72, "lat": -22.2, "lon": 166.4},
    ],
}
LIVE = {"filmNm": 19400, "sailNm": 19260, "iso": "2026-09-19T02:00:00Z", "status": "live"}
NOW_MS = int(datetime(2026, 9, 19, 2, 0, tzinfo=timezone.utc).timestamp() * 1000)
JOURNAL = {
    "latest": [
        {"id": "zee:es", "kind": "zee", "t": "2026-05-17T15:00:00Z", "event": "enter", "name": "Spanish Exclusive Economic Zone", "mrgid": 5693},
        {"id": "amp:cabrera", "kind": "amp", "t": "2026-05-18T02:00:00Z", "event": "nearby", "name": "Cabrera", "nm": 8},
        {"id": "poe:lr", "kind": "poe", "t": "2026-05-15T12:00:00Z", "event": "passed", "name": "La Rochelle - La Pallice", "poeId": "lr"},
        {"id": "wx:gale", "kind": "wx", "t": "2026-05-22T06:00:00Z", "event": "gale", "windKnots": 36.5, "maxWindKnots": 38, "hours": 6, "hs": 2.4},
        {"id": "climo:rose", "kind": "climo", "t": "2026-06-02T12:00:00Z", "event": "rose", "facts": {"deltaDeg": 120}, "name": "alizés"},
        {"id": "sci:pirata", "kind": "sci", "t": "2026-06-10T06:00:00Z", "name": "PIRATA", "facts": {"nm": 6, "name": "PIRATA"}},
        {"id": "wx:sea", "kind": "wx", "t": "2026-07-01T06:00:00Z", "event": "sea", "windKnots": 22, "maxHs": 4.2, "hours": 12, "hs": 4.2},
        {"id": "note:1", "kind": "note", "t": "2026-05-21T10:00:00Z", "text": "Première nuit au large."},
        {"id": "zee:fr", "kind": "zee", "t": "2026-05-16T09:00:00Z", "event": "enter", "name": "French Exclusive Economic Zone", "mrgid": 5677},
        {"id": "amp:pertuis", "kind": "amp", "t": "2026-05-15T18:00:00Z", "event": "nearby", "name": "Pertuis Charentais", "nm": 3},
        {"id": "poe:aj", "kind": "poe", "t": "2026-05-24T12:00:00Z", "event": "passed", "name": "Ajaccio", "poeId": "aj"},
        {"id": "sci:argo", "kind": "sci", "t": "2026-08-01T06:00:00Z", "name": "Argo", "facts": {"nm": 4}},
    ],
}


def _raw():
    return build_raw_script(CLOCK, CLOCK["marks"], LIVE, JOURNAL, lang="fr", seconds=150, now_ms=NOW_MS)


def test_raw_length_bounded_and_chapter1_names():
    plan = _raw()
    assert plan["chars"] <= FILM_MAX_CHARS
    assert plan["source"] == "rules"
    assert plan["chapters"]
    assert "Saint-Maur" in plan["chapters"][0]["text"]
    assert "La Rochelle" in plan["chapters"][0]["text"]


def test_connectors_alternate():
    plan = _raw()
    cons = CONNECTORS["fr"]
    used = []
    for i, ch in enumerate(plan["chapters"]):
        text = ch.get("text") or ""
        hit = next((c for c in cons if text.startswith(f"{c},")), None)
        if hit:
            used.append(hit)
            assert hit == connector_at(i - 1, "fr"), f"chapitre {i}: {hit} ≠ {connector_at(i - 1, 'fr')}"
    assert len(used) >= 2, f"connecteurs : {used}"
    for a, b in zip(used, used[1:]):
        assert a != b, f"connecteur répété : {a}"
    assert connector_at(0, "fr") == "Puis"
    assert connector_at(1, "fr") == "Ensuite"
    assert connector_at(6, "fr") == "Puis"


def test_raw_english_chapter1():
    plan = build_raw_script(CLOCK, CLOCK["marks"], LIVE, JOURNAL, lang="en", seconds=150, now_ms=NOW_MS)
    text = plan["chapters"][0]["text"]
    assert "Saint-Maur" in text
    assert "La Rochelle" in text
    assert ("left" in text.lower() or "departed" in text.lower())
    assert "quitté" not in text


def test_selection_deterministic():
    packed = film_candidates(JOURNAL, CLOCK["marks"], CLOCK, LIVE, NOW_MS)
    a = [e["id"] for e in select_film_events(packed["candidates"], packed["t0"], packed["tEnd"])]
    b = [e["id"] for e in select_film_events(packed["candidates"], packed["t0"], packed["tEnd"])]
    assert a == b
    assert "depart" in a and "today" in a
    assert 6 <= len(a) <= 9
    assert any(i.startswith("wx") for i in a)


def _honest_written(raw: dict, events: list[dict]) -> str:
    pad = " La mer reste la mer, le vent reste le vent, la route reste la route."
    chunks = []
    for ch in raw["chapters"]:
        bits = [ch.get("text") or ""]
        for ev in ch.get("events") or []:
            bits.append(f"[[ev:{ev['id']}]]")
        chunks.append(" ".join(bits))
    body = " ".join(chunks)
    for ev in events:
        if f"[[ev:{ev['id']}]]" not in body:
            body = f"[[ev:{ev['id']}]] " + body
    while len(body.replace("[[ev:", "").replace("]]", "")) < FILM_WRITE_MIN:
        body += pad
    # Keep visible length in range (tags don't count the same after strip — pad then trim display).
    from film_script import strip_tags
    while len(strip_tags(body)) < FILM_WRITE_MIN:
        body += pad
    display = strip_tags(body)
    if len(display) > FILM_WRITE_MAX:
        overflow = len(display) - FILM_WRITE_MAX
        body = body[: max(0, len(body) - overflow)]
        # Ensure tags still present after a tail trim: re-append missing tags then re-pad carefully.
        for ev in events:
            tag = f"[[ev:{ev['id']}]]"
            if tag not in body:
                body = tag + " " + body
        while len(strip_tags(body)) < FILM_WRITE_MIN:
            body += pad
        display = strip_tags(body)
        if len(display) > FILM_WRITE_MAX:
            # cut padding only
            body = body[: len(body) - (len(display) - FILM_WRITE_MAX)]
    return body


def test_written_valid_when_tags_and_length_and_no_new_number():
    raw = _raw()
    events = raw["_events"]
    facts = film_facts(raw, events)
    text = _honest_written(raw, events)
    ok, _, dropped = written_is_valid(text, facts, [e["id"] for e in events])
    assert dropped == 0
    assert ok, f"len={len(text)} stripped invalid"


def test_cheating_llm_falls_back_to_raw():
    raw = _raw()
    events = raw["_events"]
    facts = film_facts(raw, events)
    cheat = _honest_written(raw, events) + " Le vent atteindra 99 nœuds demain."
    ok, _, dropped = written_is_valid(cheat, facts, [e["id"] for e in events])
    assert dropped >= 1
    assert ok is False

    async def fake_cascade(system, user, **kw):
        if "JSON only" in system or "ids" in system.lower() and "select" in system.lower():
            return '{"ids":["depart"],"reason":"too few"}', "nemotron-lightning"
        return cheat, "nemotron-super"

    async def run():
        return await build_film_response(
            CLOCK, LIVE, JOURNAL, lang="fr", seconds=150, style="written",
            now_ms=NOW_MS, cascade=fake_cascade, want_write=True,
        )

    out = asyncio.run(run())
    assert out["source"] == "rules"
    assert out["style"] == "raw"
    assert "99" not in " ".join(c["text"] for c in out["chapters"])
    assert out["hasWritten"] is False


def test_honest_llm_keeps_tags_and_length():
    raw = _raw()
    events = raw["_events"]
    honest = _honest_written(raw, events)

    async def fake_cascade(system, user, **kw):
        if "select" in system.lower() or "JSON only" in system:
            ids = [e["id"] for e in events]
            return json_ids(ids), "nemotron-lightning"
        return honest, "nemotron-super"

    async def run():
        return await build_film_response(
            CLOCK, LIVE, JOURNAL, lang="fr", seconds=150, style="written",
            now_ms=NOW_MS, cascade=fake_cascade, want_write=True,
        )

    out = asyncio.run(run())
    assert out["source"] in {"nemotron", "nemotron-super"}
    assert FILM_WRITE_MIN <= out["chars"] <= FILM_WRITE_MAX
    assert out["hasWritten"] is True


def json_ids(ids):
    import json
    return json.dumps({"ids": ids, "reason": "rules-shaped pick"})


def test_film_cache_hit_skips_second_write():
    raw = _raw()
    events = raw["_events"]
    honest = _honest_written(raw, events)
    calls = {"n": 0}

    async def fake_cascade(system, user, **kw):
        calls["n"] += 1
        if "JSON only" in system:
            return json_ids([e["id"] for e in events]), "nemotron-lightning"
        return honest, "nemotron-super"

    async def run():
        a = await build_film_response(
            CLOCK, LIVE, JOURNAL, lang="fr", seconds=150, style="written",
            now_ms=NOW_MS, cascade=fake_cascade, want_write=True,
        )
        n1 = calls["n"]
        b = await build_film_response(
            CLOCK, LIVE, JOURNAL, lang="fr", seconds=150, style="written",
            now_ms=NOW_MS, cascade=fake_cascade, want_write=True,
        )
        return a, b, n1, calls["n"]

    a, b, n1, n2 = asyncio.run(run())
    assert a["chapters"][0]["text"] == b["chapters"][0]["text"]
    assert n2 == n1, "second call served from ns film"
    key = story_cache.film_cache_key(journal_fingerprint(JOURNAL, last_stop_id(JOURNAL, CLOCK["marks"])), "fr", 150)
    assert story_cache.get_film_cached(key)
    assert pearl_store.kv_count("film") >= 1


def test_new_stop_changes_fingerprint():
    a = journal_fingerprint(JOURNAL, "stop:Ajaccio")
    extra = {"latest": JOURNAL["latest"] + [
        {"id": "stop:noumea:arrival", "kind": "stop", "t": "2026-09-17T22:48:00Z", "event": "arrival", "name": "Nouméa"},
    ]}
    b = journal_fingerprint(extra, "stop:noumea:arrival")
    assert a != b


def test_http_film_route_raw(monkeypatch):
    from fastapi.testclient import TestClient
    import voyage_api
    from main import app

    monkeypatch.setattr(voyage_api, "_now", lambda: datetime(2026, 9, 19, 2, 0, tzinfo=timezone.utc))
    client = TestClient(app)
    body = _official()
    body["t0"] = OFFICIAL_T0
    client.put("/voyage/official", json=body, headers=PUBLIC)
    r = client.get("/voyage/official/film?lang=fr&seconds=150", headers=PUBLIC)
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "rules"
    assert data["chapters"]
    assert "targetSeconds" in data
    assert data["chars"] <= FILM_MAX_CHARS


def test_http_film_route_en(monkeypatch):
    from fastapi.testclient import TestClient
    import voyage_api
    from main import app

    monkeypatch.setattr(voyage_api, "_now", lambda: datetime(2026, 9, 19, 2, 0, tzinfo=timezone.utc))
    client = TestClient(app)
    body = _official()
    body["t0"] = OFFICIAL_T0
    client.put("/voyage/official", json=body, headers=PUBLIC)
    r = client.get("/voyage/official/film?lang=en&seconds=150", headers=PUBLIC)
    assert r.status_code == 200
    data = r.json()
    assert data["chapters"]
    text = data["chapters"][0]["text"]
    if "Saint-Maur" in text:
        assert "La Rochelle" in text
        assert ("left" in text.lower() or "departed" in text.lower())
