"""Lot F3 — script du film : longueur, balises, aucun nombre nouveau, cache, sélection."""
import asyncio
import re
from datetime import datetime, timezone

import pearl_store
import story_cache
from film_script import (
    OFFICIAL_ROUTE_ZEE_SOURCES,
    chapter_anchors,
    CONNECTORS,
    FILM_BUDGET_CHARS,
    FILM_CHAPTER_MAX_CHANGES,
    FILM_MAX_CHARS,
    FILM_WRITE_MAX,
    FILM_WRITE_MIN,
    SHORT_CROSSING_MS,
    allocate_chapter_budgets,
    alert_is_amp,
    bubble_score,
    build_film_response,
    build_raw_script,
    change_sentence,
    chapter_metrics,
    chapter_shape,
    coast_sentence,
    connector_at,
    cyclone_name_year,
    dated_marks,
    date_density_ok,
    dose_amp_changes,
    dose_climo_changes,
    dose_coast_changes,
    dose_project_changes,
    dose_station_changes,
    dose_zee_changes,
    film_candidates,
    film_facts,
    film_has_forbidden,
    heading_phrase,
    is_sea_chapter,
    journal_fingerprint,
    last_stop_id,
    looks_english_title,
    norm_stop,
    review_leg_for_chapter,
    review_sentences,
    official_dated_stops,
    spoken_sea_days,
    thin_chapter_dates,
    _arrival_harbor,
    _de,
    _ms,
    _nm_between,
    _window_depart_ms,
    _windows,
    warm_film_story,
    select_chapter_changes,
    select_film_events,
    station_name_speakable,
    station_spoken_label,
    speak_film_text,
    written_is_valid,
    zee_waters_label,
    _nm_label,
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
    """RG6 : plus de rotation mécanique ; les formes suivent le contenu."""
    plan = _raw()
    blob = " ".join(c.get("text") or "" for c in plan["chapters"])
    assert "À la jambe suivante" not in blob
    assert "On the next leg" not in blob
    assert connector_at(0, "fr") != "À la jambe suivante"
    long_hit = any("longue traversée" in (c.get("text") or "") for c in plan["chapters"])
    last_hit = any("dernière étape" in (c.get("text") or "") for c in plan["chapters"])
    assert long_hit or last_hit or "Berry-Mappemonde quitte" in blob


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
    import official_store
    official_store.refresh_family("film", force=True)
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


def test_http_film_route_replay_t0(monkeypatch):
    from fastapi.testclient import TestClient
    import voyage_api
    from main import app

    monkeypatch.setattr(voyage_api, "_now", lambda: datetime(2026, 9, 19, 2, 0, tzinfo=timezone.utc))
    client = TestClient(app)
    body = _official()
    body["t0"] = OFFICIAL_T0
    client.put("/voyage/official", json=body, headers=PUBLIC)
    import official_store
    official_store.refresh_family("film", force=True)
    r = client.get(
        "/voyage/official/film?lang=fr&seconds=150&t0=2025-05-15T08:00:00.000Z",
        headers=PUBLIC,
    )
    assert r.status_code == 200
    text0 = r.json()["chapters"][0]["text"]
    assert "Saint-Maur" in text0
    # RF2 : le script stocké est celui du t0 officiel — plus de recalcul à la requête.
    assert "15 mai 2026" in text0


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
    dep_re = (
        r"Berry-Mappemonde leaves .+? for (?:the long crossing to )?(.+?)(?:\s*:|,|\.|$)"
        if lang == "en" else
        r"Berry-Mappemonde quitte .+? pour (?:la longue traversée vers )?(.+?)(?:\s*:|,|\.|$)"
    )
    arr_re = r"Arrival at (.+?) on " if lang == "en" else r"Arrivée à (.+?) le "
    deps = [(m.group(1).strip(), m.start()) for m in re.finditer(dep_re, text, re.I)]
    arrs = [(m.group(1).strip(), m.start()) for m in re.finditer(arr_re, text, re.I)]
    assert len(deps) >= 2, f"départs pour : {[n for n, _ in deps]}"
    assert len(arrs) >= 2, f"arrivées : {[n for n, _ in arrs]}"
    seen = []
    for name, _ in arrs:
        key = norm_stop(name)
        assert key not in seen, f"escale répétée : {name}"
        seen.append(key)
    def _pair_name(name: str) -> str:
        s = re.sub(r"\s+(par la route|by road)\s*$", "", name, flags=re.I)
        s = re.sub(r",\s+(cap au [\w'-]+|heading [\w-]+)\s*$", "", s, flags=re.I)
        return s.strip()

    for name, i in deps:
        nxt = next(((n, j) for n, j in arrs if j > i), None)
        assert nxt, f"pas d’arrivée après départ pour {name}"
        assert norm_stop(_pair_name(nxt[0])) == norm_stop(_pair_name(name)), (
            f"départ pour {name} suivi de arrivée à {nxt[0]}"
        )
    assert not re.search(r"pour Fort-de-France[\s\S]{0,240}(?:Escale à|Arrivée à) Ajaccio", text, re.I)
    assert not re.search(r"for Fort-de-France[\s\S]{0,240}(?:Stopover in|Arrival at) Ajaccio", text, re.I)


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
    assert re.search(r"pour Ajaccio", blob), blob[:500]
    assert blob.find("Arrivée à La Rochelle") < blob.find("pour Ajaccio"), blob[:800]
    assert not re.search(r"pour La Rochelle[^.]*\.\s*Arrivée à Ajaccio", blob)
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
            assert re.search(r"par la route pour La Rochelle|quitte Saint-Maur", ch0, re.I), ch0
            assert re.search(r"Arrivée à La Rochelle", ch0), ch0


def test_chapter_iso_tb_after_ta():
    """Plancher 1 s : après _iso, chaque chapitre a tB > tA (filmPlan garde le ch. 0)."""
    from film_script import _iso, _ms

    plan = _raw()
    assert plan["chapters"]
    for ch in plan["chapters"]:
        ta, tb = _ms(ch["tA"]), _ms(ch["tB"])
        assert ta is not None and tb is not None
        assert tb > ta, (ch.get("id"), ch["tA"], ch["tB"])
        assert _iso(ta) != _iso(tb), (ch.get("id"), ch["tA"], ch["tB"])

    lr = {"name": "La Rochelle", "nm": 0, "filmNm": 0, "iso": OFFICIAL_T0, "holdHours": 72}
    live_plan = build_raw_script(
        _live_like_clock(lr), _live_like_clock(lr)["marks"], LIVE, JOURNAL,
        lang="fr", seconds=150, now_ms=NOW_MS,
    )
    assert live_plan["chapters"]
    assert live_plan["chapters"][0]["id"] == "leg-0"
    for ch in live_plan["chapters"]:
        ta, tb = _ms(ch["tA"]), _ms(ch["tB"])
        assert tb > ta, (ch.get("id"), ch["tA"], ch["tB"])
        assert ch["tA"] != ch["tB"]


def test_official_route_order_no_repeat_departure_then_arrival():
    fr = _raw()
    blob_fr = " ".join(c.get("text") or "" for c in fr["chapters"])
    _assert_route_order(blob_fr, "film FR")
    _assert_departure_arrival_pairs(blob_fr, "fr")
    for ch in fr["chapters"]:
        text = ch.get("text") or ""
        if "Berry-Mappemonde quitte" in text and "Arrivée à" in text:
            import re
            dep = re.search(
                r"Berry-Mappemonde quitte .+? pour (?:la longue traversée vers )?(.+?)(?:\s*:|,|\.|$)",
                text,
            )
            arr = re.search(r"Arrivée à (.+?) le ", text)
            assert dep and arr
            dep_name = re.sub(r",\s+(cap au [\w'-]+|heading [\w-]+)\s*$", "", dep.group(1), flags=re.I)
            assert norm_stop(dep_name) == norm_stop(arr.group(1)), ch.get("id")

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
    if re.search(r"\d[\d\s]*", blob_fr) and "quitte" in blob_fr.lower():
        assert "milles" in blob_fr or "Aujourd" in blob_fr
    assert "miles" in blob_en or "Today" in blob_en or "left" in blob_en.lower() or "leaves" in blob_en.lower()


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
    import official_store
    official_store.refresh_family("film", force=True)
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
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)", "headingDeg": 246}}},
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


FILLER = (
    "Le ciel reste haut", "La mer porte le bateau", "La route tient le cap",
    "Le vent reste le vent", "The sky stays high", "The sea carries the boat",
    "The course holds", "The wind stays the wind", "La mer reste la mer",
    "le vent reste le vent, la route reste la route",
)


def _assert_no_filler(blob: str) -> None:
    for phrase in FILLER:
        assert phrase not in blob, phrase


def test_moments_raw_no_atmos_budget_flag():
    plan = _moments_raw()
    blob = " ".join(c.get("text") or "" for c in plan["chapters"])
    assert plan["targetSeconds"] == 150
    assert plan["chars"] > 0
    assert plan["chars"] <= FILM_MAX_CHARS
    _assert_no_filler(blob)
    assert not re.search(r"\bnm\b", blob)


def test_moments_chapter_one_sentence_max_three_changes():
    plan = _moments_raw()
    assert plan["chapters"]
    for ch in plan["chapters"]:
        text = (ch.get("text") or "").strip()
        assert text
        assert re.search(r"[.!?]", text)
        named = {"zee", "coast"}
        others = [
            e for e in (ch.get("events") or [])
            if e.get("kind") not in named and not str(e.get("id") or "").startswith("stop:")
        ]
        assert len(others) <= FILM_CHAPTER_MAX_CHANGES


def test_moments_anchors_follow_the_route_chronologically():
    """27 sept. : chaque phrase gardée porte l'instant du trajet dont elle parle (ancres), croissant,
    borné au chapitre ; « approche de Fort-de-France » est ancrée à l'instant de l'approche."""
    plan = _moments_raw()
    seen_any = False
    for ch in plan["chapters"]:
        anchors = ch.get("anchors") or []
        t_a, t_b = _parse_iso_ms(ch["tA"]), _parse_iso_ms(ch["tB"])
        last_idx, last_t = -1, None
        for a in anchors:
            seen_any = True
            assert isinstance(a["charIdx"], int) and 0 <= a["charIdx"] < len(ch["text"])
            assert a["charIdx"] > last_idx, "ancres triées et sans doublon"
            t = _parse_iso_ms(a["t"])
            assert t_a <= t <= t_b, "ancre bornée au chapitre"
            assert last_t is None or t >= last_t, "chronologie stricte"
            last_idx, last_t = a["charIdx"], t
        text = ch["text"]
        pos = text.find("approche de Fort-de-France")
        if pos >= 0:
            hit = [a for a in anchors if text[a["charIdx"]:].startswith("Le 22 juin, approche de Fort-de-France")]
            assert hit, "la phrase d'approche a son ancre"
            assert _parse_iso_ms(hit[0]["t"]) == _parse_iso_ms("2026-06-22T12:00:00Z")
    assert seen_any


