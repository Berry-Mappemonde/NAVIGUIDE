import asyncio
import json
from pathlib import Path

import httpx

from story_cascade import (
    CACHE_NS,
    _PROMPT_LEAK_RE,
    _cache_get,
    _clean_text,
    _openai_text,
    build_prompt,
    cascade_text,
    filter_numbers,
    has_skipper_orders,
    need_page,
    providers,
    slim_event,
    translate,
    write_story,
)

# Capture PR #252 / revue du 22 sept. : fiche Pointe-à-Pitre servie depuis le cache.
CAPTURE_LEAK = (
    "Input: A large JSON object containing marina lists.\n"
    "- Task: Present a scale stop to a sailing crew arriving at Pointe-à-Pitre.\n"
    "What's for the boat, what's for the crew, what to know for formalities."
)


def test_default_cascade_is_token_factory_not_tavily():
    src = Path(__file__).resolve().parents[1].joinpath("story_cascade.py").read_text()
    assert "api.tokenfactory.nebius.com" in src
    assert "NAVIGUIDE_LLM_PROVIDERS" in src
    assert "integrate.api.nvidia.com" in src  # NIM : 2e maillon
    assert "openrouter.ai" in src
    assert "api.anthropic.com" in src
    assert "tavily.com" not in src
    assert providers() == ["tokenfactory", "nim", "openrouter", "claude"]  # ordre du porteur (20 sept.)


def test_need_page_only_https_from_pack():
    assert need_page({"needPage": True, "pageUrl": "https://douane.gouv.fr/x"}) == (
        True, "https://douane.gouv.fr/x",
    )
    assert need_page({"needPage": False, "pageUrl": "https://douane.gouv.fr/x"})[0] is False
    assert need_page({"needPage": True, "pageUrl": "javascript:alert(1)"})[0] is False


def test_slim_event_keeps_tavily_null():
    out = slim_event({"event": "zee-enter", "tavily": "nope", "nvidia": None})
    assert out["tavily"] is None


def test_prompt_mentions_online_url_only_when_asked():
    system, user = build_prompt({"event": "zee-enter", "lang": "fr"}, None)
    assert "JSON" in user
    assert "monde" in system
    _, user2 = build_prompt({"event": "amp-ahead", "lang": "fr"}, "https://cabrera.es/v")
    assert "https://cabrera.es/v" in user2
    assert "Ne cherche pas le monde" in user2


SKIPPER = {
    "profile": "cruise",
    "profile_phrase": "Ordres Berry — croisière.",
    "comfort": "normal",
    "boat": {"name": "Leopard 46", "loaM": 14, "draftM": 1.4},
    "used": [
        {"id": "hsAlertM", "value": 3.5, "unit": "m", "source": "usage",
         "rule": "constante Croisière E1 3,5 m"},
    ],
}


def test_has_skipper_orders_needs_used_values():
    assert has_skipper_orders({"skipper": SKIPPER}) is True
    assert has_skipper_orders({"skipper": {"profile": "cruise", "used": []}}) is False
    assert has_skipper_orders({"skipper": None}) is False
    assert has_skipper_orders({}) is False
    assert has_skipper_orders(None) is False


def test_prompt_cites_the_skipper_thresholds_only_when_present():
    body = {"event": "hs-shift", "lang": "fr", "payload": {"hs": 3.6}, "skipper": SKIPPER}
    system, user = build_prompt(body, None)
    assert "skipper.used" in system
    assert "Aucun autre chiffre" in system
    assert "Thinking OFF" in system
    assert '"hsAlertM"' in user
    assert "3.5" in user
    assert "constante Croisière E1 3,5 m" in user

    system_en, _ = build_prompt({**body, "lang": "en"}, None)
    assert "skipper.used" in system_en

    plain, _ = build_prompt({"event": "hs-shift", "lang": "fr", "payload": {"hs": 3.6}}, None)
    assert "skipper.used" not in plain


def test_prompt_is_sober_one_or_two_sentences_no_machinery():
    """Revue du 19 sept. : le fait et sa source, rien sur le juge, l'identifiant, le bateau."""
    system, _ = build_prompt({"event": "depth-alert", "lang": "fr"}, None)
    assert "UNE ou DEUX phrases" in system
    for word in ("juge", "identifiant", "DOI", "tirant", "aucune information supplémentaire"):
        assert word in system  # listed as forbidden
    system_en, _ = build_prompt({"event": "depth-alert", "lang": "en"}, None)
    assert "ONE or TWO plain sentences" in system_en


