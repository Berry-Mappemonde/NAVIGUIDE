"""Lot F3 — script du film : longueur, balises, aucun nombre nouveau, cache, sélection."""
import asyncio
import re
from datetime import datetime, timezone

import pearl_store
import story_cache
from film_script import (
    CONNECTORS,
    FILM_BUDGET_CHARS,
    FILM_CHAPTER_MAX_CHANGES,
    FILM_MAX_CHARS,
    FILM_WRITE_MAX,
    FILM_WRITE_MIN,
    allocate_chapter_budgets,
    bubble_score,
    build_film_response,
    build_raw_script,
    connector_at,
    dated_marks,
    film_candidates,
    film_facts,
    is_sea_chapter,
    journal_fingerprint,
    last_stop_id,
    norm_stop,
    official_dated_stops,
    select_chapter_changes,
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
    assert pearl_store.kv_count("film-story") >= 1


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
    assert "Saint-Maur" in data["chapters"][0]["text"]
    assert "15 mai 2026" in data["chapters"][0]["text"]
    assert "2027" not in data["chapters"][0]["text"]
    assert not re.search(r"\bnm\b", " ".join(c.get("text") or "" for c in data["chapters"]))
    assert "targetSeconds" in data
    assert data["chars"] <= FILM_MAX_CHARS
    sea = [c for c in data["chapters"] if is_sea_chapter(c)]
    for ch in sea:
        evs = ch.get("events") or []
        assert evs, f"chapitre de mer sans événement : {ch.get('id')}"
        assert all(e.get("score") in {1, 2, 3} for e in evs)


def test_bubble_scores_are_one_two_or_three():
    assert bubble_score({"kind": "stop", "event": "arrival"}) == 3
    assert bubble_score({"kind": "stop", "event": "departure"}) == 3
    assert bubble_score({"kind": "zee", "event": "enter"}) == 2
    assert bubble_score({"kind": "sci"}) == 2
    assert bubble_score({"kind": "amp"}) == 1
    assert bubble_score({"kind": "climo"}) == 1
    assert bubble_score({"kind": "wx", "maxWindKnots": 38}) == 3
    assert bubble_score({"kind": "wx", "hs": 3.2}) == 3
    assert bubble_score({"kind": "wx", "windKnots": 20, "hs": 1.2}) is None
    assert bubble_score({"kind": "wx", "maxWindKnots": 30}, wind_max_kt=28) == 3


def test_official_sea_chapters_have_scored_events():
    plan = _raw()
    sea = [c for c in plan["chapters"] if is_sea_chapter(c)]
    assert sea, "le voyage officiel a des chapitres de mer"
    for ch in sea:
        evs = ch.get("events") or []
        assert evs, f"chapitre de mer sans événement : {ch.get('id')} {ch.get('fromName')} → {ch.get('toName')}"
        for e in evs:
            assert e.get("score") in {1, 2, 3}, e
            assert "charIdx" in e
            assert e.get("kind")
            assert e.get("title") is not None
            assert e.get("fact") is not None


ROUTE_STOPS = ["Saint-Maur", "La Rochelle", "Ajaccio", "Fort-de-France", "Nouméa"]


def _first_index(text: str, needle: str) -> int:
    return text.lower().find(needle.lower())


def _assert_route_order(text: str, label: str) -> None:
    hits = [(n, _first_index(text, n)) for n in ROUTE_STOPS if _first_index(text, n) >= 0]
    assert len(hits) >= 4, f"{label} : escales manquantes ({[n for n, _ in hits]})"
    for (a, ia), (b, ib) in zip(hits, hits[1:]):
        assert ia < ib, f"{label} : {b} avant {a}"


def _assert_departure_arrival_pairs(text: str, lang: str = "fr") -> None:
    import re
    dep_re = r"departure for (.+?)(?:\s*:|\.|$)" if lang == "en" else r"départ vers (.+?)(?:\s*:|\.|$)"
    arr_re = r"Arrival at (.+?) on " if lang == "en" else r"Arrivée à (.+?) le "
    deps = [(m.group(1).strip(), m.start()) for m in re.finditer(dep_re, text, re.I)]
    arrs = [(m.group(1).strip(), m.start()) for m in re.finditer(arr_re, text, re.I)]
    assert len(deps) >= 2, f"départs vers : {[n for n, _ in deps]}"
    assert len(arrs) >= 2, f"arrivées : {[n for n, _ in arrs]}"
    seen = []
    for name, _ in arrs:
        key = norm_stop(name)
        assert key not in seen, f"escale répétée : {name}"
        seen.append(key)
    for name, i in deps:
        nxt = next(((n, j) for n, j in arrs if j > i), None)
        assert nxt, f"pas d’arrivée après départ vers {name}"
        assert norm_stop(nxt[0]) == norm_stop(name), f"départ vers {name} suivi de arrivée à {nxt[0]}"
    assert not re.search(r"départ vers Fort-de-France[\s\S]{0,240}(?:Escale à|Arrivée à) Ajaccio", text, re.I)
    assert not re.search(r"departure for Fort-de-France[\s\S]{0,240}(?:Stopover in|Arrival at) Ajaccio", text, re.I)


def test_dated_marks_merges_ajaccio_aliases():
    extra = CLOCK["marks"] + [
        {"name": "Ajaccio", "nm": 1820, "filmNm": 1942.3, "iso": "2026-05-24T13:00:00Z", "holdHours": 72},
        {"name": "Ajaccio (Corse)", "nm": 9000, "filmNm": 9000, "iso": "2026-07-01T00:00:00Z", "holdHours": 0},
    ]
    dated = dated_marks(extra)
    assert sum(1 for s in dated if "ajaccio" in s["name"].lower()) == 1
    assert norm_stop("Ajaccio (Corse)") == "ajaccio"


def test_dated_marks_keeps_distinct_stops_at_filmnm_zero():
    dated = dated_marks([
        {"name": "Saint-Maur (Berry, Indre)", "nm": 0, "filmNm": 0, "iso": OFFICIAL_T0},
        {"name": "La Rochelle", "nm": 0, "filmNm": 0, "iso": OFFICIAL_T0},
        {"name": "Ajaccio (Corse)", "nm": 1820, "filmNm": 1942, "iso": "2026-05-24T12:51:00Z"},
    ])
    keys = [norm_stop(s["name"]) for s in dated]
    assert "saint-maur" in keys
    assert "la rochelle" in keys
    assert "ajaccio" in keys


def _live_like_clock(lr: dict) -> dict:
    return {
        "t0": OFFICIAL_T0,
        "marks": [CLOCK["marks"][0], lr, *CLOCK["marks"][2:]],
    }


def _assert_no_rochelle_to_ajaccio_skip(blob: str) -> None:
    assert "Arrivée à La Rochelle" in blob, blob[:500]
    assert "départ vers Ajaccio" in blob, blob[:500]
    assert blob.find("Arrivée à La Rochelle") < blob.find("départ vers Ajaccio"), blob[:800]
    assert not re.search(r"vers La Rochelle[^.]*\.\s*Arrivée à Ajaccio", blob)
    _assert_departure_arrival_pairs(blob, "fr")


def test_live_like_clock_pairs_rochelle_before_ajaccio():
    """La Rochelle iso = T0 ou filmNm 0 : Arrivée à La Rochelle avant départ vers Ajaccio."""
    variants = (
        {"name": "La Rochelle", "nm": 0, "filmNm": 0, "iso": OFFICIAL_T0, "holdHours": 72, "lat": 46.15, "lon": -1.16},
        {"name": "La Rochelle", "nm": 0, "filmNm": 122, "iso": OFFICIAL_T0, "holdHours": 72, "lat": 46.15, "lon": -1.16},
    )
    for lr in variants:
        clock = _live_like_clock(lr)
        for journal in (JOURNAL, {**JOURNAL, **MOMENTS}):
            plan = build_raw_script(clock, clock["marks"], LIVE, journal, lang="fr", seconds=150, now_ms=NOW_MS)
            blob = _script_blob(plan)
            _assert_no_rochelle_to_ajaccio_skip(blob)
            ch0 = plan["chapters"][0]["text"]
            assert re.search(r"départ vers La Rochelle", ch0, re.I), ch0
            assert re.search(r"Arrivée à La Rochelle", ch0), ch0


def test_official_route_order_no_repeat_departure_then_arrival():
    fr = _raw()
    blob_fr = " ".join(c.get("text") or "" for c in fr["chapters"])
    _assert_route_order(blob_fr, "film FR")
    _assert_departure_arrival_pairs(blob_fr, "fr")
    for ch in fr["chapters"]:
        text = ch.get("text") or ""
        if "départ vers" in text and "Arrivée à" in text:
            import re
            dep = re.search(r"départ vers (.+?)(?:\s*:|\.|$)", text)
            arr = re.search(r"Arrivée à (.+?) le ", text)
            assert dep and arr
            assert norm_stop(dep.group(1)) == norm_stop(arr.group(1)), ch.get("id")

    en = build_raw_script(CLOCK, CLOCK["marks"], LIVE, JOURNAL, lang="en", seconds=150, now_ms=NOW_MS)
    blob_en = " ".join(c.get("text") or "" for c in en["chapters"])
    _assert_route_order(blob_en, "film EN")
    _assert_departure_arrival_pairs(blob_en, "en")


SIM_CLOCK = {
    "t0": "2027-04-25T08:00:00Z",
    "marks": [
        {"name": "La Rochelle", "nm": 0, "filmNm": 122, "iso": "2027-04-25T08:00:00Z", "holdHours": 72, "lat": 46.15, "lon": -1.16},
        {"name": "Ajaccio (Corse)", "nm": 1820, "filmNm": 1942, "iso": "2027-05-04T12:00:00Z", "holdHours": 72, "lat": 41.9, "lon": 8.7},
        {"name": "Fort-de-France (Martinique)", "nm": 6973, "filmNm": 7095, "iso": "2027-06-02T08:00:00Z", "holdHours": 72, "lat": 14.6, "lon": -61.0},
    ],
}


def _script_blob(plan: dict) -> str:
    return " ".join(c.get("text") or "" for c in (plan.get("chapters") or []))


def test_official_script_ignores_simulation_clock():
    plan = build_raw_script(SIM_CLOCK, SIM_CLOCK["marks"], LIVE, JOURNAL, lang="fr", seconds=150, now_ms=NOW_MS)
    assert plan["chapters"]
    text0 = plan["chapters"][0]["text"]
    assert "Saint-Maur" in text0
    assert "15 mai 2026" in text0
    assert "La Rochelle" in text0
    assert "2027" not in text0
    assert "25 avril" not in text0
    assert not re.search(r"a quitté La Rochelle", text0, re.I)
    blob = _script_blob(plan)
    assert not re.search(r"\bnm\b", blob), blob


def test_no_bare_nm_in_official_script():
    fr = _raw()
    en = build_raw_script(CLOCK, CLOCK["marks"], LIVE, JOURNAL, lang="en", seconds=150, now_ms=NOW_MS)
    blob_fr = _script_blob(fr)
    blob_en = _script_blob(en)
    assert "Saint-Maur" in fr["chapters"][0]["text"]
    assert "15 mai 2026" in fr["chapters"][0]["text"]
    assert not re.search(r"\bnm\b", blob_fr), blob_fr
    assert not re.search(r"\bnm\b", blob_en), blob_en
    if re.search(r"\d[\d\s]*", blob_fr) and "départ" in blob_fr.lower():
        assert "milles nautiques" in blob_fr or "mille nautique" in blob_fr or "Aujourd" in blob_fr
    assert "nautical mile" in blob_en or "Today" in blob_en or "left" in blob_en.lower()


def test_official_dated_stops_pins_saint_maur():
    stops = official_dated_stops(SIM_CLOCK["marks"], SIM_CLOCK)
    assert is_saint_or_first(stops)
    assert stops[0]["iso"].startswith("2026-05-15")


def test_official_dated_stops_pins_first_rochelle_not_return():
    """La Rochelle départ (filmNm 122) ne doit pas hériter de l'iso du retour."""
    marks = [
        {"name": "Saint-Maur (Berry, Indre)", "nm": 0, "filmNm": 0, "iso": None},
        {"name": "La Rochelle", "nm": 122, "filmNm": 122, "iso": "2027-05-10T02:40:39Z", "holdHours": 72},
        {"name": "Ajaccio (Corse)", "nm": 1942, "filmNm": 1942, "iso": "2026-05-30T13:56:06Z", "holdHours": 72},
        {"name": "Fort-de-France (Martinique)", "nm": 7095, "filmNm": 7095, "iso": "2026-07-10T23:11:45Z", "holdHours": 72},
    ]
    stops = official_dated_stops(marks)
    assert is_saint_or_first(stops)
    assert "rochelle" in stops[1]["name"].lower()
    assert stops[1]["iso"].startswith("2026-05-15")
    assert "ajaccio" in stops[2]["name"].lower()
    clock = {"t0": OFFICIAL_T0, "marks": marks}
    plan = build_raw_script(clock, marks, LIVE, JOURNAL, lang="fr", seconds=150, now_ms=NOW_MS)
    blob = _script_blob(plan)
    _assert_no_rochelle_to_ajaccio_skip(blob)


def is_saint_or_first(stops):
    assert stops
    assert "saint-maur" in stops[0]["name"].lower().replace(" ", "-")
    return True


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
    blob = _script_blob(data)
    if "Saint-Maur" in text:
        assert ("left" in text.lower() or "departed" in text.lower())
    deps = list(re.finditer(r"departure for (.+?)(?:\s*:|\.|$)", blob, re.I))
    arrs = list(re.finditer(r"Arrival at (.+?) on ", blob, re.I))
    if len(deps) >= 2:
        _assert_departure_arrival_pairs(blob, "en")
    elif deps and arrs:
        assert norm_stop(deps[0].group(1)) == norm_stop(arrs[0].group(1))


MOMENTS = {
    "moments": [
        {"seq": 0, "t": "2026-05-15T08:00:00Z", "signature": "s0", "legIdx": 0, "changes": [],
         "moment": {"leg": {"from": "Saint-Maur", "to": "La Rochelle"}}},
        {"seq": 1, "t": "2026-05-15T11:30:00Z", "signature": "s1", "legIdx": 0, "changes": [
            {"kind": "approche", "score": 3, "title": "La Rochelle", "fact": "Approche de La Rochelle, reste 12 milles nautiques."},
        ], "moment": {"leg": {"from": "Saint-Maur", "to": "La Rochelle"}}},
        {"seq": 2, "t": "2026-05-15T12:00:00Z", "signature": "s2", "legIdx": 0, "changes": [
            {"kind": "escale", "score": 3, "title": "Arrivée à La Rochelle", "fact": "Saint-Maur → La Rochelle"},
        ], "moment": {"leg": {"from": "Saint-Maur", "to": "La Rochelle"}}},
        {"seq": 3, "t": "2026-05-17T15:00:00Z", "signature": "s3", "legIdx": 1, "changes": [
            {"kind": "zee-enter", "score": 2, "title": "Spanish Exclusive Economic Zone", "fact": "Spanish Exclusive Economic Zone"},
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)"}}},
        {"seq": 4, "t": "2026-05-22T06:00:00Z", "signature": "s4", "legIdx": 1, "changes": [
            {"kind": "alert-on", "score": 3, "title": "Vent 38 kn", "fact": "Vent 38 kn attendu pendant 6 heures."},
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)"}}},
        {"seq": 5, "t": "2026-05-24T10:00:00Z", "signature": "s5", "legIdx": 1, "changes": [
            {"kind": "approche", "score": 3, "title": "Ajaccio", "fact": "Approche de Ajaccio, reste 40 milles nautiques."},
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)"}}},
        {"seq": 6, "t": "2026-05-24T12:51:00Z", "signature": "s6", "legIdx": 1, "changes": [
            {"kind": "escale", "score": 3, "title": "Arrivée à Ajaccio", "fact": "La Rochelle → Ajaccio"},
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)"}}},
        {"seq": 7, "t": "2026-06-10T06:00:00Z", "signature": "s7", "legIdx": 2, "changes": [
            {"kind": "station", "score": 2, "title": "PIRATA", "fact": "Station PIRATA à 6 milles nautiques."},
        ], "moment": {"leg": {"from": "Ajaccio (Corse)", "to": "Fort-de-France (Martinique)"}}},
        {"seq": 8, "t": "2026-06-22T12:00:00Z", "signature": "s8", "legIdx": 2, "changes": [
            {"kind": "approche", "score": 3, "title": "Fort-de-France", "fact": "Approche de Fort-de-France, reste 90 milles nautiques."},
        ], "moment": {"leg": {"from": "Ajaccio (Corse)", "to": "Fort-de-France (Martinique)"}}},
        {"seq": 9, "t": "2026-06-23T08:34:00Z", "signature": "s9", "legIdx": 2, "changes": [
            {"kind": "escale", "score": 3, "title": "Arrivée à Fort-de-France", "fact": "Ajaccio → Fort-de-France"},
        ], "moment": {"leg": {"from": "Ajaccio (Corse)", "to": "Fort-de-France (Martinique)"}}},
        {"seq": 10, "t": "2026-08-01T06:00:00Z", "signature": "s10", "legIdx": 3, "changes": [
            {"kind": "amp", "score": 1, "title": "Cabrera", "fact": "Cabrera (8 milles nautiques)"},
        ], "moment": {"leg": {"from": "Fort-de-France (Martinique)", "to": "Nouméa (Nouvelle-Calédonie)"}}},
        {"seq": 11, "t": "2026-09-17T18:00:00Z", "signature": "s11", "legIdx": 3, "changes": [
            {"kind": "approche", "score": 3, "title": "Nouméa", "fact": "Approche de Nouméa, reste 70 milles nautiques."},
        ], "moment": {"leg": {"from": "Fort-de-France (Martinique)", "to": "Nouméa (Nouvelle-Calédonie)"}}},
        {"seq": 12, "t": "2026-09-17T22:48:00Z", "signature": "s12", "legIdx": 3, "changes": [
            {"kind": "escale", "score": 3, "title": "Arrivée à Nouméa", "fact": "Fort-de-France → Nouméa"},
        ], "moment": {"leg": {"from": "Fort-de-France (Martinique)", "to": "Nouméa (Nouvelle-Calédonie)"}}},
    ],
}


def _moments_raw(lang="fr"):
    return build_raw_script(CLOCK, CLOCK["marks"], LIVE, {**JOURNAL, **MOMENTS}, lang=lang, seconds=150, now_ms=NOW_MS)


def test_allocate_budgets_floor_and_total():
    budgets = allocate_chapter_budgets([1, 9, 30, 86], FILM_BUDGET_CHARS, 120)
    assert len(budgets) == 4
    assert all(b >= 120 for b in budgets)
    assert sum(budgets) == FILM_BUDGET_CHARS
    assert budgets[-1] > budgets[0]


def test_moments_raw_length_within_budget():
    plan = _moments_raw()
    lo, hi = int(FILM_BUDGET_CHARS * 0.9), int(FILM_BUDGET_CHARS * 1.1)
    assert lo <= plan["chars"] <= hi
    assert plan["targetSeconds"] == 150
    assert not re.search(r"\bnm\b", " ".join(c.get("text") or "" for c in plan["chapters"]))


def test_moments_chapter_one_sentence_max_three_changes():
    plan = _moments_raw()
    assert plan["chapters"]
    for ch in plan["chapters"]:
        text = (ch.get("text") or "").strip()
        assert text
        assert re.search(r"[.!?]", text)
        changes = [e for e in (ch.get("events") or []) if e.get("kind") != "stop" or "approach" in str(e.get("id") or "").lower() or e.get("card", {}).get("kind") == "stop"]
        assert len(ch.get("events") or []) <= FILM_CHAPTER_MAX_CHANGES + 1  # + arrivée de jambe
        assert len([e for e in (ch.get("events") or []) if e.get("id") and not str(e.get("id")).startswith("stop:")]) <= FILM_CHAPTER_MAX_CHANGES


def test_moments_arrival_each_stop_route_order():
    plan = _moments_raw()
    blob = " ".join(c.get("text") or "" for c in plan["chapters"])
    _assert_route_order(blob, "journal FR")
    _assert_departure_arrival_pairs(blob, "fr")
    for name in ("La Rochelle", "Ajaccio", "Fort-de-France", "Nouméa"):
        assert re.search(rf"Arrivée à {name}", blob), name


def test_moments_connectors_differ():
    plan = _moments_raw()
    starts = []
    for i, ch in enumerate(plan["chapters"]):
        if i == 0:
            continue
        text = ch.get("text") or ""
        hit = next((c for c in CONNECTORS["fr"] if text.startswith(f"{c},")), None)
        if hit:
            starts.append(hit)
    assert len(starts) >= 2
    for a, b in zip(starts, starts[1:]):
        assert a != b


def test_moments_approche_bubble_title_is_stop():
    plan = _moments_raw()
    titles = []
    for ch in plan["chapters"]:
        for ev in ch.get("events") or []:
            eid = str(ev.get("id") or "")
            if "approche" in eid or ev.get("kind") == "stop" and "approche" in str(ev.get("fact") or "").lower():
                titles.append(ev.get("title"))
            if str(ev.get("title") or "") in {"La Rochelle", "Ajaccio", "Fort-de-France", "Nouméa"}:
                titles.append(ev.get("title"))
    assert "Ajaccio" in titles or any(t and "Ajaccio" in t for t in titles)
    for ch in plan["chapters"]:
        dest = (ch.get("toName") or "").split("(")[0].strip()
        if not dest:
            continue
        approach = next(
            (e for e in (ch.get("events") or []) if dest.split()[0] in str(e.get("title") or "")),
            None,
        )
        if approach:
            assert dest.split()[0] in (approach.get("title") or "")


def test_moments_short_sentences_no_cut():
    plan = _moments_raw()
    for ch in plan["chapters"]:
        text = ch.get("text") or ""
        assert text.endswith((".", "!", "?", "…"))
        for sent in re.split(r"(?<=[.!?…])\s+", text):
            if sent.strip():
                assert sent.strip()[-1] in ".!?…"


def test_select_chapter_changes_caps_at_three():
    changes = [
        {"id": "a", "kind": "escale", "score": 3, "tMs": 1, "title": "Arrivée à Ajaccio", "fact": "x"},
        {"id": "b", "kind": "approche", "score": 3, "tMs": 2, "title": "Ajaccio", "fact": "y"},
        {"id": "c", "kind": "alert-on", "score": 3, "tMs": 3, "title": "Vent", "fact": "38 kn"},
        {"id": "d", "kind": "station", "score": 2, "tMs": 4, "title": "PIRATA", "fact": "z"},
        {"id": "e", "kind": "amp", "score": 1, "tMs": 5, "title": "AMP", "fact": "w"},
    ]
    picked = select_chapter_changes(changes, 0, 10)
    assert len(picked) <= 3
    kinds = {c["kind"] for c in picked}
    assert "escale" in kinds
    assert "approche" in kinds or "alert-on" in kinds


def test_written_no_number_outside_facts():
    raw = _moments_raw()
    events = raw.get("_events") or []
    facts = film_facts(raw, events)
    cheat = "Le vent atteindra 99 nœuds demain."
    ok, _, dropped = written_is_valid(cheat, facts, [])
    assert dropped >= 1
    assert ok is False


def test_film_written_served_from_cache_without_llm():
    raw = _raw()
    events = raw["_events"]
    honest = _honest_written(raw, events)
    calls = {"n": 0}

    async def fake_cascade(system, user, **kw):
        calls["n"] += 1
        if "JSON only" in system:
            return json_ids([e["id"] for e in events]), "nemotron-lightning"
        return honest, "nemotron-super"

    async def boom(*_a, **_k):
        calls["n"] += 1
        raise AssertionError("LLM au clic")

    async def run():
        await build_film_response(
            CLOCK, LIVE, JOURNAL, lang="fr", seconds=150, style="written",
            now_ms=NOW_MS, cascade=fake_cascade, want_write=True,
        )
        n1 = calls["n"]
        out = await build_film_response(
            CLOCK, LIVE, JOURNAL, lang="fr", seconds=150, style="written",
            now_ms=NOW_MS, cascade=boom, want_write=False,
        )
        return n1, calls["n"], out

    n1, n2, out = asyncio.run(run())
    assert n1 >= 1
    assert n2 == n1
    assert out["hasWritten"] is True
    assert out["style"] == "written"
