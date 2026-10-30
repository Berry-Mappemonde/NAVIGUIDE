"""NIM gratuit en dev / tests : modèle choisi par variable, jamais compté en USD Token Factory."""
import asyncio

import httpx
import pytest

import llm_budget
import story_cascade as sc


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("NAVIGUIDE_NIM_MODEL", "NAVIGUIDE_NIM_MODEL_WRITE", "NAVIGUIDE_NIM_MODEL_DEEP",
              "NAVIGUIDE_NIM_FAST_TIERS", "NAVIGUIDE_NIM_FAST_MODEL",
              "NAVIGUIDE_NIM_CONCURRENCY", "NAVIGUIDE_NIM_MAX_ATTEMPTS"):
        monkeypatch.delenv(k, raising=False)


def test_default_model_unchanged():
    assert sc.nim_model() == sc.NIM_MODEL == "openai/gpt-oss-20b"
    assert sc.nim_model("write") == sc.NIM_MODEL


def test_global_then_per_tier(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_NIM_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
    assert sc.nim_model("write") == "nvidia/nemotron-3-ultra-550b-a55b"
    monkeypatch.setenv("NAVIGUIDE_NIM_MODEL_WRITE", "nvidia/nemotron-3-super-120b-a12b")
    assert sc.nim_model("write") == "nvidia/nemotron-3-super-120b-a12b"
    assert sc.nim_model("deep") == "nvidia/nemotron-3-ultra-550b-a55b"
    monkeypatch.setenv("NAVIGUIDE_NIM_MODEL_DEEP", "  ")
    assert sc.nim_model("deep") == "nvidia/nemotron-3-ultra-550b-a55b"


def test_call_nim_uses_model_and_never_records_usd(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("NAVIGUIDE_NIM_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
    seen = {}

    def handler(request):
        import json
        seen["url"] = str(request.url)
        seen["model"] = json.loads(request.content)["model"]
        return httpx.Response(200, json={
            "model": seen["model"],
            "choices": [{"message": {"content": "Le bateau file vers les Antilles."}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 8},
        })

    recorded = []
    monkeypatch.setattr(llm_budget, "record", lambda *a, **k: recorded.append(a))

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await sc._call_nim("sys", "user", client, tier="write")

    res = asyncio.run(run())
    assert seen["url"].startswith("https://integrate.api.nvidia.com/")
    assert seen["model"] == "nvidia/nemotron-3-ultra-550b-a55b"
    _text, source = res
    assert source == "nvidia-nemotron-3-ultra-550b-a55b"
    assert res.model == "nvidia/nemotron-3-ultra-550b-a55b"
    assert recorded == []  # aucun compteur Token Factory (tokens / USD)


def test_write_tier_override_only_affects_write(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_NIM_MODEL_WRITE", "nvidia/nemotron-3.5-super-vl-120b-a12b")
    assert sc.nim_model("write") == "nvidia/nemotron-3.5-super-vl-120b-a12b"
    assert sc.nim_model("WRITE") == "nvidia/nemotron-3.5-super-vl-120b-a12b"
    assert sc.nim_model("deep") == sc.NIM_MODEL
    assert sc.nim_model() == sc.NIM_MODEL


def test_fast_tier_and_explicit_override(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_NIM_FAST_TIERS", "NANO,FAST")
    monkeypatch.setenv("NAVIGUIDE_NIM_FAST_MODEL", "fast/model")
    assert sc.nim_model("nano") == "fast/model"
    assert sc.nim_model("write") == sc.NIM_MODEL
    monkeypatch.setenv("NAVIGUIDE_NIM_MODEL_NANO", "specific/model")
    assert sc.nim_model("nano") == "specific/model"


def _nim_response():
    return httpx.Response(200, json={"choices": [{"message": {"content": "Cap au sud."}}]})


def test_nim_retries_429_then_succeeds(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setattr(sc, "_nim_sleep", lambda delay: asyncio.sleep(0))
    statuses = iter([429, 200])
    requests = []
    def handler(request):
        requests.append(request)
        status = next(statuses)
        return httpx.Response(status, json={} if status == 429 else _nim_response().json())
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await sc._call_nim("sys", "user", client)
    asyncio.run(run())
    assert len(requests) == 2


def test_nim_retry_after_is_honored(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    sleeps = []
    async def fake_sleep(delay): sleeps.append(delay)
    monkeypatch.setattr(sc, "_nim_sleep", fake_sleep)
    calls = 0
    def handler(_request):
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"Retry-After": "3"}) if calls == 1 else _nim_response()
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await sc._call_nim("sys", "user", client)
    asyncio.run(run())
    assert sleeps == [3]


def test_nim_three_429_raise_after_three(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    async def fake_sleep(_delay): pass
    monkeypatch.setattr(sc, "_nim_sleep", fake_sleep)
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429, text="limited")
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await sc._call_nim("sys", "user", client)
    with pytest.raises(RuntimeError):
        asyncio.run(run())
    assert len(calls) == 3


def test_nim_does_not_retry_400(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(400, text="bad request")
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await sc._call_nim("sys", "user", client)
    with pytest.raises(RuntimeError):
        asyncio.run(run())
    assert len(calls) == 1


@pytest.mark.parametrize(("limit", "expected"), [("1", 1), ("2", 2)])
def test_nim_concurrency_limit(monkeypatch, limit, expected):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("NAVIGUIDE_NIM_CONCURRENCY", limit)
    active = peak = 0
    async def fake_sleep(_delay): pass
    monkeypatch.setattr(sc, "_nim_sleep", fake_sleep)
    async def run():
        nonlocal active, peak
        class DelayedMockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                nonlocal active, peak
                active += 1
                peak = max(peak, active)
                await asyncio.sleep(0.01)
                active -= 1
                return _nim_response()
        async with httpx.AsyncClient(transport=DelayedMockTransport()) as client:
            await asyncio.gather(*(sc._call_nim("sys", "user", client) for _ in range(3)))
    asyncio.run(run())
    assert peak <= expected
    if expected == 1:
        assert peak == 1


def test_invalid_nim_concurrency_uses_default(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_NIM_CONCURRENCY", "invalid")
    assert sc._nim_int_env("NAVIGUIDE_NIM_CONCURRENCY", 2, 1, 16) == 2


def test_call_nim_logs_chosen_model(monkeypatch, caplog):
    import logging
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("NAVIGUIDE_NIM_MODEL_WRITE", "nvidia/nemotron-3.5-super-vl-120b-a12b")

    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": "Cap au sud-ouest."}}]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await sc._call_nim("sys", "user", client, tier="write")

    with caplog.at_level(logging.INFO, logger=sc.log.name):
        asyncio.run(run())
    assert any("nvidia/nemotron-3.5-super-vl-120b-a12b" in r.getMessage() for r in caplog.records)