def test_tidy_story_keeps_the_fact_drops_the_machinery():
    from story_cascade import tidy_story

    verbose = (
        "**Briefing nautique – La Rochelle**\n\n"
        "Le port d’entrée officiel se situe à Porto-Vecchio, à 292,3 nm. "
        "L’évènement est classé comme poe-ahead et porte l’identifiant poe-ahead:5682. "
        "Il a été jugé now avec la raison playhead. "
        "Le navire, un Leopard 46 de 14 m et 1,4 m de tirant d’eau, est en croisière avec un confort normal. "
        "Aucune information supplémentaire sur la période ou un DOI n’est disponible."
    )
    assert tidy_story(verbose) == "Le port d’entrée officiel se situe à Porto-Vecchio, à 292,3 nm."

    depth = (
        "La situation est classée immédiate par le juge. "
        "On approche du plateau : 2,3 m sondés pour un seuil fixé à 15 m, source EMODnet. "
        "Ne convient pas à la navigation. "
        "Le skipper a indiqué ce seuil conformément aux règles de croisière."
    )
    assert tidy_story(depth) == (
        "On approche du plateau : 2,3 m sondés pour un seuil fixé à 15 m, source EMODnet. "
        "Ne convient pas à la navigation."
    )

    # Only machinery → the local phrase; nothing at all → "".
    only_meta = "L’événement zee-exit est classé info. La décision a été prise immédiatement (juge)."
    assert tidy_story(only_meta, "Retour en haute mer — plus de ZEE à déclarer.") == "Retour en haute mer — plus de ZEE à déclarer."
    assert tidy_story(only_meta) == ""
    assert tidy_story(None, "repli") == "repli"
    # Long text is cut on a word, never mid-figure.
    long = "Vent " + "très " * 120 + "fort."
    out = tidy_story(long)
    assert len(out) <= 322 and out.endswith("…")


def test_write_story_returns_tidy_text_and_flags_local_fallback(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_ok(
            "La ZEE française a été quittée. L’évènement est classé info et jugé immédiat.",
        ))

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    async def run(text_handler):
        async with httpx.AsyncClient(transport=httpx.MockTransport(text_handler)) as client:
            return await write_story({
                "event": "zee-exit", "eventId": "zee-exit:1", "lang": "fr", "needPage": False,
                "phrase": "Retour en haute mer — plus de ZEE à déclarer.",
            }, client=client)

    out = asyncio.run(run(handler))
    assert out["status"] == "ready"
    assert out["text"] == "La ZEE française a été quittée."
    assert out["source"] == "nemotron-super"
    assert "+local" not in out["engine"]

    def only_meta(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_ok("Événement classé info, jugé immédiat par le juge."))

    out2 = asyncio.run(run(only_meta))
    assert out2["status"] == "ready"
    assert out2["text"] == "Retour en haute mer — plus de ZEE à déclarer."
    assert out2["engine"].endswith("+local")


def test_slim_event_keeps_skipper_used_and_tavily_null():
    out = slim_event({"event": "hs-shift", "tavily": "nope", "skipper": SKIPPER})
    assert out["tavily"] is None
    assert out["skipper"]["used"][0]["value"] == 3.5
    assert out["skipper"]["boat"]["name"] == "Leopard 46"


def _chat_ok(text="Récit court de la ZEE.", model="nvidia/nemotron-3-super-120b-a12b"):
    return {
        "choices": [{"message": {"content": text}}],
        "model": model,
        "usage": {"prompt_tokens": 12, "completion_tokens": 8},
    }


def _tf_body(system="sys", user="La ZEE 5677.", **kw):
    kw.setdefault("tier", "write")
    kw.setdefault("fallback", "Phrase locale.")
    kw.setdefault("facts", {"zee": {"mrgid": 5677}})
    return system, user, kw