def _parse_iso_ms(value: str) -> int:
    from datetime import datetime, timezone
    return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc).timestamp() * 1000)


def test_chapter_anchors_unit_sorted_bounded_deduped():
    text = "Départ vers Ajaccio. Le 31 mai, approche d’Ajaccio. Arrivée le 1er juin."
    anchored = [
        ("Arrivée le 1er juin.", 5_000),      # après tB → borné
        ("Le 31 mai, approche d’Ajaccio.", 900),
        ("Départ vers Ajaccio.", -50),        # avant tA → borné
        ("Phrase coupée par le budget.", 500),  # absente du texte → ignorée
        ("Le 31 mai, approche d’Ajaccio.", 950),  # même position → une seule ancre
    ]
    out = chapter_anchors(text, anchored, 0, 2_000, "fr")
    assert [a["charIdx"] for a in out] == [0, text.find("Le 31"), text.find("Arrivée")]
    assert [a["t"] for a in out] == ["1970-01-01T00:00:00Z", "1970-01-01T00:00:00Z", "1970-01-01T00:00:02Z"]


def test_moments_arrival_each_stop_route_order():
    plan = _moments_raw()
    blob = " ".join(c.get("text") or "" for c in plan["chapters"])
    _assert_route_order(blob, "journal FR")
    _assert_departure_arrival_pairs(blob, "fr")
    for name in ("La Rochelle", "Ajaccio", "Fort-de-France", "Nouméa"):
        assert re.search(rf"Arrivée à {name}", blob), name


def test_moments_connectors_differ():
    plan = _moments_raw()
    blob = _script_blob(plan)
    assert "À la jambe suivante" not in blob
    shapes = []
    for ch in plan["chapters"]:
        text = ch.get("text") or ""
        if "longue traversée" in text:
            shapes.append("long")
        elif "d'île en île" in text:
            shapes.append("hop")
        elif "dernière étape" in text:
            shapes.append("last")
        elif "Berry-Mappemonde quitte" in text:
            shapes.append("open")
    assert len(shapes) >= 2


def test_moments_approche_bubble_title_is_stop():
    plan = _moments_raw()
    titles = []
    for ch in plan["chapters"]:
        for ev in ch.get("events") or []:
            eid = str(ev.get("id") or "")
            if "approche" in eid or ev.get("kind") == "stop":
                titles.append(ev.get("title"))
            if str(ev.get("title") or "") in {"La Rochelle", "Ajaccio", "Fort-de-France", "Nouméa"}:
                titles.append(ev.get("title"))
    assert "Ajaccio" in titles or any(t and "Ajaccio" in str(t) for t in titles)
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
    assert len(picked) <= FILM_CHAPTER_MAX_CHANGES   # 4 depuis le 27 sept. (arrivée, fait de mer, marina d'escale, approche)
    kinds = {c["kind"] for c in picked}
    assert "escale" in kinds
    assert "approche" in kinds or "alert-on" in kinds
    assert [c["tMs"] for c in picked] == sorted(c["tMs"] for c in picked)   # dits dans l'ordre du voyage


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


