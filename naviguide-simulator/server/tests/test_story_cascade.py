import asyncio
from pathlib import Path

import httpx

from story_cascade import build_prompt, has_skipper_orders, need_page, slim_event, write_story


def test_source_forbids_nemotron_and_tavily():
    src = Path(__file__).resolve().parents[1].joinpath("story_cascade.py").read_text()
    assert "Not Nemotron" in src
    assert "Not Tavily" in src
    assert "Not Token Factory" in src
    assert "integrate.api.nvidia.com" in src
    assert "openrouter.ai" in src
    assert "api.anthropic.com" in src
    assert "tavily.com" not in src
    assert "nvidia-nemotron" not in src.lower()


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
    assert "CE skipper" in system
    assert "skipper.used" in system
    assert "N’invente pas d’autre chiffre" in system
    assert "Thinking OFF" in system
    assert '"hsAlertM"' in user
    assert "3.5" in user
    assert "constante Croisière E1 3,5 m" in user

    system_en, _ = build_prompt({**body, "lang": "en"}, None)
    assert "THIS skipper" in system_en
    assert "skipper.used" in system_en

    plain, _ = build_prompt({"event": "hs-shift", "lang": "fr", "payload": {"hs": 3.6}}, None)
    assert "skipper.used" not in plain
    assert "CE skipper" not in plain


def test_slim_event_keeps_skipper_used_and_tavily_null():
    out = slim_event({"event": "hs-shift", "tavily": "nope", "skipper": SKIPPER})
    assert out["tavily"] is None
    assert out["skipper"]["used"][0]["value"] == 3.5
    assert out["skipper"]["boat"]["name"] == "Leopard 46"


def _chat_ok(text="Récit court de la ZEE.", model="openai/gpt-oss-20b"):
    return {
        "choices": [{"message": {"content": text}}],
        "model": model,
    }


def test_write_story_nim_first_without_page(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if "nvidia.com" in str(request.url):
            return httpx.Response(200, json=_chat_ok())
        return httpx.Response(500, json={"error": "no"})

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    transport = httpx.MockTransport(handler)

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
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
    assert out["cascade"] == "nim-or-claude"
    assert out["engine"].startswith("nvidia-")
    assert any("nvidia.com" in u for u in seen)
    assert not any("openrouter" in u or "anthropic" in u for u in seen)


def test_write_story_online_skips_nim(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        body = request.read().decode()
        assert "cabrera.es" in body
        assert ":online" in body or "openrouter.ai" in str(request.url)
        return httpx.Response(200, json=_chat_ok("Page officielle Cabrera : visiteurs."))

    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    transport = httpx.MockTransport(handler)

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await write_story({
                "event": "amp-ahead",
                "eventId": "amp:1",
                "needPage": True,
                "pageUrl": "https://cabrera.es/v",
                "tavily": None,
            }, client=client)

    out = asyncio.run(run())
    assert out["status"] == "ready"
    assert out["engine"] == "openrouter-online"
    assert out["tavily"] is None
    assert not any("nvidia.com" in u for u in seen)
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

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")

    transport = httpx.MockTransport(handler)

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await write_story({
                "event": "zee-enter",
                "eventId": "z",
                "needPage": False,
            }, client=client)

    out = asyncio.run(run())
    assert out["status"] == "ready"
    assert out["engine"] == "claude"
    assert any("nvidia.com" in u for u in seen)
    assert any("openrouter.ai" in u for u in seen)
    assert any("anthropic.com" in u for u in seen)