def test_cascade_tokenfactory_write_is_nemotron_super(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        assert "tokenfactory.nebius.com" in str(request.url)
        body = request.read().decode()
        assert "nemotron-3-super-120b-a12b" in body
        return httpx.Response(200, json=_chat_ok("Entrée dans la ZEE française."))

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")

    async def run():
        system, user, kw = _tf_body()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text(system, user, client, **kw)

    text, source = asyncio.run(run())
    assert source == "nemotron-super"
    assert "ZEE" in text
    assert len(seen) == 1
    assert not any("openrouter" in u or "anthropic" in u or "nvidia.com" in u for u in seen)


def test_cascade_tokenfactory_429_falls_to_openrouter(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if "tokenfactory" in str(request.url):
            return httpx.Response(429, json={"error": "rate"})
        if "openrouter.ai" in str(request.url):
            return httpx.Response(200, json=_chat_ok("Filet OpenRouter : ZEE 5677."))
        return httpx.Response(500, json={"error": "no"})

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    async def run():
        system, user, kw = _tf_body()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text(system, user, client, **kw)

    text, source = asyncio.run(run())
    assert source == "openrouter"
    assert "5677" in text
    assert any("tokenfactory" in u for u in seen)
    assert any("openrouter.ai" in u for u in seen)


def test_cascade_all_down_returns_rules(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(503, json={"error": "down"})

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")

    async def run():
        system, user, kw = _tf_body()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text(system, user, client, **kw)

    text, source = asyncio.run(run())
    assert source == "rules"
    assert text == "Phrase locale."
    assert any("tokenfactory" in u for u in seen)
    assert any("openrouter.ai" in u for u in seen)
    assert any("anthropic.com" in u for u in seen)


def test_cascade_budget_cap_makes_no_request(monkeypatch):
    import llm_budget

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    monkeypatch.setenv("NAVIGUIDE_LLM_DAILY_TOKENS_WRITE", "10")
    llm_budget.record("write", 10, 0)
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=_chat_ok("ne doit pas partir"))

    async def run():
        system, user, kw = _tf_body()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text(system, user, client, **kw)

    text, source = asyncio.run(run())
    assert source == "budget"
    assert seen == []
    assert text == "Phrase locale."


def test_cascade_lock_one_call_for_two_identical_requests(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=_chat_ok("Un seul appel Token Factory, ZEE 5677."))

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")

    async def run():
        system, user, kw = _tf_body()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            a, b = await asyncio.gather(
                cascade_text(system, user, client, **kw),
                cascade_text(system, user, client, **kw),
            )
            return a, b

    (t1, s1), (t2, s2) = asyncio.run(run())
    assert {s1, s2} <= {"nemotron-super", "cache"}
    assert t1 == t2
    assert len(seen) == 1


def test_filter_numbers_always_applied_on_cascade(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_ok(
            "La ZEE 5677 commence ici. Le vent sera de 99 kn demain.",
        ))

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")

    async def run():
        system, user, kw = _tf_body()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text(system, user, client, **kw)

    text, source = asyncio.run(run())
    assert source == "nemotron-super"
    assert "5677" in text
    assert "99" not in text


def test_filter_numbers_drops_invented_figures():
    text, dropped = filter_numbers(
        "La ZEE 5677. Il fera 30 kn demain.",
        {"zee": {"mrgid": 5677}},
    )
    assert "5677" in text and "30" not in text and dropped == 1


def test_write_story_tokenfactory_first_without_page(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if "tokenfactory" in str(request.url):
            return httpx.Response(200, json=_chat_ok())
        return httpx.Response(500, json={"error": "no"})

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await write_story({
                "event": "zee-enter",
                "eventId": "zee-enter:1",
                "lang": "fr",
                "needPage": False,
                "tavily": None,
            }, client=client)

    out = asyncio.run(run())
    assert out["status"] == "ready"
    assert out["tavily"] is None
    assert out["cascade"] == "tokenfactory-openrouter-claude"
    assert out["source"] == "nemotron-super"
    assert any("tokenfactory" in u for u in seen)
    assert not any("openrouter" in u or "anthropic" in u or "nvidia.com" in u for u in seen)


def test_write_story_need_page_still_reaches_openrouter_online(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if "tokenfactory" in str(request.url):
            return httpx.Response(503, json={"error": "down"})
        body = request.read().decode()
        assert "cabrera.es" in body
        return httpx.Response(200, json=_chat_ok("Page officielle Cabrera : visiteurs."))

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await write_story({
                "event": "amp-ahead",
                "eventId": "amp:1",
                "needPage": True,
                "pageUrl": "https://cabrera.es/v",
                "tavily": None,
            }, client=client)

    out = asyncio.run(run())
    assert out["status"] == "ready"
    assert out["source"] == "openrouter"
    assert out["tavily"] is None
    assert any("openrouter.ai" in u for u in seen)
    assert not any("tavily" in u for u in seen)


def test_write_story_falls_to_claude(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if "anthropic.com" in str(request.url):
            return httpx.Response(200, json={
                "content": [{"type": "text", "text": "Filet Claude : ZEE."}],
            })
        return httpx.Response(503, json={"error": "down"})

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await write_story({
                "event": "zee-enter",
                "eventId": "z",
                "needPage": False,
            }, client=client)

    out = asyncio.run(run())
    assert out["status"] == "ready"
    assert out["source"] == "claude"
    assert any("tokenfactory" in u for u in seen)
    assert any("openrouter.ai" in u for u in seen)
    assert any("anthropic.com" in u for u in seen)


def test_nim_still_available_behind_the_flag(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if "nvidia.com" in str(request.url):
            return httpx.Response(200, json=_chat_ok("NIM : ZEE."))
        return httpx.Response(500, json={"error": "no"})

    monkeypatch.setenv("NAVIGUIDE_LLM_PROVIDERS", "nim,openrouter,claude")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text("s", "ZEE 1", client, fallback="x", facts={"n": 1})

    text, source = asyncio.run(run())
    assert "ZEE" in text
    assert any("nvidia.com" in u for u in seen)
    assert source.startswith("nvidia-")


FR_STORY = "Le 21 mai 2026 le bateau entre dans la ZEE française à La Rochelle, 36,5 kn [[ev:wx:gale]]."
EN_STORY = "On 21 May 2026 the boat entered the French EEZ at La Rochelle, 36.5 kn [[ev:wx:gale]]."


def test_translate_fr_is_noop():
    text, source = asyncio.run(translate("Déjà en français, ZEE 5677.", "fr"))
    assert text == "Déjà en français, ZEE 5677."
    assert source == "rules"


def test_translate_empty_is_rules():
    text, source = asyncio.run(translate("  ", "en"))
    assert text == "" and source == "rules"


def test_translate_en_keeps_numbers_names_dates(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        body = request.read().decode()
        assert "Nemotron-3_5-Lightning" in body
        assert "36,5" in body and "La Rochelle" in body and "2026" in body
        return httpx.Response(200, json=_chat_ok(
            EN_STORY + " Tomorrow 99 kn.",
            model="nvidia/Nemotron-3_5-Lightning",
        ))

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await translate(FR_STORY, "en", client)

    text, source = asyncio.run(run())
    assert source == "nemotron-lightning"
    assert "36.5" in text or "36,5" in text
    assert "La Rochelle" in text
    assert "2026" in text
    assert "[[ev:wx:gale]]" in text
    assert "99" not in text, "aucun chiffre nouveau"
    assert any("tokenfactory" in u for u in seen)


def test_translate_cache_is_per_lang(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=_chat_ok(EN_STORY, model="nvidia/Nemotron-3_5-Lightning"))

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            a = await translate(FR_STORY, "en", client)
            b = await translate(FR_STORY, "en", client)
            fr = await translate(FR_STORY, "fr", client)
            return a, b, fr

    (t1, s1), (t2, s2), (t3, s3) = asyncio.run(run())
    assert t1 == t2 == EN_STORY.strip()
    assert {s1, s2} <= {"nemotron-lightning", "cache"}
    assert len(seen) == 1
    assert t3 == FR_STORY and s3 == "rules"


def test_write_story_en_translates_after_french_draft(monkeypatch):
    seen_models = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        if "Nemotron-3_5-Lightning" in body:
            seen_models.append("fast")
            return httpx.Response(200, json=_chat_ok(
                "The boat entered the French EEZ 5677.",
                model="nvidia/Nemotron-3_5-Lightning",
            ))
        seen_models.append("write")
        return httpx.Response(200, json=_chat_ok("Le bateau entre dans la ZEE française 5677."))

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await write_story({
                "event": "zee-enter", "eventId": "zee-enter:en", "lang": "en",
                "needPage": False, "payload": {"zee": {"mrgid": 5677}},
            }, client=client)

    out = asyncio.run(run())
    assert out["status"] == "ready"
    assert out["source"] == "nemotron-lightning"
    assert "5677" in out["text"]
    assert "99" not in out["text"]
    assert seen_models == ["write", "fast"]


def test_openai_text_strips_think_keeps_sentence():
    """Lot RA1 : Nemotron thinking stays out of the visitor text."""
    data = {
        "choices": [{
            "message": {
                "content": "<think>raisonnement…</think> La Rochelle est un port.",
                "reasoning_content": "Analyze User Input: Task: Translate…",
            },
        }],
    }
    assert _openai_text(data) == "La Rochelle est un port."


def test_openai_text_unclosed_think_is_cut():
    data = {"choices": [{"message": {"content": "<think>encore en train de réfléchir"}}]}
    assert _openai_text(data) == ""


def test_clean_text_strips_analyze_preamble():
    raw = (
        "**Analyze User Input: Task: Translate this paragraph.** "
        "Wait, let me re-read carefully. "
        "Saint-Maur is a quiet harbor on the Marne."
    )
    assert _clean_text(raw) == "Saint-Maur is a quiet harbor on the Marne."


def test_clean_text_prompt_leak_is_empty():
    leaked = (
        "You translate a sailing-log paragraph from French to English. "
        "Keep every number, unit, proper name."
    )
    assert _clean_text(leaked) == ""
    echoed = (
        "Request: Present a stop/escales to a sailing crew arriving at Saint-Maur. "
        "- Constraints: Max 3 sentences."
    )
    assert _clean_text(echoed) == ""
    assert _clean_text("Here's a thinking process: 1") == ""
    assert "Analyze User Input" not in _clean_text("**Analyze User Input:** Entity: REPHY")


def test_prompt_leak_re_covers_22_sept_forms():
    """Lot RB3 : les formes de la capture (et leurs traductions) vident le texte."""
    forms = (
        "Input: A large JSON object containing marina lists.",
        "What's for the boat, what's for the crew.",
        "- Task: Present a scale stop to a sailing crew.",
        "Task: Present a scale stop at Pointe-à-Pitre.",
        "Entrée : Un grand objet JSON déjà collecté.",
        "Ce qu'il y a pour le bateau, ce qu'il y a pour l'équipage.",
        "- Tâche : Présente une escale à Pointe-à-Pitre.",
        "You are the logbook of the Berry-Mappemonde sailing expedition.",
        "Tu es le journal de bord de l'expédition à la voile.",
        CAPTURE_LEAK,
    )
    for form in forms:
        assert _PROMPT_LEAK_RE.search(form), form
        assert _clean_text(form) == "", form
    healthy = "Pointe-à-Pitre has a marina at Bas-du-Fort and a harbour master's office."
    assert not _PROMPT_LEAK_RE.search(healthy)
    assert _clean_text(healthy) == healthy
    # Un « task » sans deux-points (phrase réelle) n'est pas une fuite.
    real = "The harbour master's task is to assign a berth."
    assert _clean_text(real) == real


def test_llm_cache_leaked_entry_is_invalidated(monkeypatch):
    """Lot RB3 : une perle llm-cache fuitée est droppée, jamais re-servie."""
    import pearl_store

    monkeypatch.delenv("NAVIGUIDE_LLM_CACHE_TTL_S", raising=False)
    key = "rb3-leak-capture"
    pearl_store.kv_put(CACHE_NS, key, {"text": CAPTURE_LEAK, "source": "nemotron-super"})
    assert pearl_store.kv_get(CACHE_NS, key) is not None
    assert _cache_get(key) is None
    assert pearl_store.kv_get(CACHE_NS, key) is None


def test_llm_cache_healthy_entry_is_served_unchanged(monkeypatch):
    import pearl_store

    monkeypatch.delenv("NAVIGUIDE_LLM_CACHE_TTL_S", raising=False)
    key = "rb3-healthy"
    text = "Pointe-à-Pitre has a marina at Bas-du-Fort."
    pearl_store.kv_put(CACHE_NS, key, {"text": text, "source": "nemotron-super"})
    assert _cache_get(key) == (text, "cache")
    stored = (pearl_store.kv_get(CACHE_NS, key) or {}).get("value") or {}
    assert stored.get("text") == text


def test_cascade_think_block_keeps_final_sentence(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_ok(
            "<think>raisonnement…</think> La Rochelle est un port.",
        ))

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text(
                "sys", "La Rochelle.", client, fallback="Phrase locale.", facts="La Rochelle",
            )

    text, source = asyncio.run(run())
    assert text == "La Rochelle est un port."
    assert source == "nemotron-super"


def test_cascade_reasoning_only_falls_to_rules(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_ok(
            "<think>Wait, let me analyze the task. Analyze User Input.</think>",
        ))

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text(
                "sys", "user", client, fallback="Phrase locale.", facts="user",
            )

    text, source = asyncio.run(run())
    assert source == "rules"
    assert text == "Phrase locale."


def test_tokenfactory_payload_disables_thinking(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if "tokenfactory" in str(request.url):
            seen.update(json.loads(request.content.decode()))
            return httpx.Response(200, json=_chat_ok("La Rochelle est un port."))
        return httpx.Response(500, json={"error": "no"})

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text(
                "sys", "La Rochelle.", client, fallback="x", facts="La Rochelle",
            )

    text, source = asyncio.run(run())
    assert "port" in text
    assert source == "nemotron-super"
    assert seen["chat_template_kwargs"]["thinking"] is False
    assert seen["reasoning_effort"] == "low"