def _rich_journal():
    extra = [
        {"seq": 13, "t": "2026-05-15T11:00:00Z", "signature": "marina", "legIdx": 0, "changes": [],
         "moment": {"leg": {"from": "Saint-Maur", "to": "La Rochelle"},
                    "around": [{"kind": "marina", "title": "Les Minimes", "fact": "Les Minimes (2 nm)",
                                "lat": 46.14, "lon": -1.17}]}},
        {"seq": 14, "t": "2026-05-15T12:10:00Z", "signature": "port", "legIdx": 1, "changes": [
            {"kind": "port", "score": 2, "title": "La Rochelle", "fact": "La Rochelle"},
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)"}}},
        {"seq": 15, "t": "2026-07-10T06:00:00Z", "signature": "irma", "legIdx": 3, "changes": [
            {"kind": "cyclone", "score": 3, "title": "Irma", "fact": "Irma (2017)"},
        ], "moment": {"leg": {"from": "Fort-de-France (Martinique)", "to": "Nouméa (Nouvelle-Calédonie)"}}},
        {"seq": 16, "t": "2026-06-23T08:00:00Z", "signature": "culture", "legIdx": 2, "changes": [
            {"kind": "culture", "score": 1, "title": "Fort Saint-Louis", "fact": "Fort Saint-Louis."},
        ], "moment": {"leg": {"from": "Ajaccio (Corse)", "to": "Fort-de-France (Martinique)"}}},
        {"seq": 17, "t": "2026-07-11T06:00:00Z", "signature": "nameless", "legIdx": 3, "changes": [
            {"kind": "cyclone", "score": 1, "title": "Cyclone", "fact": "3 traces de cyclone ce mois-ci."},
        ], "moment": {"leg": {"from": "Fort-de-France (Martinique)", "to": "Nouméa (Nouvelle-Calédonie)"}}},
    ]
    return {**JOURNAL, "moments": MOMENTS["moments"] + extra}


def _rich_raw(seconds=0, lang="fr"):
    return build_raw_script(
        CLOCK, CLOCK["marks"], LIVE, _rich_journal(), lang=lang, seconds=seconds, now_ms=NOW_MS,
    )


def test_official_script_has_no_atmos_or_pad():
    for plan in (_raw(), _moments_raw(), _rich_raw(0), _rich_raw(150)):
        blob = " ".join(c.get("text") or "" for c in plan["chapters"])
        _assert_no_filler(blob)


def test_rich_moments_without_budget_cites_each_type():
    plan = _rich_raw(0)
    blob = " ".join(c.get("text") or "" for c in plan["chapters"])
    assert plan["targetSeconds"] == 0
    assert "Les Minimes" in blob
    assert "à portée de" not in blob
    assert re.search(r"amarré à la marina Les Minimes|marina Les Minimes", blob)
    assert re.search(r"longe La Rochelle|devant La Rochelle", blob)
    assert re.search(r"aire marine protégée(?: :| ) Cabrera|l'aire marine protégée Cabrera", blob)
    assert re.search(r"une bouée", blob)
    assert "PIRATA" not in blob
    assert "stations scientifiques croisées" not in blob
    assert "Irma" in blob and "2017" in blob
    assert "Fort Saint-Louis" in blob
    assert "traces de cyclone ce mois-ci" not in blob
    assert "marina croisée" not in blob
    assert "station croisée : Station croisée" not in blob
    _assert_no_filler(blob)
    _assert_departure_arrival_pairs(blob, "fr")
    _assert_route_order(blob, "journal riche FR")
    assert not re.search(r"\bnm\b", blob)
    assert not re.search(r"\d+[.,]\d{1,2}(?!\d)", blob)
    assert "1 820 milles" in blob or "1820 milles" in blob


def test_budget_150_reached_and_no_decimals():
    plan = _rich_raw(150)
    blob = " ".join(c.get("text") or "" for c in plan["chapters"])
    assert plan["targetSeconds"] == 150
    _assert_no_filler(blob)
    assert not re.search(r"\d+[.,]\d{1,2}(?!\d)", blob)
    assert not re.search(r"\bnm\b", blob)


def test_spoken_distances_rounded_no_abbrev():
    assert _nm_label(1820.4, "fr") == "1 820 milles nautiques"
    assert _nm_label(1, "fr") == "1 mille nautique"
    spoken = speak_film_text("Approche, reste 12.4 nm.", "fr")
    assert "nm" not in spoken
    assert "12.4" not in spoken
    assert "12 milles nautiques" in spoken


def test_nameless_cyclone_is_silence():
    assert cyclone_name_year({"title": "Cyclone", "fact": "3 traces de cyclone ce mois-ci."}) == ("", "")
    assert cyclone_name_year({"title": "Irma", "fact": "Irma (2017)"}) == ("Irma", "2017")
    assert change_sentence({"kind": "cyclone", "title": "Cyclone", "fact": "3 traces de cyclone ce mois-ci."}, "fr") == ""


REVIEW_GIBRALTAR = {
    "legs": [
        {
            "from": "Ajaccio (Corse)",
            "to": "Fort-de-France (Martinique)",
            "antiShipping": {"score": 0.4, "lanes": ["Gibraltar"]},
            "season": {"galePct": 22, "cyclones": 3, "cells": 4, "missing": 0},
            "flags": [{"kind": "formalities", "names": ["Espagne"]}],
        }
    ]
}


def test_review_sentences_facts_only():
    assert review_sentences(None) == []
    assert review_sentences({}) == []
    assert review_sentences({"from": "Ajaccio", "to": "Fort-de-France"}) == []
    bits = review_sentences(REVIEW_GIBRALTAR["legs"][0], "fr")
    assert any("Gibraltar" in s for s in bits)
    assert any("Saison cyclonique" in s for s in bits)
    assert any("Coup de vent" in s and "22" in s for s in bits)
    assert not any("À surveiller" in s or s == "Alerte." or s.startswith("Couloirs") for s in bits)
    assert any("passe par" in s for s in bits)
    assert review_leg_for_chapter(REVIEW_GIBRALTAR, "Ajaccio", "Fort-de-France")
    assert review_leg_for_chapter(REVIEW_GIBRALTAR, "La Rochelle", "Ajaccio") is None


def test_review_lane_named_in_correct_chapter():
    plan = build_raw_script(
        CLOCK, CLOCK["marks"], LIVE, {**JOURNAL, **MOMENTS},
        lang="fr", seconds=0, now_ms=NOW_MS, review=REVIEW_GIBRALTAR,
    )
    hit = [c for c in plan["chapters"] if "Gibraltar" in (c.get("text") or "")]
    assert len(hit) == 1, [c.get("fromName") for c in plan["chapters"]]
    ch = hit[0]
    assert "Ajaccio" in (ch.get("fromName") or "")
    assert "Fort-de-France" in (ch.get("toName") or "")
    assert "Saison cyclonique" in ch["text"]
    assert "Coup de vent" in ch["text"]
    assert "22" in ch["text"]
    for c in plan["chapters"]:
        if c is not ch:
            assert "Gibraltar" not in (c.get("text") or "")
    _assert_no_filler(" ".join(c.get("text") or "" for c in plan["chapters"]))


def test_review_lane_named_without_moments_journal():
    """Lot RC8 : sans moments, _compose doit encore citer le couloir."""
    plan = build_raw_script(
        CLOCK, CLOCK["marks"], LIVE, JOURNAL,
        lang="fr", seconds=0, now_ms=NOW_MS, review=REVIEW_GIBRALTAR,
    )
    hit = [c for c in plan["chapters"] if "Gibraltar" in (c.get("text") or "")]
    assert len(hit) == 1, [c.get("fromName") for c in plan["chapters"]]
    assert "Ajaccio" in (hit[0].get("fromName") or "")
    assert "Fort-de-France" in (hit[0].get("toName") or "")
    _assert_no_filler(" ".join(c.get("text") or "" for c in plan["chapters"]))


def test_warm_film_story_passes_review_without_clock(monkeypatch):
    """Lot RC8 : le préchauffe envoie review_official à build_film_response."""
    import film_script
    import voyage_store

    voy = {
        "voyageId": "seed-no-clock",
        "t0": OFFICIAL_T0,
        "marks": [
            {"name": "Ajaccio (Corse)", "nm": 1820, "filmNm": 1942},
            {"name": "Fort-de-France (Martinique)", "nm": 6973, "filmNm": 7095},
        ],
        "points": [
            {"lat": 41.92, "lon": 8.74, "cumNm": 1820},
            {"lat": 36.05, "lon": -5.6, "cumNm": 2500},
            {"lat": 14.59, "lon": -61.07, "cumNm": 6973},
        ],
    }
    captured: list = []

    async def fake_build(*_a, **kw):
        captured.append(kw.get("review"))
        return {"hasWritten": False, "chars": 0, "source": "rules"}

    monkeypatch.setattr(film_script, "build_film_response", fake_build)
    monkeypatch.setattr(voyage_store, "load_voyage", lambda _vid: voy)
    monkeypatch.setattr("voyage_api._climo_clock", lambda _v: {
        "t0": OFFICIAL_T0, "vertices": [], "marks": voy["marks"],
    })
    out = asyncio.run(warm_film_story("seed-no-clock", langs=("fr",)))
    assert out["status"] == "ready"
    assert captured and captured[0] is not None
    legs = (captured[0] or {}).get("legs") or []
    assert any("Ajaccio" in (leg.get("from") or "") and "Fort-de-France" in (leg.get("to") or "") for leg in legs)
    pack = next(
        (leg.get("antiShipping") or {}) for leg in legs
        if "Ajaccio" in (leg.get("from") or "")
    )
    assert "Gibraltar" in (pack.get("lanes") or [])


def test_review_unknown_fields_are_silence():
    empty = {"legs": [{"from": "Ajaccio (Corse)", "to": "Fort-de-France (Martinique)"}]}
    plan = build_raw_script(
        CLOCK, CLOCK["marks"], LIVE, {**JOURNAL, **MOMENTS},
        lang="fr", seconds=0, now_ms=NOW_MS, review=empty,
    )
    blob = " ".join(c.get("text") or "" for c in plan["chapters"])
    assert "Gibraltar" not in blob
    assert "Saison cyclonique" not in blob
    assert "Couloirs" not in blob
    assert "À surveiller" not in blob
    _assert_no_filler(blob)


def test_select_chapter_changes_unlimited_without_budget():
    changes = [
        {"id": "a", "kind": "escale", "score": 3, "tMs": 1, "title": "Arrivée à Ajaccio", "fact": "x"},
        {"id": "b", "kind": "approche", "score": 3, "tMs": 2, "title": "Ajaccio", "fact": "y"},
        {"id": "c", "kind": "alert-on", "score": 3, "tMs": 3, "title": "Vent", "fact": "38 kn"},
        {"id": "d", "kind": "station", "score": 2, "tMs": 4, "title": "PIRATA", "fact": "z"},
        {"id": "e", "kind": "amp", "score": 1, "tMs": 5, "title": "Cabrera", "fact": "Cabrera"},
        {"id": "f", "kind": "marina", "score": 2, "tMs": 6, "title": "Les Minimes", "fact": "Les Minimes"},
        {"id": "g", "kind": "cyclone", "score": 3, "tMs": 7, "title": "Irma", "fact": "Irma (2017)"},
        {"id": "h", "kind": "culture", "score": 1, "tMs": 8, "title": "Fort Saint-Louis", "fact": "Fort Saint-Louis."},
        {"id": "i", "kind": "marina", "score": 2, "tMs": 9, "title": "Les Minimes", "fact": "Les Minimes encore"},
        {"id": "j", "kind": "station", "score": 2, "tMs": 10, "title": "Station croisée", "fact": "Station croisée"},
    ]
    picked = select_chapter_changes(changes, 0, 10, budget=False)
    names = [c.get("title") for c in picked]
    assert names.count("Les Minimes") == 1
    assert not any(
        (c.get("title") or "").casefold() == "station croisée" for c in picked
    )
    assert {c["kind"] for c in picked} >= {"marina", "cyclone", "culture", "amp", "station"}


RE7_CLOCK = {
    "t0": OFFICIAL_T0,
    "marks": [
        {"name": "Saint-Maur (Berry, Indre)", "nm": 0, "filmNm": 0, "iso": "2026-05-15T08:00:00Z", "holdHours": 0, "lat": 46.8, "lon": 1.6},
        {"name": "La Rochelle", "nm": 122, "filmNm": 122, "iso": "2026-05-15T12:00:00Z", "holdHours": 72, "lat": 46.15, "lon": -1.16},
        {"name": "Cayenne (Guyane)", "nm": 4000, "filmNm": 4000, "iso": "2026-07-01T08:00:00Z", "holdHours": 24, "lat": 4.9, "lon": -52.3},
        {"name": "Halifax (Nouvelle-Écosse)", "nm": 4000, "filmNm": 4100, "iso": "2026-07-02T08:00:00Z", "holdHours": 24, "lat": 44.6, "lon": -63.6},
        {"name": "Nouméa (Nouvelle-Calédonie)", "nm": 19055, "filmNm": 19177, "iso": "2026-09-17T22:48:00Z", "holdHours": 72, "lat": -22.2, "lon": 166.4},
    ],
}
RE7_LIVE = {
    "filmNm": 19400, "sailNm": 19260, "iso": "2026-09-19T02:00:00Z",
    "status": "live", "fromStop": "Nouméa",
}
RE7_REVIEW = {
    "legs": [
        {
            "from": "La Rochelle",
            "to": "Cayenne (Guyane)",
            "antiShipping": {"score": 0.4, "lanes": ["Bay of Biscay", "Gibraltar"]},
            "season": {"galePct": 18, "cyclones": 0, "cells": 2, "missing": 0},
        }
    ]
}


def _re7_journal():
    moments = [
        {"seq": 0, "t": "2026-05-15T08:00:00Z", "signature": "s0", "legIdx": 0, "changes": [],
         "moment": {"leg": {"from": "Saint-Maur", "to": "La Rochelle"}}},
        {"seq": 1, "t": "2026-05-15T12:00:00Z", "signature": "s1", "legIdx": 0, "changes": [
            {"kind": "escale", "score": 3, "title": "Arrivée à La Rochelle", "fact": "Saint-Maur → La Rochelle"},
        ], "moment": {"leg": {"from": "Saint-Maur", "to": "La Rochelle"}}},
        {"seq": 2, "t": "2026-05-16T09:00:00Z", "signature": "s2", "legIdx": 1, "changes": [
            {"kind": "zee-enter", "score": 2, "title": "Entrée dans Zone économique exclusive espagnole",
             "fact": "Entrée dans Zone économique exclusive espagnole"},
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Cayenne (Guyane)"}}},
        {"seq": 3, "t": "2026-05-16T10:00:00Z", "signature": "s3", "legIdx": 1, "changes": [
            {"kind": "marina", "score": 2, "title": "Gran Roque", "fact": "Gran Roque (2 nm)"},
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Cayenne (Guyane)"}}},
        {"seq": 4, "t": "2026-05-16T11:00:00Z", "signature": "s4", "legIdx": 1, "changes": [
            {"kind": "marina", "score": 2, "title": "Gran Roque", "fact": "Gran Roque (2 nm)", "id": "gr2"},
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Cayenne (Guyane)"}}},
        {"seq": 5, "t": "2026-05-16T12:00:00Z", "signature": "s5", "legIdx": 1, "changes": [
            {"kind": "marina", "score": 2, "title": "Gran Roque", "fact": "Gran Roque encore", "id": "gr3"},
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Cayenne (Guyane)"}}},
        {"seq": 6, "t": "2026-05-16T13:00:00Z", "signature": "s6", "legIdx": 1, "changes": [
            {"kind": "station", "score": 2, "title": "Station croisée", "fact": "Station croisée"},
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Cayenne (Guyane)"}}},
        {"seq": 7, "t": "2026-05-16T14:00:00Z", "signature": "s7", "legIdx": 1, "changes": [
            {"kind": "zee-enter", "score": 2, "title": "Ports d'entrée : Les Sables-d'Olonne",
             "fact": "Les Sables-d'Olonne"},
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Cayenne (Guyane)"}}},
        {"seq": 8, "t": "2026-05-16T15:00:00Z", "signature": "s8", "legIdx": 1, "changes": [
            {"kind": "zee-enter", "score": 2, "title": "Formalités d'entrée",
             "fact": "Aucun port d'entrée officiel n'est connu pour cette ZEE."},
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Cayenne (Guyane)"}}},
        {"seq": 9, "t": "2026-05-16T16:00:00Z", "signature": "s9", "legIdx": 1, "changes": [
            {"kind": "marina", "score": 1, "title": "Monaco", "fact": "Monaco (80 nm)", "nm": 80},
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Cayenne (Guyane)"}}},
        {"seq": 10, "t": "2026-07-01T08:00:00Z", "signature": "s10", "legIdx": 2, "changes": [
            {"kind": "escale", "score": 3, "title": "Arrivée à Cayenne", "fact": "La Rochelle → Cayenne"},
        ], "moment": {"leg": {"from": "La Rochelle", "to": "Cayenne (Guyane)"}}},
        {"seq": 11, "t": "2026-07-01T10:00:00Z", "signature": "s11", "legIdx": 2, "changes": [],
         "moment": {"leg": {"from": "Cayenne (Guyane)", "to": "Halifax (Nouvelle-Écosse)", "vehicle": "plane"}}},
        {"seq": 12, "t": "2026-07-02T08:00:00Z", "signature": "s12", "legIdx": 3, "changes": [
            {"kind": "escale", "score": 3, "title": "Arrivée à Halifax", "fact": "Cayenne → Halifax"},
        ], "moment": {"leg": {"from": "Cayenne (Guyane)", "to": "Halifax (Nouvelle-Écosse)", "vehicle": "plane"}}},
        {"seq": 13, "t": "2026-07-03T10:00:00Z", "signature": "s13", "legIdx": 3, "changes": [],
         "moment": {"leg": {"from": "Halifax (Nouvelle-Écosse)", "to": "Cayenne (Guyane)", "vehicle": "plane"}}},
        {"seq": 14, "t": "2026-07-10T06:00:00Z", "signature": "s14", "legIdx": 4, "changes": [
            {"kind": "cyclone", "score": 3, "title": "Irma", "fact": "Irma (2017)"},
        ], "moment": {"leg": {"from": "Halifax (Nouvelle-Écosse)", "to": "Nouméa (Nouvelle-Calédonie)"}}},
        {"seq": 15, "t": "2026-07-11T06:00:00Z", "signature": "s15", "legIdx": 4, "changes": [
            {"kind": "cyclone", "score": 1, "title": "Cyclone", "fact": "3 traces de cyclone ce mois-ci."},
        ], "moment": {"leg": {"from": "Halifax (Nouvelle-Écosse)", "to": "Nouméa (Nouvelle-Calédonie)"}}},
        {"seq": 16, "t": "2026-08-01T06:00:00Z", "signature": "s16", "legIdx": 4, "changes": [
            {"kind": "amp", "score": 1, "title": "Cabrera (IUCN Unassigned)", "fact": "Cabrera (IUCN Unassigned)"},
        ], "moment": {"leg": {"from": "Halifax (Nouvelle-Écosse)", "to": "Nouméa (Nouvelle-Calédonie)"}}},
        {"seq": 17, "t": "2026-08-02T06:00:00Z", "signature": "s17", "legIdx": 4, "changes": [
            {"kind": "station", "score": 2, "title": "PIRATA", "fact": "Station PIRATA à 6 milles nautiques."},
        ], "moment": {"leg": {"from": "Halifax (Nouvelle-Écosse)", "to": "Nouméa (Nouvelle-Calédonie)"}}},
        {"seq": 18, "t": "2026-08-03T06:00:00Z", "signature": "s18", "legIdx": 4, "changes": [
            {"kind": "culture", "score": 1, "title": "Fort Saint-Louis", "fact": "Fort Saint-Louis."},
        ], "moment": {"leg": {"from": "Halifax (Nouvelle-Écosse)", "to": "Nouméa (Nouvelle-Calédonie)"}}},
        {"seq": 19, "t": "2026-09-17T22:48:00Z", "signature": "s19", "legIdx": 4, "changes": [
            {"kind": "escale", "score": 3, "title": "Arrivée à Nouméa", "fact": "Halifax → Nouméa"},
        ], "moment": {"leg": {"from": "Halifax (Nouvelle-Écosse)", "to": "Nouméa (Nouvelle-Calédonie)"}}},
    ]
    return {"moments": moments, "latest": []}


def test_re7_discourse_eleven_defects():
    from film_script import script_words

    plan = build_raw_script(
        RE7_CLOCK, RE7_CLOCK["marks"], RE7_LIVE, _re7_journal(),
        lang="fr", seconds=0, now_ms=NOW_MS, review=RE7_REVIEW,
    )
    blob = _script_blob(plan)
    assert plan["targetSeconds"] == 0
    assert script_words(plan["chapters"]) <= 800
    assert "station croisée : Station croisée" not in blob
    assert "Aucun port d'entrée" not in blob
    assert "entrée dans Entrée dans" not in blob
    assert "IUCN" not in blob
    # RG6 : marina de route tues ; seule la marina d'escale est nommée à l'arrivée.
    assert "Gran Roque" not in blob
    assert "Monaco" not in blob
    assert re.search(r"s'envole de Cayenne pour Halifax", blob)
    assert re.search(r"le bateau attend à Cayenne", blob)
    assert re.search(r"Aujourd’hui, le bateau est à Nouméa", blob)
    assert "Irma" in blob and "2017" in blob
    assert "une bouée" in blob
    assert "PIRATA" not in blob
    assert "stations scientifiques croisées" not in blob
    assert "Cabrera" in blob
    assert "Fort Saint-Louis" in blob
    assert "golfe de Gascogne" in blob
    assert "détroit de Gibraltar" in blob
    assert "Bay of Biscay" not in blob
    assert re.search(r"eaux espagnoles", blob)
    idx_zee = blob.find("eaux espagnoles")
    idx_dep = blob.find("pour Cayenne")
    if idx_dep < 0:
        idx_dep = blob.find("quitte")
    assert 0 <= idx_dep < idx_zee
    _assert_no_filler(blob)
    assert not re.search(r"\bnm\b", blob)


def _rf5_air_marks_no_halifax_iso():
    marks = []
    for m in RE7_CLOCK["marks"]:
        row = dict(m)
        if "Halifax" in row["name"]:
            row.pop("iso", None)
            row.pop("vehicle", None)
        marks.append(row)
    return marks


def test_rf5_air_survives_tight_budget():
    """Lot RF5 : jambe avion aller + retour, budget 150 s et 108 s."""
    for seconds in (150, 108):
        plan = build_raw_script(
            RE7_CLOCK, RE7_CLOCK["marks"], RE7_LIVE, _re7_journal(),
            lang="fr", seconds=seconds, now_ms=NOW_MS, review=RE7_REVIEW,
        )
        blob = _script_blob(plan)
        assert plan["targetSeconds"] == seconds
        assert re.search(r"s'envole de Cayenne pour Halifax", blob), blob
        assert re.search(r"le bateau attend à Cayenne", blob), blob
        _assert_no_filler(blob)


def test_rf5_air_when_halifax_has_no_iso():
    """Arrivée avion sans iso (hors clock_marks) : Cayenne nommée ne suffit pas — l'avion reste dit."""
    marks = _rf5_air_marks_no_halifax_iso()
    clock = {**RE7_CLOCK, "marks": marks}
    plan = build_raw_script(clock, marks, RE7_LIVE, None, lang="fr", seconds=0, now_ms=NOW_MS)
    blob = _script_blob(plan)
    assert "Cayenne" in blob
    assert re.search(r"s'envole de Cayenne pour Halifax", blob), blob
    assert re.search(r"le bateau attend à Cayenne", blob), blob
    assert "avion pour Nouméa" not in blob
    _assert_no_filler(blob)


def test_rf5_air_return_without_moments():
    """Sans moments, dated_marks dédoublonne Cayenne : le retour avion doit quand même être dit."""
    plan = build_raw_script(
        RE7_CLOCK, RE7_CLOCK["marks"], RE7_LIVE, None,
        lang="fr", seconds=150, now_ms=NOW_MS,
    )
    blob = _script_blob(plan)
    assert re.search(r"s'envole de Cayenne pour Halifax", blob), blob
    assert re.search(r"le bateau attend à Cayenne", blob), blob
    assert "avion pour Nouméa" not in blob
    _assert_no_filler(blob)


def test_rf5_no_air_invented_on_ajaccio_route():
    """Route sans Cayenne/Halifax : pas de phrase d'avion inventée."""
    plan = build_raw_script(CLOCK, CLOCK["marks"], LIVE, JOURNAL, lang="fr", seconds=0, now_ms=NOW_MS)
    blob = _script_blob(plan)
    assert "Cayenne" not in blob
    assert "Halifax" not in blob
    assert not re.search(r"prend l'avion|retour en avion|s'envole|flies to|return flight|the boat waits", blob)


def test_rg1_road_phrase_on_first_chapter():
    plan = build_raw_script(CLOCK, CLOCK["marks"], LIVE, JOURNAL, lang="fr", seconds=0, now_ms=NOW_MS)
    ch0 = plan["chapters"][0]["text"]
    assert re.search(r"par la route", ch0, re.I), ch0
    assert re.search(r"La Rochelle", ch0), ch0


def test_rg1_depart_ms_is_clock_leave_not_hold():
    """Écart nul quand l'horloge quitte à tA — jamais tA + 3 jours d'escale."""
    t_a = _ms(OFFICIAL_T0)
    t_end = _ms("2026-09-19T02:00:00Z")
    lr = {
        "name": "La Rochelle", "iso": OFFICIAL_T0, "holdHours": 72,
        "lat": 46.15, "lon": -1.16, "filmNm": 122, "nm": 0,
    }
    aj = {
        "name": "Ajaccio (Corse)", "iso": "2026-05-24T12:00:00Z", "holdHours": 72,
        "lat": 41.9, "lon": 8.7, "filmNm": 1942, "nm": 1820,
    }
    clock = {
        "t0": OFFICIAL_T0,
        "marks": [lr, aj],
        "vertices": [
            {"iso": OFFICIAL_T0, "lat": 46.20, "lon": -1.16, "vehicle": "main"},
        ],
    }
    windows = _windows([lr, aj], t_a, t_end, clock)
    sail = next(w for w in windows if "ajaccio" in (w.get("destName") or "").lower())
    assert _window_depart_ms(sail) == t_a
    bare = _windows([lr, aj], t_a, t_end, {"t0": OFFICIAL_T0, "vertices": [], "marks": [lr, aj]})
    sail_bare = next(w for w in bare if "ajaccio" in (w.get("destName") or "").lower())
    assert _window_depart_ms(sail_bare) == t_a
    hold_ms = 72 * 3_600_000
    assert _window_depart_ms(sail_bare) != t_a + hold_ms


def test_rg1_air_window_not_told_as_navigation():
    marks = [
        {"name": "Saint-Maur (Berry, Indre)", "nm": 0, "filmNm": 0, "iso": OFFICIAL_T0, "holdHours": 0, "lat": 46.8, "lon": 1.6},
        {"name": "La Rochelle", "nm": 122, "filmNm": 122, "iso": "2026-05-15T12:00:00Z", "holdHours": 0, "lat": 46.15, "lon": -1.16},
        {"name": "Cayenne (Guyane)", "nm": 4000, "filmNm": 4000, "iso": "2026-07-19T08:00:00Z", "holdHours": 72, "lat": 4.93, "lon": -52.33},
        {"name": "Saint-Pierre (Saint-Pierre-et-Miquelon)", "nm": 4100, "filmNm": 4100, "iso": "2026-07-25T08:00:00Z", "holdHours": 72, "lat": 46.78, "lon": -56.18},
        {"name": "Papeete (Polynésie française)", "nm": 11000, "filmNm": 11100, "iso": "2026-09-08T08:00:00Z", "holdHours": 72, "lat": -17.5, "lon": -149.5},
    ]
    clock = {"t0": OFFICIAL_T0, "marks": marks, "vertices": [
        {"iso": "2026-07-19T08:00:00Z", "lat": 4.93, "lon": -52.33, "vehicle": "quay"},
        {"iso": "2026-07-22T08:00:00Z", "lat": 46.78, "lon": -56.18, "vehicle": "plane"},
        {"iso": "2026-07-25T18:00:00Z", "lat": 4.93, "lon": -52.33, "vehicle": "plane"},
        {"iso": "2026-07-28T08:00:00Z", "lat": 4.80, "lon": -52.50, "vehicle": "main"},
    ]}
    live = {"filmNm": 12000, "sailNm": 11800, "iso": "2026-09-19T02:00:00Z", "status": "live"}
    journal = {
        "moments": [
            {"seq": 0, "t": "2026-07-23T08:00:00Z", "changes": [
                {"kind": "zee-enter", "score": 2, "title": "Entrée dans Zone économique exclusive canadienne",
                 "fact": "Entrée dans Zone économique exclusive canadienne"},
            ], "moment": {"leg": {"from": "Cayenne (Guyane)", "to": "Saint-Pierre (Saint-Pierre-et-Miquelon)"}}},
            {"seq": 1, "t": "2026-07-25T06:00:00Z", "changes": [
                {"kind": "approche", "score": 3, "title": "Saint-Pierre", "fact": "Approche de Saint-Pierre"},
            ], "moment": {"leg": {"from": "Cayenne (Guyane)", "to": "Saint-Pierre (Saint-Pierre-et-Miquelon)"}}},
            {"seq": 2, "t": "2026-07-25T08:00:00Z", "changes": [
                {"kind": "escale", "score": 3, "title": "Arrivée à Saint-Pierre", "fact": "Cayenne → Saint-Pierre"},
            ], "moment": {"leg": {"from": "Cayenne (Guyane)", "to": "Saint-Pierre (Saint-Pierre-et-Miquelon)"}}},
            {"seq": 3, "t": "2026-07-28T09:00:00Z", "changes": [
                {"kind": "zee-enter", "score": 2, "title": "Entrée dans Zone économique exclusive du Panama",
                 "fact": "Entrée dans Zone économique exclusive du Panama"},
            ], "moment": {"leg": {"from": "Cayenne (Guyane)", "to": "Papeete (Polynésie française)"}}},
        ],
        "latest": [],
    }
    plan = build_raw_script(clock, marks, live, journal, lang="fr", seconds=0, now_ms=NOW_MS)
    blob = _script_blob(plan)
    assert re.search(r"s'envole de Cayenne pour Saint-Pierre-et-Miquelon", blob), blob
    assert re.search(r"le bateau attend à Cayenne", blob), blob
    assert not re.search(r"départ vers Saint-Pierre", blob), blob
    assert not re.search(r"Berry-Mappemonde quitte Cayenne.{0,80}pour Saint-Pierre", blob), blob
    assert not re.search(r"approche de Saint-Pierre", blob, re.I), blob
    assert not re.search(r"Arrivée à Saint-Pierre", blob), blob
    assert not re.search(r"eaux canadiennes", blob), blob
    next_sail = next(
        c for c in plan["chapters"]
        if re.search(r"pour Papeete|quitte Cayenne", c.get("text") or "")
    )
    assert "Cayenne" in (next_sail.get("fromName") or "")
    assert "Saint-Pierre" not in (next_sail.get("fromName") or "")


def test_rg1_depart_anchor_stays_at_port():
    t_end = _ms("2026-09-19T02:00:00Z")
    lr = {
        "name": "La Rochelle", "iso": "2026-05-15T12:00:00Z", "holdHours": 72,
        "lat": 46.15, "lon": -1.16, "filmNm": 122, "nm": 0,
    }
    aj = {
        "name": "Ajaccio (Corse)", "iso": "2026-05-24T12:00:00Z", "holdHours": 72,
        "lat": 41.9, "lon": 8.7, "filmNm": 1942, "nm": 1820,
    }
    leave_iso = "2026-05-15T13:00:00Z"
    clock = {
        "t0": OFFICIAL_T0,
        "marks": [CLOCK["marks"][0], lr, aj],
        "vertices": [
            {"iso": "2026-05-15T12:00:00Z", "lat": 46.15, "lon": -1.16, "vehicle": "main"},
            {"iso": leave_iso, "lat": 46.15, "lon": -1.24, "vehicle": "main"},
        ],
    }
    live = {"filmNm": 2000, "sailNm": 1900, "iso": "2026-05-25T00:00:00Z", "status": "live"}
    plan = build_raw_script(clock, clock["marks"], live, None, lang="fr", seconds=0, now_ms=t_end)
    ch = next(
        c for c in plan["chapters"]
        if re.search(r"pour Ajaccio|quitte La Rochelle", c.get("text") or "")
    )
    anchors = ch.get("anchors") or []
    assert anchors, ch
    text = ch.get("text") or ""
    depart_anchor = next(
        a for a in anchors
        if re.search(r"Ajaccio|La Rochelle", text[max(0, int(a.get("charIdx") or 0)):])
    )
    t_anchor = _ms(depart_anchor["t"])
    vert = min(
        clock["vertices"],
        key=lambda v: abs((_ms(v["iso"]) or 0) - (t_anchor or 0)),
    )
    d = _nm_between(46.15, -1.16, vert["lat"], vert["lon"])
    assert d is not None and d <= 5.0, (d, depart_anchor, vert)


def test_official_route_zee_all_have_spoken_names():
    """Toute ZEE de la route officielle a un nom parlé, sans jargon de source."""
    for src in OFFICIAL_ROUTE_ZEE_SOURCES:
        spoken = zee_waters_label(src, "fr")
        assert spoken, f"pas de nom parlé pour {src!r}"
        assert "zone économique exclusive" not in spoken.lower(), (src, spoken)
        assert "exclusive economic" not in spoken.lower(), (src, spoken)
        en = zee_waters_label(src, "en")
        assert en, f"no spoken EN name for {src!r}"
        assert "exclusive economic" not in en.lower(), (src, en)


def test_zee_haute_mer_and_sahara_spoken():
    assert zee_waters_label("Haute mer", "fr") == "haute mer"
    assert zee_waters_label("High Seas", "en") == "the high seas"
    assert "disputées du Sahara occidental" in zee_waters_label(
        "Overlapping claim Western Sahara: Western Sahara / Morocco", "fr",
    )
    assert "Barbade" in zee_waters_label("Zone économique exclusive (Barbadian)", "fr") or (
        "barbadiennes" in zee_waters_label("Zone économique exclusive (Barbadian)", "fr")
    )
    assert "vénézuéliennes" in zee_waters_label("Zone économique exclusive vénézuélienne", "fr")
    assert "indiennes" in zee_waters_label(
        "Zone économique exclusive indienne (Andaman and Nicobar Islands)", "fr",
    )


def test_heading_phrase_eight_directions():
    assert heading_phrase(246, "fr") == "cap au sud-ouest"
    assert heading_phrase(0, "fr") == "cap au nord"
    assert heading_phrase(90, "fr") == "cap à l'est"
    assert heading_phrase(270, "fr") == "cap à l'ouest"
    assert heading_phrase(90, "en") == "heading east"
    assert heading_phrase(None, "fr") == ""


def test_zee_dosage_short_keeps_all_long_one_per_day():
    day = 86_400_000
    short = [
        {"id": "a", "kind": "zee-enter", "tMs": 1, "t": "2026-07-01T08:00:00Z",
         "title": "Antiguan and Barbudan Exclusive Economic Zone", "fact": "x", "score": 2},
        {"id": "b", "kind": "zee-enter", "tMs": 2, "t": "2026-07-01T14:00:00Z",
         "title": "Kittitian and Nevisian Exclusive Economic Zone", "fact": "y", "score": 2},
        {"id": "c", "kind": "zee-enter", "tMs": 3, "t": "2026-07-01T20:00:00Z",
         "title": "Sint-Eustatius Exclusive Economic Zone", "fact": "z", "score": 2},
    ]
    for i, c in enumerate(short):
        c["tMs"] = _ms(c["t"])
    clustered = dose_zee_changes(short, span_ms=2 * day)
    assert len(clustered) == 1
    sent = change_sentence(clustered[0], "fr")
    assert "Antigua" in sent and "Saint-Kitts" in sent and "Sint-Eustatius" in sent
    assert "zones économiques exclusives" not in sent
    assert "zone économique exclusive" not in sent
    it_fr = [
        {"id": "it", "kind": "zee-enter", "tMs": _ms("2026-05-24T22:04:29Z"),
         "t": "2026-05-24T22:04:29Z", "title": "Zone économique exclusive italienne",
         "fact": "Zone économique exclusive italienne", "score": 2},
        {"id": "fr", "kind": "zee-enter", "tMs": _ms("2026-05-25T21:27:29Z"),
         "t": "2026-05-25T21:27:29Z", "title": "Zone économique exclusive française (France métropolitaine)",
         "fact": "Zone économique exclusive française (France métropolitaine)", "score": 2},
    ]
    it_fr_c = dose_zee_changes(it_fr, span_ms=2 * day)
    assert len(it_fr_c) == 1
    it_sent = change_sentence(it_fr_c[0], "fr")
    assert "les eaux" in it_sent and "italiennes" in it_sent and "françaises" in it_sent

    long_span = 10 * day
    long_zee = [
        {"id": f"z{i}", "kind": "zee-enter", "score": 2,
         "title": title, "fact": title,
         "t": t, "tMs": _ms(t)}
        for i, (title, t) in enumerate((
            ("Spanish Exclusive Economic Zone", "2026-05-16T08:00:00Z"),
            ("Portuguese Exclusive Economic Zone", "2026-05-18T08:00:00Z"),
            ("Moroccan Exclusive Economic Zone", "2026-05-21T08:00:00Z"),
            ("Italian Exclusive Economic Zone", "2026-05-24T08:00:00Z"),
            ("French Exclusive Economic Zone", "2026-05-25T08:00:00Z"),
        ))
    ]
    dosed = dose_zee_changes(long_zee, span_ms=long_span)
    assert len(dosed) == 5
    same_day = [
        {**long_zee[0], "id": "extra", "t": "2026-05-16T20:00:00Z", "tMs": _ms("2026-05-16T20:00:00Z"),
         "title": "Portuguese Exclusive Economic Zone"},
    ]
    one_day = dose_zee_changes([long_zee[0], same_day[0]], span_ms=long_span)
    assert len(one_day) == 1


def test_zee_named_in_date_order_no_count():
    t0 = _ms("2026-05-15T08:00:00Z")
    changes = [
        {"id": "es", "kind": "zee-enter", "score": 2, "tMs": _ms("2026-05-16T08:00:00Z"),
         "t": "2026-05-16T08:00:00Z", "title": "Spanish Exclusive Economic Zone",
         "fact": "Spanish Exclusive Economic Zone"},
        {"id": "pt", "kind": "zee-enter", "score": 2, "tMs": _ms("2026-05-18T08:00:00Z"),
         "t": "2026-05-18T08:00:00Z", "title": "Portuguese Exclusive Economic Zone",
         "fact": "Portuguese Exclusive Economic Zone"},
        {"id": "ma", "kind": "zee-enter", "score": 2, "tMs": _ms("2026-05-21T08:00:00Z"),
         "t": "2026-05-21T08:00:00Z", "title": "Moroccan Exclusive Economic Zone",
         "fact": "Moroccan Exclusive Economic Zone"},
        {"id": "arr", "kind": "escale", "score": 3, "tMs": _ms("2026-05-26T08:00:00Z"),
         "t": "2026-05-26T08:00:00Z", "title": "Arrivée à Ajaccio", "fact": "x"},
    ]
    picked = select_chapter_changes(changes, t0, _ms("2026-05-26T12:00:00Z"), budget=True)
    kinds = [c["kind"] for c in picked]
    assert kinds.count("zee-enter") >= 3
    texts = [change_sentence(c, "fr") for c in picked if c["kind"] == "zee-enter"]
    blob = " ".join(texts)
    assert blob.find("espagnoles") < blob.find("portugaises") < blob.find("marocaines")
    assert "zones économiques exclusives" not in blob
    assert "zone économique exclusive" not in blob


def test_coast_milestones_ordered_by_route():
    t0 = _ms("2026-05-15T08:00:00Z")
    coasts = [
        {"id": "cam", "kind": "coast", "score": 2, "tMs": _ms("2026-05-16T12:00:00Z"),
         "t": "2026-05-16T12:00:00Z", "title": "Camariñas", "fact": "Camariñas (4 nm)"},
        {"id": "mux", "kind": "coast", "score": 2, "tMs": _ms("2026-05-16T14:00:00Z"),
         "t": "2026-05-16T14:00:00Z", "title": "Muxía", "fact": "Muxía (3 nm)"},
        {"id": "tan", "kind": "coast", "score": 2, "tMs": _ms("2026-05-21T08:00:00Z"),
         "t": "2026-05-21T08:00:00Z", "title": "Tanger", "fact": "Tanger (2 nm)"},
        {"id": "alg", "kind": "coast", "score": 2, "tMs": _ms("2026-05-21T09:00:00Z"),
         "t": "2026-05-21T09:00:00Z", "title": "Algeciras", "fact": "Algeciras (3 nm)"},
        {"id": "ptt", "kind": "coast", "score": 2, "tMs": _ms("2026-05-24T10:00:00Z"),
         "t": "2026-05-24T10:00:00Z", "title": "Porto Torres", "fact": "Porto Torres (5 nm)"},
    ]
    dosed = dose_coast_changes(coasts, span_ms=11 * 86_400_000)
    assert [ _utc_day_from(c) for c in dosed ] == sorted(_utc_day_from(c) for c in dosed)
    galice = next(c for c in dosed if "Camariñas" in (c.get("title") or "") or "Galice" in (c.get("title") or ""))
    sent = coast_sentence(galice, "fr")
    assert "Galice" in sent
    assert "Camariñas" in sent and "Muxía" in sent
    gib = next(c for c in dosed if any(p in (c.get("title") or "") or p in " ".join(c.get("ports") or [])
                                        for p in ("Tanger", "Algeciras", "Gibraltar")))
    gsent = coast_sentence(gib, "fr")
    assert "Gibraltar" in gsent
    assert "Tanger" in gsent and "Algeciras" in gsent
    sar = next(c for c in dosed if "Porto Torres" in (c.get("title") or "") or "Sardaigne" in (c.get("title") or ""))
    assert "Sardaigne" in coast_sentence(sar, "fr")
    picked = select_chapter_changes(coasts, t0, _ms("2026-05-26T12:00:00Z"), budget=True)
    coast_picked = [c for c in picked if c.get("kind") == "coast"]
    assert len(coast_picked) >= 3
    times = [c.get("tMs") or 0 for c in coast_picked]
    assert times == sorted(times)


def test_stock_ports_and_marinas_become_named_coasts():
    """Les 44 ports et les marinas du stock (Camariñas, Tanger…) sont des jalons, pas un comptage."""
    t0 = _ms("2026-05-15T08:00:00Z")
    changes = [
        {"id": "cam", "kind": "marina", "score": 2, "tMs": _ms("2026-05-18T11:42:00Z"),
         "t": "2026-05-18T11:42:00Z", "title": "Club Náutico de Camariñas",
         "fact": "Club Náutico de Camariñas (4 nm)"},
        {"id": "mux", "kind": "marina", "score": 2, "tMs": _ms("2026-05-18T12:42:00Z"),
         "t": "2026-05-18T12:42:00Z", "title": "Porto de Muxía", "fact": "Porto de Muxía (3 nm)"},
        {"id": "tan", "kind": "port", "score": 2, "tMs": _ms("2026-05-21T14:37:58Z"),
         "t": "2026-05-21T14:37:58Z", "title": "Tanger", "fact": "Tanger"},
        {"id": "alg", "kind": "port", "score": 2, "tMs": _ms("2026-05-21T19:05:47Z"),
         "t": "2026-05-21T19:05:47Z", "title": "Algeciras", "fact": "Algeciras"},
        {"id": "ptt", "kind": "port", "score": 2, "tMs": _ms("2026-05-25T15:48:38Z"),
         "t": "2026-05-25T15:48:38Z", "title": "Porto Torres", "fact": "Porto Torres"},
    ]
    dosed = dose_coast_changes(changes, span_ms=11 * 86_400_000)
    blob = " ".join(coast_sentence(c, "fr") for c in dosed)
    assert "zone économique exclusive" not in blob
    assert "Galice" in blob and "Camariñas" in blob and "Muxía" in blob
    assert "Gibraltar" in blob and "Tanger" in blob and "Algeciras" in blob
    assert "Sardaigne" in blob and "Porto Torres" in blob
    picked = select_chapter_changes(changes, t0, _ms("2026-05-26T12:00:00Z"), budget=True)
    assert [c.get("kind") for c in picked if c.get("kind") == "coast"]
    times = [c.get("tMs") or 0 for c in picked if c.get("kind") == "coast"]
    assert times == sorted(times)


def _utc_day_from(change: dict) -> str:
    from film_script import _utc_day
    return _utc_day(change)


def test_rg2_film_names_route_and_heading():
    journal = {
        "moments": [
            {"seq": 0, "t": "2026-05-15T08:00:00Z", "signature": "s0", "legIdx": 0, "changes": [],
             "moment": {"leg": {"from": "Saint-Maur", "to": "La Rochelle"}}},
            {"seq": 1, "t": "2026-05-15T12:00:00Z", "signature": "s1", "legIdx": 0, "changes": [
                {"kind": "escale", "score": 3, "title": "Arrivée à La Rochelle", "fact": "x"},
            ], "moment": {"leg": {"from": "Saint-Maur", "to": "La Rochelle"}}},
            {"seq": 2, "t": "2026-05-15T13:00:00Z", "signature": "s2", "legIdx": 1, "changes": [],
             "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)", "headingDeg": 246}}},
            {"seq": 3, "t": "2026-05-16T08:00:00Z", "signature": "s3", "legIdx": 1, "changes": [
                {"kind": "zee-enter", "score": 2, "title": "Spanish Exclusive Economic Zone",
                 "fact": "Spanish Exclusive Economic Zone"},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)", "headingDeg": 246}}},
            {"seq": 4, "t": "2026-05-16T12:00:00Z", "signature": "s4", "legIdx": 1, "changes": [
                {"kind": "coast", "score": 2, "title": "Camariñas", "fact": "Camariñas (4 nm)"},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)", "headingDeg": 240}}},
            {"seq": 5, "t": "2026-05-16T14:00:00Z", "signature": "s5", "legIdx": 1, "changes": [
                {"kind": "coast", "score": 2, "title": "Muxía", "fact": "Muxía (3 nm)"},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)", "headingDeg": 240}}},
            {"seq": 6, "t": "2026-05-18T08:00:00Z", "signature": "s6", "legIdx": 1, "changes": [
                {"kind": "zee-enter", "score": 2, "title": "Portuguese Exclusive Economic Zone",
                 "fact": "Portuguese Exclusive Economic Zone"},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)", "headingDeg": 180}}},
            {"seq": 7, "t": "2026-05-21T08:00:00Z", "signature": "s7", "legIdx": 1, "changes": [
                {"kind": "zee-enter", "score": 2, "title": "Moroccan Exclusive Economic Zone",
                 "fact": "Moroccan Exclusive Economic Zone"},
                {"kind": "coast", "score": 2, "title": "Tanger", "fact": "Tanger (2 nm)"},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)", "headingDeg": 90}}},
            {"seq": 8, "t": "2026-05-21T09:00:00Z", "signature": "s8", "legIdx": 1, "changes": [
                {"kind": "coast", "score": 2, "title": "Algeciras", "fact": "Algeciras (3 nm)"},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)", "headingDeg": 90}}},
            {"seq": 9, "t": "2026-05-24T10:00:00Z", "signature": "s9", "legIdx": 1, "changes": [
                {"kind": "zee-enter", "score": 2, "title": "Italian Exclusive Economic Zone",
                 "fact": "Italian Exclusive Economic Zone"},
                {"kind": "coast", "score": 2, "title": "Porto Torres", "fact": "Porto Torres (5 nm)"},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)", "headingDeg": 45}}},
            {"seq": 10, "t": "2026-05-25T08:00:00Z", "signature": "s10", "legIdx": 1, "changes": [
                {"kind": "zee-enter", "score": 2, "title": "French Exclusive Economic Zone",
                 "fact": "French Exclusive Economic Zone"},
                {"kind": "coast", "score": 2, "title": "Calvi", "fact": "Calvi (6 nm)"},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)", "headingDeg": 20}}},
            {"seq": 11, "t": "2026-05-24T12:51:00Z", "signature": "s11", "legIdx": 1, "changes": [
                {"kind": "escale", "score": 3, "title": "Arrivée à Ajaccio", "fact": "x"},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)"}}},
        ],
        "latest": [],
    }
    plan = build_raw_script(CLOCK, CLOCK["marks"], LIVE, journal, lang="fr", seconds=0, now_ms=NOW_MS)
    blob = _script_blob(plan)
    assert "zone économique exclusive" not in blob.lower()
    assert "zones économiques exclusives" not in blob
    assert blob.find("espagnoles") < blob.find("portugaises") < blob.find("marocaines")
    assert "Galice" in blob
    assert "Gibraltar" in blob
    assert "Sardaigne" in blob or "Corse" in blob
    assert "cap au sud-ouest" in blob


def test_chaluts_never_spoken_as_amp():
    fishing = {
        "kind": "amp", "score": 1, "title": "Pertuis Charentais - Chaluts",
        "fact": "Pertuis Charentais - Chaluts (2 nm): IUCN Unassigned.",
    }
    alert = {
        "kind": "alert-on", "score": 3, "title": "Aire marine protégée",
        "fact": "Pertuis Charentais - Pétoncles - Center Pertuis Breton deposit (3 nm): IUCN Unassigned.",
    }
    assert change_sentence(fishing, "fr") == ""
    assert not alert_is_amp(alert)
    assert "Pétoncles" not in change_sentence(alert, "fr")
    assert "deposit" not in change_sentence(alert, "fr").lower()
    real = {
        "kind": "amp", "score": 1, "title": "Pertuis charentais - Rochebonne",
        "fact": "Pertuis charentais - Rochebonne (12 nm)", "nm": 12,
    }
    sent = change_sentence(real, "fr")
    assert "Rochebonne" in sent
    assert "douze milles" in sent
    assert "Pétoncles" not in sent


def test_project_sentence_and_dosage():
    near = {
        "kind": "project", "score": 1, "title": "Récif sentinelle",
        "fact": "Récif sentinelle (10 nm)", "nm": 10, "gold_on": True,
    }
    sent = change_sentence(near, "fr")
    assert "le projet Récif sentinelle" in sent
    assert "dix milles" in sent
    far = {**near, "id": "far", "nm": 60, "title": "Loin", "fact": "Loin (60 nm)"}
    from film_script import change_is_speakable, change_on_route
    assert change_on_route(near)
    assert not change_on_route(far)
    short_span = SHORT_CROSSING_MS - 1
    many = [
        {**near, "id": f"p{i}", "title": f"Projet {i}", "fact": f"Projet {i} (1 nm)",
         "nm": 1 + i, "gold_on": i == 2, "tMs": i}
        for i in range(5)
    ]
    assert len(dose_project_changes(many, short_span)) == 1
    assert dose_project_changes(many, short_span)[0]["gold_on"] is True
    long_span = 12 * 86_400_000
    assert len(dose_project_changes(many, long_span)) == 3
    amps = [
        {"kind": "amp", "id": f"a{i}", "title": f"Réserve {i}", "fact": f"Réserve {i} ({i} nm)",
         "nm": i + 1, "tMs": i}
        for i in range(5)
    ]
    assert len(dose_amp_changes(amps, short_span)) == 1
    assert len(dose_amp_changes(amps, long_span)) == 3
    assert dose_amp_changes(amps, short_span)[0]["nm"] == 1


def test_climo_sentence_and_dosage():
    atlas = {
        "kind": "climo", "id": "climo:ne", "event": "ne_trades", "regimeId": "ne_trades",
        "t": "2026-06-14T12:00:00Z", "tMs": _ms("2026-06-14T12:00:00Z"),
        "source": "atlas", "nature": "season", "windKnots": 15,
        "placeFr": "au sud du Cap-Vert", "placeEn": "south of Cape Verde",
        "title": "alizés de nord-est", "fact": "alizés de nord-est",
    }
    fr = change_sentence(atlas, "fr")
    en = change_sentence(atlas, "en")
    assert "alizés de nord-est" in fr
    assert "quinze nœuds de saison" in fr
    assert "northeasterly trade winds" in en
    assert "fifteen seasonal knots" in en
    zone = {
        **atlas, "id": "climo:zone", "source": "zone_fallback", "nature": "zone",
        "windKnots": None, "dirFromDeg": None,
    }
    zfr = change_sentence(zone, "fr")
    assert "vents moyens de saison" in zfr
    assert "quinze" not in zfr
    assert not re.search(r"\d+\s*n", zfr)
    many = [
        {**atlas, "id": f"c{i}", "tMs": i, "event": "ne_trades" if i < 2 else "force",
         "regimeId": "ne_trades" if i < 2 else None}
        for i in range(5)
    ]
    assert len(dose_climo_changes(many, SHORT_CROSSING_MS - 1)) == 1
    assert len(dose_climo_changes(many, 20 * 86_400_000)) == 2
    picked = select_chapter_changes(many, 0, 20 * 86_400_000, budget=True)
    assert sum(1 for c in picked if c.get("kind") == "climo") <= 2


def test_rg5_dataset_title_never_spoken():
    assert not station_name_speakable("Bacteria in Rias of Galicia")
    silent = {
        "kind": "station",
        "title": "Bacteria in Rias of Galicia",
        "fact": "Bacteria in Rias of Galicia (2 nm)",
        "t": "2026-05-16T12:00:00Z",
    }
    assert change_sentence(silent, "fr") == ""
    assert change_sentence(silent, "en") == ""
    assert "Bacteria" not in (change_sentence(silent, "fr") or "")


def test_rg5_argo_speaks_type_not_wmo():
    ch = {
        "kind": "station",
        "title": "Argo 6904216",
        "fact": "Argo 6904216 (4 nm)",
        "t": "2026-05-18T12:00:00Z",
        "source": "argo",
    }
    fr = change_sentence(ch, "fr")
    en = change_sentence(ch, "en")
    assert fr == "Le 18 mai, un flotteur Argo."
    assert en == "On 18 May, an Argo float."
    assert "6904216" not in fr
    assert "6904216" not in en
    assert station_spoken_label(ch, "fr") == "un flotteur Argo"
    assert station_name_speakable("Argo 6904216")


def test_rg5_named_types_from_title_words():
    assert station_spoken_label({"kind": "station", "title": "PELGAS2025"}, "fr") == "la campagne PELGAS"
    assert station_spoken_label({"kind": "station", "title": "PELGAS2025"}, "en") == "the PELGAS campaign"
    assert station_spoken_label({"kind": "station", "title": "Wave buoy 12"}, "fr") == "une bouée"
    assert station_spoken_label({"kind": "station", "title": "CTD and nutrients sections"}, "fr") == "une station côtière"
    assert station_spoken_label({"kind": "station", "title": "Coastal observatory Brest"}, "fr") == "un observatoire"
    assert station_spoken_label({"kind": "station", "title": "Station croisée"}, "fr") == ""


def test_rg5_one_station_per_chapter_closest_no_count():
    from film_script import _group_changes

    bacteria = {
        "id": "s0", "kind": "station", "score": 2, "tMs": 1, "nm": 1,
        "title": "Bacteria in Rias of Galicia", "fact": "Bacteria in Rias of Galicia",
    }
    far = {
        "id": "s1", "kind": "station", "score": 2, "tMs": 2, "nm": 8,
        "title": "Argo 6904216", "fact": "Argo 6904216", "source": "argo",
    }
    near = {
        "id": "s2", "kind": "station", "score": 2, "tMs": 3, "nm": 2,
        "title": "Argo 6901234", "fact": "Argo 6901234", "source": "argo",
    }
    escale = {
        "id": "e", "kind": "escale", "score": 3, "tMs": 4,
        "title": "Arrivée à Ajaccio", "fact": "x",
    }
    picked = select_chapter_changes([bacteria, far, near, escale], 0, 10, budget=False)
    stations = [c for c in picked if c.get("kind") == "station"]
    assert len(stations) == 1
    assert stations[0]["id"] == "s2"
    assert dose_station_changes([bacteria, far, near], 99) == [near]

    crowd = [
        {**far, "id": f"g{i}", "tMs": i, "title": f"Argo {6904216 + i}"}
        for i in range(6)
    ]
    grouped = _group_changes(crowd, 20 * 86_400_000)
    blob = " ".join(change_sentence(c, "fr") for c in grouped)
    assert "stations scientifiques croisées" not in blob
    assert not any(str(c.get("id") or "").startswith("group:station") for c in grouped)

    moments = {
        "moments": [
            {"seq": 0, "t": "2026-05-15T08:00:00Z", "signature": "s0", "legIdx": 0, "changes": [],
             "moment": {"leg": {"from": "Saint-Maur", "to": "La Rochelle"}}},
            {"seq": 1, "t": "2026-05-15T12:00:00Z", "signature": "s1", "legIdx": 0, "changes": [
                {"kind": "escale", "score": 3, "title": "Arrivée à La Rochelle", "fact": "x"},
            ], "moment": {"leg": {"from": "Saint-Maur", "to": "La Rochelle"}}},
            {"seq": 2, "t": "2026-05-16T09:00:00Z", "signature": "s2", "legIdx": 1, "changes": [
                {"kind": "station", "score": 2, "title": "Bacteria in Rias of Galicia",
                 "fact": "Bacteria in Rias of Galicia", "nm": 1},
                {"kind": "station", "score": 2, "title": "Argo 6904216",
                 "fact": "Argo 6904216 (8 nm)", "nm": 8, "source": "argo"},
                {"kind": "station", "score": 2, "title": "Argo 6901234",
                 "fact": "Argo 6901234 (2 nm)", "nm": 2, "source": "argo"},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)"}}},
            {"seq": 3, "t": "2026-05-24T12:51:00Z", "signature": "s3", "legIdx": 1, "changes": [
                {"kind": "escale", "score": 3, "title": "Arrivée à Ajaccio", "fact": "x"},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)"}}},
        ],
        "latest": [],
    }
    plan = build_raw_script(CLOCK, CLOCK["marks"], LIVE, moments, lang="fr", seconds=0, now_ms=NOW_MS)
    blob = _script_blob(plan)
    assert "Bacteria" not in blob
    assert "stations scientifiques croisées" not in blob
    assert blob.count("un flotteur Argo") <= 1
    assert "6904216" not in blob
    assert "6901234" not in blob


def _rg6_review():
    return {
        "legs": [
            {
                "from": "La Rochelle", "to": "Ajaccio (Corse)",
                "legNm": 1820, "daysAtSea": 9.5, "plannedKnots": 8,
            },
            {
                "from": "Ajaccio (Corse)", "to": "Fort-de-France (Martinique)",
                "legNm": 5153, "daysAtSea": 26.8, "plannedKnots": 8,
            },
            {
                "from": "Fort-de-France (Martinique)", "to": "Nouméa (Nouvelle-Calédonie)",
                "legNm": 12082, "daysAtSea": 63.0, "plannedKnots": 8,
            },
        ]
    }


def test_rg6_de_never_doubles():
    assert _de("Fineveke") == "de Fineveke"
    assert _de("de Fineveke") == "de Fineveke"
    assert "de de" not in _de("de Fineveke")
    assert _de("Ajaccio").startswith("d’") or _de("Ajaccio").startswith("d'")
    assert _de("Papeete") == "de Papeete"


def test_rg6_english_title_and_forbidden():
    assert looks_english_title("The Careenage")
    assert looks_english_title("Center Pertuis Breton deposit")
    assert looks_english_title("Laboratory Ship to Test Innovations in Extreme Conditions")
    assert looks_english_title("Coordination of a Global Socioeconomic Monitoring Initiative for Coastal Management")
    assert looks_english_title("Lesser Antilles Expedition")
    assert looks_english_title("Coral Gardeners")
    assert looks_english_title("Port Zante Marina")
    assert looks_english_title("IntelliReefs")
    assert not looks_english_title("port d'Ajaccio")
    assert not looks_english_title("Les Minimes")
    assert not looks_english_title("CÔTE À CÔTE")
    assert film_has_forbidden("À surveiller. Couloirs : Gibraltar. La jambe compte 12 milles.")
    assert film_has_forbidden("à portée de de Fineveke")
    assert not film_has_forbidden("Le 15 mai, Berry-Mappemonde quitte La Rochelle pour Ajaccio.")


def test_rg6_spoken_sea_days_and_date_thin():
    assert spoken_sea_days(9.5, "fr") == "une dizaine de jours de mer"
    assert spoken_sea_days(1.0, "fr") == "un jour de mer"
    assert spoken_sea_days(26.8, "fr") == "une trentaine de jours de mer"
    thinned = thin_chapter_dates([
        "Le 15 mai, Berry-Mappemonde quitte La Rochelle pour Ajaccio : 1 820 milles.",
        "Le 16 mai, les eaux espagnoles.",
        "Le 18 mai, les eaux portugaises.",
        "Arrivée à Ajaccio le 26 mai, amarré au port d'Ajaccio : trois jours d'escale.",
    ], "fr")
    assert "Le 15 mai" in thinned[0]
    assert not re.search(r"\b16 mai\b", thinned[1])
    assert "lendemain" in thinned[1].lower() or thinned[1].startswith("Puis")
    assert date_density_ok(" ".join(thinned), "fr")


def test_rg6_chapter_shape_and_metrics():
    w_long = {
        "fromName": "Ajaccio (Corse)", "toName": "Fort-de-France (Martinique)",
        "from": {"name": "Ajaccio (Corse)", "nm": 1820},
        "to": {"name": "Fort-de-France (Martinique)", "nm": 6973},
        "mode": "sail", "vehicle": "main",
    }
    m = chapter_metrics(w_long, _rg6_review())
    assert m["legNm"] == 5153
    assert m["daysAtSea"] == 26.8
    assert m["plannedKnots"] == 8
    assert chapter_shape(w_long, 2, 4, m) == "long"
    w_hop = {
        "fromName": "Fort-de-France", "toName": "Pointe-à-Pitre",
        "from": {"name": "Fort-de-France", "nm": 100},
        "to": {"name": "Pointe-à-Pitre", "nm": 292},
        "mode": "sail",
    }
    mh = chapter_metrics(w_hop, None)
    assert mh["legNm"] == 192
    assert chapter_shape(w_hop, 3, 8, mh) == "hop"


def test_rg6_gabarit_opening_route_arrival():
    journal = {
        "moments": [
            {"seq": 0, "t": "2026-05-15T08:00:00Z", "signature": "s0", "legIdx": 0, "changes": [],
             "moment": {"leg": {"from": "Saint-Maur", "to": "La Rochelle"}}},
            {"seq": 1, "t": "2026-05-15T12:00:00Z", "signature": "s1", "legIdx": 0, "changes": [
                {"kind": "escale", "score": 3, "title": "Arrivée à La Rochelle", "fact": "x"},
            ], "moment": {"leg": {"from": "Saint-Maur", "to": "La Rochelle"}}},
            {"seq": 2, "t": "2026-05-15T13:00:00Z", "signature": "s2", "legIdx": 1, "changes": [],
             "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)", "headingDeg": 246}}},
            {"seq": 3, "t": "2026-05-16T08:00:00Z", "signature": "s3", "legIdx": 1, "changes": [
                {"kind": "zee-enter", "score": 2, "title": "Spanish Exclusive Economic Zone",
                 "fact": "Spanish Exclusive Economic Zone"},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)", "headingDeg": 246}}},
            {"seq": 4, "t": "2026-05-16T12:00:00Z", "signature": "s4", "legIdx": 1, "changes": [
                {"kind": "coast", "score": 2, "title": "Camariñas", "fact": "Camariñas (4 nm)"},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)"}}},
            {"seq": 5, "t": "2026-05-21T08:00:00Z", "signature": "s5", "legIdx": 1, "changes": [
                {"kind": "marina", "score": 2, "title": "port d'Ajaccio", "fact": "port d'Ajaccio (1 nm)",
                 "lat": 41.92, "lon": 8.74},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)"}}},
            {"seq": 6, "t": "2026-05-24T12:51:00Z", "signature": "s6", "legIdx": 1, "changes": [
                {"kind": "escale", "score": 3, "title": "Arrivée à Ajaccio", "fact": "x"},
            ], "moment": {"leg": {"from": "La Rochelle", "to": "Ajaccio (Corse)"}}},
        ],
        "latest": [],
    }
    plan = build_raw_script(
        CLOCK, CLOCK["marks"], LIVE, journal, lang="fr", seconds=0, now_ms=NOW_MS,
        review=_rg6_review(),
    )
    ch = next(c for c in plan["chapters"] if "Ajaccio" in (c.get("toName") or c.get("text") or ""))
    text = ch["text"]
    assert re.search(r"Berry-Mappemonde quitte La Rochelle", text)
    assert "cap au sud-ouest" in text
    assert "1 820 milles" in text
    assert "dizaine de jours de mer" in text
    assert "8 nœuds de moyenne" in text
    assert "eaux espagnoles" in text
    assert "Arrivée à Ajaccio" in text
    assert "port d'Ajaccio" in text or "port d’Ajaccio" in text
    assert "à quai" not in text
    assert "À surveiller" not in text
    assert "Couloirs" not in text
    assert "La jambe" not in text
    assert "à portée de" not in text
    assert not film_has_forbidden(text)
    assert date_density_ok(text, "fr")
    sents = [s for s in re.split(r"(?<=[.!?…])\s+", text) if s.strip()]
    assert any("quitte" in s for s in sents)
    assert any("eaux" in s or "Galice" in s or "Camariñas" in s for s in sents)
    assert any(s.startswith("Arrivée") for s in sents)


def test_rg6_all_sail_chapters_have_distance_days_no_jargon():
    plan = build_raw_script(
        CLOCK, CLOCK["marks"], LIVE, {**JOURNAL, **MOMENTS},
        lang="fr", seconds=0, now_ms=NOW_MS, review=_rg6_review(),
    )
    blob = _script_blob(plan)
    assert not film_has_forbidden(blob)
    assert "3 jours à quai" not in blob
    assert blob.count("à quai") == 0
    hold_forms = set()
    for ch in plan["chapters"]:
        text = ch.get("text") or ""
        assert date_density_ok(text, "fr"), text
        if not is_sea_chapter(ch):
            continue
        if _is_airish(ch):
            continue
        assert re.search(r"\d[\d\s]*\s*milles", text), text
        assert re.search(
            r"jours de mer|jour de mer|dizaine de jours|vingtaine|trentaine|quarantaine",
            text,
        ), text
        if "Arrivée à" in text:
            for form in ("d'escale", "escale de", "au port", "on reste"):
                if form in text:
                    hold_forms.add(form)
    assert "Berry-Mappemonde quitte" in blob


def _is_airish(ch: dict) -> bool:
    t = ch.get("text") or ""
    return "s'envole" in t or "flies" in t


def test_rg6_hold_silent_when_clock_does_not_stop():
    from film_script import _arrival_sentence
    stop = {
        "name": "La Rochelle", "iso": "2026-05-15T12:00:00Z", "holdHours": 72,
        "lat": 46.15, "lon": -1.16,
    }
    clock = {
        "vertices": [
            {"iso": "2026-05-15T12:00:00Z", "lat": 46.15, "lon": -1.16, "vehicle": "main"},
            {"iso": "2026-05-15T13:00:00Z", "lat": 46.10, "lon": -1.30, "vehicle": "main"},
        ]
    }
    sent = _arrival_sentence(stop, "fr", clock=clock, harbor="le port de La Rochelle", chapter_i=0)
    assert "Arrivée à La Rochelle" in sent
    assert "escale" not in sent
    assert "à quai" not in sent


def test_rg6_arrival_harbor_ignores_far_marina():
    dest = {"name": "Ajaccio (Corse)", "lat": 41.92, "lon": 8.74}
    far = {"kind": "marina", "title": "Porto de Barizo", "lat": 43.32, "lon": -8.87, "tMs": 1}
    near = {"kind": "marina", "title": "port d'Ajaccio", "lat": 41.92, "lon": 8.74, "tMs": 2}
    spoken = _arrival_harbor([far, near], dest, "fr")
    assert "Ajaccio" in spoken
    assert "Barizo" not in spoken
    only_far = _arrival_harbor([far], dest, "fr")
    assert "Ajaccio" in only_far
    assert "Barizo" not in only_far
