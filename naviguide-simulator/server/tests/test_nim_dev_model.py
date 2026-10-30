"""NIM gratuit en dev / tests : modèle choisi par variable, jamais compté en USD Token Factory."""
import asyncio

import httpx
import pytest

import llm_budget
import story_cascade as sc


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("NAVIGUIDE_NIM_MODEL", "NAVIGUIDE_NIM_MODEL_WRITE", "NAVIGUIDE_NIM_MODEL_DEEP"):
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
