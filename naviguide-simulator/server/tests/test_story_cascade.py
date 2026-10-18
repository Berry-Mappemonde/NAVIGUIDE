import asyncio
import json
from pathlib import Path

import httpx

from story_cascade import (
    CACHE_NS,
    DEFAULT_PROVIDERS,
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
    story_tier,
    translate,
    write_story,
)

# Capture PR #252 / revue du 22 sept. : fiche Pointe-à-Pitre servie depuis le cache.
CAPTURE_LEAK = (
    "Input: A large JSON object containing marina lists.\n"
    "- Task: Present a scale stop to a sailing crew arriving at Pointe-à-Pitre.\n"
    "What's for the boat, what's for the crew, what to know for formalities."
)


def test_story_tier_ultra_for_escales_and_alerts():
    assert story_tier({"type": "stop"}) == "deep"
    assert story_tier({"type": "wind-gale"}) == "deep"
    assert story_tier({"type": "zee-enter", "severity": "info"}) == "write"
    assert story_tier({"type": "zee-enter", "severity": "alert"}) == "deep"


def test_default_cascade_is_token_factory_not_tavily():
    src = Path(__file__).resolve().parents[1].joinpath("story_cascade.py").read_text()
    assert "api.tokenfactory.nebius.com" in src
    assert "api.tokenfactory.us-central1.nebius.com" in src
    assert "NAVIGUIDE_LLM_PROVIDERS" in src
    assert "integrate.api.nvidia.com" in src  # NIM : 2e maillon
    assert "openrouter.ai" in src
    assert "api.anthropic.com" in src
    assert "tavily.com" not in src
    assert DEFAULT_PROVIDERS == ("tokenfactory", "nim", "openrouter", "claude")
    assert providers() == list(DEFAULT_PROVIDERS)  # ordre du porteur (20 sept.)


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
    """Nemotron thinking stays out of the visitor text."""
    data = {
        "choices": [{
            "message": {
                "content": "<think>raisonnement…</think> La Rochelle est un port.",
                "reasoning_content": "Analyze User Input: Task: Translate…",
                "reasoning": "I need to answer using ONLY the JSON.",
            },
        }],
    }
    assert _openai_text(data) == "La Rochelle est un port."


def test_openai_text_ignores_nvidia_reasoning_field():
    data = {
        "choices": [{
            "message": {
                "content": "",
                "reasoning": "I need to answer using ONLY the JSON. It lists:",
            },
        }],
    }
    assert _openai_text(data) == ""


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
    """Les formes de la capture (et leurs traductions) vident le texte."""
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
        "I need to answer using ONLY the JSON. It lists:",
        "The JSON does not contain any information about Cape Horn.",
        "JSON does not hold the answer.",
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
    """Une perle llm-cache fuitée est droppée, jamais re-servie."""
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
    assert seen["chat_template_kwargs"]["enable_thinking"] is False
    assert "thinking" not in seen["chat_template_kwargs"]
    assert seen["reasoning_effort"] == "none"
    assert "extra_body" not in seen


def test_lightning_payload_includes_thinking_off_flags_at_json_root():
    """LT1 étape A confirmée (#432) : drapeaux au premier niveau du JSON, pas extra_body."""
    import llm_budget
    import story_cascade

    payload = story_cascade._tf_payload("sys", "user", "fast")
    assert set(payload) >= {
        "model", "messages", "max_tokens", "reasoning_effort", "chat_template_kwargs",
    }
    assert payload["reasoning_effort"] == "none"
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert "extra_body" not in payload
    nested = payload.get("extra_body")
    assert nested is None
    assert payload["max_tokens"] == llm_budget.max_tokens_for("fast")
    assert payload["max_tokens"] == 1024


def test_fast_nim_fallback_updates_status_by_tier(monkeypatch):
    import llm_budget

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "tokenfactory" in url:
            return httpx.Response(400, text='{"error":"fail"}')
        if "nvidia.com" in url:
            return httpx.Response(200, json=_chat_ok("NIM fallback text."))
        return httpx.Response(500)

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text(
                "sys", "user", client, tier="fast", fallback="x", facts="user",
            )

    text, source = asyncio.run(run())
    assert "NIM" in text
    st = llm_budget.status()
    assert st["fallback"]["nim"] == 1
    assert st["lastSourceByTier"]["fast"] == "nim"
    assert st["lastSource"] == "nim"


