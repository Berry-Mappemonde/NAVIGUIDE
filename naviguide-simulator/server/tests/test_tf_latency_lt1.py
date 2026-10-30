"""Non-régression garde de latence TF (contre-revue PR #153, P1-1, P1-2, P2).

R1 : un timeout Lightning relance Super VL (LT1).
R2 : providers par défaut + timeout TF → pas de repli hors Nemotron (sauf opt-in).
R3 : le délai TF est une échéance totale, pas un délai entre deux lectures.
R4 : nano, file pleine → pas de second passage dans la même file.
R5 : un timeout HTTP est compté au budget du jour (estimation prudente).
"""
import asyncio, json, time
import httpx, pytest
import llm_budget, story_cascade
from story_cascade import cascade_text


def _ok(model):
    return {"choices": [{"message": {"content": "Récit court de la ZEE."}}], "model": model,
            "usage": {"prompt_tokens": 12, "completion_tokens": 8}}


def _run(handler, **kw):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await cascade_text("sys", kw.pop("user", "La ZEE."), c, fallback="Phrase locale.", facts={}, **kw)
    return asyncio.run(go())


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.setenv("NAVIGUIDE_TF_MODEL_GUARD", "0")
    story_cascade.reset_runtime()
    yield
    story_cascade.reset_runtime()


def test_R1_fast_timeout_still_retries_super(monkeypatch):
    """LT1 : un timeout Lightning (fast) doit relancer Super VL (write)."""
    monkeypatch.setenv("NAVIGUIDE_LLM_PROVIDERS", "tokenfactory")
    seen = []
    def h(req):
        body = json.loads(req.read().decode())
        seen.append(body["model"])
        if "Lightning" in body["model"]:
            raise httpx.ReadTimeout("slow", request=req)
        return httpx.Response(200, json=_ok(body["model"]))
    text, source = _run(h, tier="fast")
    assert source == "nemotron-super-vl", f"LT1 perdu : source={source}, appels={seen}"
    assert len(seen) == 2 and "Lightning" in seen[0] and "Super" in seen[1], seen
    assert llm_budget.status()["retrySuper"] == 1


def test_R1b_queue_timeout_does_not_retry_super(monkeypatch):
    """Un timeout de file n'est pas relancé sur Super (même file partagée)."""
    exc = story_cascade.TokenFactoryTimeout("tokenfactory queue timeout", queue=True)
    assert story_cascade._tf_fast_super_retry(exc) is False
    assert story_cascade._tf_fast_super_retry(
        story_cascade.TokenFactoryTimeout("tokenfactory timeout after 25 s")) is True


def _r2_handler(seen):
    def h(req):
        seen.append(str(req.url))
        if "tokenfactory" in str(req.url):
            raise httpx.ReadTimeout("slow", request=req)
        body = json.loads(req.read().decode())
        return httpx.Response(200, json=_ok(body["model"]))
    return h


def test_R2_timeout_default_providers_stays_nemotron(monkeypatch):
    """Timeout TF : NIM GPT-OSS est sauté tant que le fallback externe est opt-in."""
    monkeypatch.delenv("NAVIGUIDE_LLM_PROVIDERS", raising=False)
    monkeypatch.delenv("NAVIGUIDE_LLM_TIMEOUT_FALLBACK", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "nv-test")
    seen = []
    res = _run(_r2_handler(seen), tier="write")
    assert res[1] == "rules"
    assert all("tokenfactory" in u for u in seen), seen


def test_R2b_timeout_fallback_opt_in_is_labelled(monkeypatch):
    """Opt-in explicite : le repli NIM reste possible et étiqueté (nvidia-…)."""
    monkeypatch.delenv("NAVIGUIDE_LLM_PROVIDERS", raising=False)
    monkeypatch.setenv("NAVIGUIDE_LLM_TIMEOUT_FALLBACK", "1")
    monkeypatch.setenv("NVIDIA_API_KEY", "nv-test")
    res = _run(_r2_handler([]), tier="write")
    assert res[1].startswith("nvidia-") and "gpt-oss" in res.model


def test_R2c_non_timeout_failure_keeps_default_cascade(monkeypatch):
    """Un 5xx TF (pas un timeout) garde la cascade par défaut, inchangée."""
    monkeypatch.delenv("NAVIGUIDE_LLM_PROVIDERS", raising=False)
    monkeypatch.delenv("NAVIGUIDE_LLM_TIMEOUT_FALLBACK", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "nv-test")
    def h(req):
        if "tokenfactory" in str(req.url):
            return httpx.Response(503, json={"error": "busy"})
        body = json.loads(req.read().decode())
        return httpx.Response(200, json=_ok(body["model"]))
    res = _run(h, tier="write")
    assert res[1].startswith("nvidia-")


def test_R3_timeout_is_a_total_deadline(monkeypatch):
    """httpx read=1 s mais un serveur qui égrène un octet / 0,4 s pendant ~3 s."""
    monkeypatch.setenv("NAVIGUIDE_LLM_PROVIDERS", "tokenfactory")
    monkeypatch.setenv("NAVIGUIDE_TF_TIMEOUT_S", "1")
    async def go():
        async def serve(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            await asyncio.sleep(0.05)
            body = json.dumps(_ok("nvidia/Nemotron-3.5-Super-VL")).encode()
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n")
            await writer.drain()
            chunks = [body[i:i + max(1, len(body) // 8)] for i in range(0, len(body), max(1, len(body) // 8))]
            for c in chunks:
                writer.write(f"{len(c):x}\r\n".encode() + c + b"\r\n"); await writer.drain(); await asyncio.sleep(0.4)
            writer.write(b"0\r\n\r\n"); await writer.drain(); writer.close()
        srv = await asyncio.start_server(serve, "127.0.0.1", 0)
        port = srv.sockets[0].getsockname()[1]
        monkeypatch.setattr(story_cascade, "TOKENFACTORY_URL", f"http://127.0.0.1:{port}/v1/chat/completions")
        async with srv, httpx.AsyncClient() as c:
            t0 = time.monotonic()
            res = await cascade_text("sys", "La ZEE.", c, tier="write", fallback="Phrase locale.", facts={})
            return res, time.monotonic() - t0
    (text, source), dt = asyncio.run(go())
    assert dt < 2.0, f"échéance dépassée : {dt:.2f} s pour 1 s"
    assert source == "rules"


def test_R4_nano_queue_timeout_does_not_double(monkeypatch):
    """Nano : file pleine → timeout file, puis repli Lightning qui ré-attend la même file."""
    monkeypatch.setenv("NAVIGUIDE_LLM_PROVIDERS", "tokenfactory")
    monkeypatch.setenv("NAVIGUIDE_TF_PARALLEL", "1")
    monkeypatch.setenv("NAVIGUIDE_TF_TIMEOUT_S", "0.5")
    story_cascade.reset_runtime()
    async def go():
        sema = story_cascade._tf_limiter(); await sema.acquire()
        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=_ok("x")))) as c:
                t0 = time.monotonic()
                res = await cascade_text("sys", "La ZEE.", c, tier="nano", fallback="Phrase locale.", facts={})
                return res, time.monotonic() - t0
        finally:
            sema.release()
    (text, source), dt = asyncio.run(go())
    lat = llm_budget.latency_status()
    assert source == "rules"
    assert dt < 0.9, f"file attendue deux fois : {dt:.2f} s"
    assert "fast" not in lat or not (lat.get("fast") or {}).get("timeouts")


def test_R5_http_timeout_counts_budget(monkeypatch):
    """Un timeout HTTP compte une estimation prudente au plafond du jour."""
    monkeypatch.setenv("NAVIGUIDE_LLM_PROVIDERS", "tokenfactory")
    before = int(llm_budget.get_usage("write")["tokens"])
    def h(req):
        raise httpx.ReadTimeout("slow", request=req)
    _run(h, tier="write")
    after = int(llm_budget.get_usage("write")["tokens"])
    assert after - before >= llm_budget.max_tokens_for("write")