def test_fast_tokenfactory_empty_retries_super(monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        calls.append(body.get("model"))
        if "Lightning" in (body.get("model") or ""):
            return httpx.Response(200, json={
                "choices": [{"message": {"content": ""}, "finish_reason": "length"}],
                "usage": {"completion_tokens": 60},
                "model": body["model"],
            })
        return httpx.Response(200, json=_chat_ok("Lightning failed, Super answers.", model=body["model"]))

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text(
                "sys", "user", client, tier="fast", fallback="x", facts="user",
            )

    text, source = asyncio.run(run())
    assert source == "nemotron-super"
    assert "Super" in text
    assert len(calls) == 2
    assert any("Lightning" in m for m in calls)
    assert any("super" in m.lower() for m in calls)
    import llm_budget
    st = llm_budget.status()
    assert st["retrySuper"] == 1
    assert st["lastSourceByTier"]["fast"] == "nemotron-super"


def test_fast_tokenfactory_success_clears_tier_errors(monkeypatch):
    import llm_budget

    llm_budget.remember_cascade_errors(
        [{"provider": "tokenfactory", "reason": "old fast error"}], tier="fast",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        return httpx.Response(200, json=_chat_ok("Lightning ok.", model=body.get("model")))

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text(
                "sys", "user", client, tier="fast", fallback="x", facts="user",
            )

    text, source = asyncio.run(run())
    assert source == "nemotron-lightning"
    assert llm_budget.last_errors() is None
    st = llm_budget.status()
    assert "lastErrors" not in st
    assert st["lastSourceByTier"]["fast"] == "nemotron-lightning"


def test_fast_tokenfactory_empty_then_super_empty_calls_nim(monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        body = json.loads(request.content.decode()) if request.content else {}
        calls.append(url)
        if "tokenfactory" in url:
            return httpx.Response(200, json={
                "choices": [{"message": {"content": ""}, "finish_reason": "length"}],
                "usage": {"completion_tokens": 0},
                "model": body.get("model") or "tf",
            })
        if "nvidia.com" in url:
            return httpx.Response(200, json=_chat_ok("NIM after double TF miss."))
        return httpx.Response(500, json={"error": "no"})

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text(
                "sys", "user", client, tier="fast", fallback="x", facts="user",
            )

    text, source = asyncio.run(run())
    assert "NIM" in text
    assert source.startswith("nvidia-")
    assert sum("tokenfactory" in u for u in calls) == 2
    assert any("nvidia.com" in u for u in calls)


def test_ultra_payload_uses_cookbook_host_and_budget():
    import llm_budget
    import story_cascade

    payload = story_cascade._tf_payload("sys", "user", "deep")
    assert payload["reasoning_effort"] == "none"
    assert payload["chat_template_kwargs"]["enable_thinking"] is False
    assert "extra_body" not in payload
    assert payload["max_tokens"] == llm_budget.max_tokens_for("deep")
    assert payload["max_tokens"] == 2048
    assert "us-central1" in story_cascade._tf_url("deep")
    assert "us-central1" not in story_cascade._tf_url("fast")
    assert "us-central1" not in story_cascade._tf_url("write")


def test_tokenfactory_http_error_includes_body():
    import story_cascade

    class Fake:
        status_code = 400
        text = '{"error":"max_tokens too small for thinking"}'

    err = story_cascade._http_error("tokenfactory", Fake())
    assert "400" in str(err)
    assert "max_tokens too small" in str(err)


def test_cascade_records_tokenfactory_failure(monkeypatch, caplog):
    import llm_budget
    import story_cascade

    def handler(request: httpx.Request) -> httpx.Response:
        if "tokenfactory" in str(request.url):
            return httpx.Response(422, text='{"error":"empty completion"}')
        return httpx.Response(500)

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    caplog.set_level("WARNING", logger="naviguide-simulator.story-cascade")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text("sys", "user", client, fallback="Phrase locale.", facts="user")

    text, source = asyncio.run(run())
    assert source == "rules"
    assert text == "Phrase locale."
    hops = llm_budget.last_errors()
    assert hops and hops[0]["provider"] == "tokenfactory"
    assert "422" in hops[0]["reason"]
    assert "empty completion" in hops[0]["reason"]
    err = llm_budget.last_error()
    assert err["provider"] == "tokenfactory"
    assert any("tokenfactory" in r.message for r in caplog.records)
    assert {h["provider"] for h in hops} >= {"tokenfactory", "nim", "openrouter", "claude"}
    assert llm_budget.status()["lastError"]["reason"] == err["reason"]


def test_cascade_keeps_tokenfactory_error_when_nim_answers(monkeypatch):
    import llm_budget

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "tokenfactory" in url:
            return httpx.Response(400, text='{"error":"thinking not allowed"}')
        if "integrate.api.nvidia.com" in url:
            return httpx.Response(200, json=_chat_ok("The boat is at the quay."))
        return httpx.Response(500)

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text("sys", "The boat.", client, fallback="x", facts="The boat")

    text, source = asyncio.run(run())
    assert "quay" in text
    assert source.startswith("nvidia-")
    err = llm_budget.last_error()
    assert err["provider"] == "tokenfactory"
    assert "400" in err["reason"]
    assert "thinking not allowed" in err["reason"]


def _empty_reasoning(body, reasoning, finish="length"):
    return {
        "choices": [{
            "message": {"content": "", "reasoning": reasoning},
            "finish_reason": finish,
        }],
        "usage": {"prompt_tokens": 8, "completion_tokens": 40},
        "model": body.get("model"),
    }


def test_empty_content_with_reasoning_stays_on_the_tier(monkeypatch):
    """content vide + reasoning + finish=length : le texte et la source du palier, sans repli."""
    import llm_budget

    cases = (
        ("fast", "nvidia/Nemotron-3_5-Lightning", "nemotron-lightning", False),
        ("write", "nvidia/nemotron-3-super-120b-a12b", "nemotron-super", False),
        ("deep", "nvidia/Nemotron-3-Ultra-550b-a55b", "nemotron-ultra", True),
        ("judge", "nvidia/Nemotron-3-Ultra-550b-a55b", "nemotron-ultra", True),
    )
    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    for tier, model, source, ultra_host in cases:
        seen = []

        def handler(request: httpx.Request, _seen=seen) -> httpx.Response:
            body = json.loads(request.content.decode())
            _seen.append((str(request.url), body.get("model")))
            return httpx.Response(200, json=_empty_reasoning(
                body,
                "Analyze User Input: Task: Translate.\nLa Rochelle est un port.",
            ))

        async def run(tier=tier):
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await cascade_text(
                    "sys", f"user-{tier}", client, tier=tier, fallback="Phrase locale.", facts=None,
                )

        result = asyncio.run(run())
        text, got = result
        assert got == source, tier
        assert "port" in text, tier
        assert "Analyze" not in text, tier
        assert result.model == model, tier
        assert result.tier == tier
        assert len(seen) == 1, tier
        assert seen[0][1] == model, tier
        assert ("us-central1" in seen[0][0]) is ultra_host, tier
        assert "nvidia.com" not in seen[0][0]
        assert llm_budget.get_usage(tier)["calls"] == 1
        assert llm_budget.last_error() is None
        assert llm_budget.last_source_by_tier().get(tier) == source


def test_fast_leak_reasoning_still_retries_super(monkeypatch):
    """Un raisonnement qui n'est qu'une fuite ne devient pas le texte : Super est appelé."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        calls.append(body.get("model"))
        if "Lightning" in (body.get("model") or ""):
            return httpx.Response(200, json=_empty_reasoning(
                body, "I need to answer using ONLY the JSON. It lists:",
            ))
        return httpx.Response(200, json=_chat_ok("Super écrit le port.", model=body["model"]))

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cascade_text("sys", "user", client, tier="fast", fallback="x", facts=None)

    result = asyncio.run(run())
    text, source = result
    assert source == "nemotron-super"
    assert "port" in text
    assert "JSON" not in text
    assert len(calls) == 2
    assert "Lightning" in calls[0]
    assert "super" in calls[1].lower()
    assert result.model == "nvidia/nemotron-3-super-120b-a12b"
    assert result.tier == "write"


def test_write_story_keeps_exact_super_model_and_tier(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body["model"] == "nvidia/nemotron-3-super-120b-a12b"
        return httpx.Response(200, json=_chat_ok("Entrée dans la ZEE.", model=body["model"]))

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await write_story({
                "event": "zee-enter", "eventId": "zee-enter:model", "lang": "fr", "needPage": False,
            }, client=client)

    out = asyncio.run(run())
    assert out["status"] == "ready"
    assert out["source"] == "nemotron-super"
    assert out["tier"] == "write"
    assert out["model"] == "nvidia/nemotron-3-super-120b-a12b"
    assert out["ai_model"] == "nvidia/nemotron-3-super-120b-a12b"
    assert out["ai_generated"] is True
    assert "Token Factory" not in out["model"]


def test_fallback_model_is_not_labelled_token_factory(monkeypatch):
    """OpenRouter, Claude et NIM gardent leur modèle. Jamais un id Nemotron."""
    import llm_budget

    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    monkeypatch.setenv("NVIDIA_API_KEY", "nim-test")
    monkeypatch.setenv("NAVIGUIDE_LLM_CACHE_TTL_S", "0")

    def openrouter_handler(request: httpx.Request) -> httpx.Response:
        if "tokenfactory" in str(request.url):
            return httpx.Response(503, json={"error": "down"})
        if "openrouter.ai" in str(request.url):
            return httpx.Response(200, json=_chat_ok("Filet OpenRouter : le port."))
        return httpx.Response(500, json={"error": "no"})

    async def run_or():
        async with httpx.AsyncClient(transport=httpx.MockTransport(openrouter_handler)) as client:
            return await write_story({
                "event": "zee-enter", "eventId": "zee-or", "lang": "fr", "needPage": False,
            }, client=client)

    opened = asyncio.run(run_or())
    assert opened["source"] == "openrouter"
    assert opened["model"] == "openai/gpt-4o-mini"
    assert opened["ai_model"] == "openrouter"
    assert opened["tier"] == "write"
    assert "nemotron" not in opened["model"].lower()
    assert "nemotron" not in opened["ai_model"].lower()

    def claude_handler(request: httpx.Request) -> httpx.Response:
        if "anthropic.com" in str(request.url):
            return httpx.Response(200, json={
                "model": "claude-haiku-4-5",
                "content": [{"type": "text", "text": "Filet Claude : le port."}],
            })
        return httpx.Response(503, json={"error": "down"})

    async def run_claude():
        async with httpx.AsyncClient(transport=httpx.MockTransport(claude_handler)) as client:
            return await write_story({
                "event": "zee-enter", "eventId": "zee-claude", "lang": "fr", "needPage": False,
            }, client=client)

    claude = asyncio.run(run_claude())
    assert claude["source"] == "claude"
    assert claude["model"] == "claude-haiku-4-5"
    assert claude["ai_model"] == "claude"
    assert "nemotron" not in claude["model"].lower()
    assert "Token Factory" not in claude["ai_model"]

    def nim_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "tokenfactory" in url:
            body = json.loads(request.content.decode())
            return httpx.Response(200, json=_empty_reasoning(body, ""))
        if "nvidia.com" in url:
            return httpx.Response(200, json=_chat_ok("NIM : le port."))
        return httpx.Response(500, json={"error": "no"})

    async def run_nim():
        async with httpx.AsyncClient(transport=httpx.MockTransport(nim_handler)) as client:
            return await write_story({
                "event": "zee-enter", "eventId": "zee-nim", "lang": "fr", "needPage": False,
            }, client=client)

    nim = asyncio.run(run_nim())
    assert nim["source"].startswith("nvidia-")
    assert nim["model"] == "openai/gpt-oss-20b"
    assert nim["ai_model"] == "openai/gpt-oss-20b"
    assert "nemotron" not in nim["model"].lower()
    assert "Token Factory" not in nim["ai_model"]
    assert llm_budget.status()["lastSourceByTier"]["write"] == "nim"
