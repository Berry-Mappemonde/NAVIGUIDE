"""Plafonds journaliers Token Factory (lot L1)."""
from datetime import datetime, timezone

import llm_budget


def test_estimate_usd_matches_plan_grid():
    # Super : 0,30 $ / M in, 0,90 $ / M out → 1000 + 100 tokens = 0,00039 $
    assert llm_budget.estimate_usd("write", 1000, 100) == 0.00039
    assert llm_budget.estimate_usd("fast", 1_000_000, 0) == 0.06
    assert llm_budget.estimate_usd("judge", 0, 1_000_000) == 3.0


def test_record_increments_tokens_calls_usd():
    assert llm_budget.get_usage("write")["tokens"] == 0
    out = llm_budget.record("write", 2000, 300)
    assert out["tokens"] == 2300
    assert out["calls"] == 1
    assert out["usd"] == llm_budget.estimate_usd("write", 2000, 300)
    out2 = llm_budget.record("write", 100, 0)
    assert out2["tokens"] == 2400 and out2["calls"] == 2
    st = llm_budget.status()
    assert st["write"]["tokens"] == 2400
    assert st["write"]["calls"] == 2
    assert st["fast"]["tokens"] == 0 and st["judge"]["calls"] == 0


def test_allow_false_at_cap(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_LLM_DAILY_TOKENS_WRITE", "100")
    assert llm_budget.allow("write") is True
    llm_budget.record("write", 60, 40)
    assert llm_budget.get_usage("write")["tokens"] == 100
    assert llm_budget.allow("write") is False
    llm_budget.record("write", 10, 0)  # counter may grow; still capped
    assert llm_budget.allow("write") is False


def test_models_and_sources_are_overridable(monkeypatch):
    assert llm_budget.model_for("fast") == "nvidia/Nemotron-3_5-Lightning"
    assert llm_budget.model_for("write") == "nvidia/nemotron-3-super-120b-a12b"
    assert llm_budget.model_for("judge") == "nvidia/Nemotron-3-Ultra-550b-a55b"
    assert llm_budget.source_for("write") == "nemotron-super"
    monkeypatch.setenv("NAVIGUIDE_TF_MODEL_WRITE", "nvidia/nemotron-3-nano-30b-a3b")
    assert llm_budget.model_for("write") == "nvidia/nemotron-3-nano-30b-a3b"
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    llm_budget.record("fast", 1, 1)
    import pearl_store
    assert pearl_store.kv_get("llm-budget", f"{day}:fast")["value"]["calls"] == 1


def test_allow_tavily_respects_daily_cap(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_TAVILY_DAILY_CREDITS", "1")
    assert llm_budget.allow_tavily() is True
    llm_budget.record_tavily(1)
    assert llm_budget.tavily_usage()["credits"] == 1
    assert llm_budget.allow_tavily() is False


def test_remember_source_skips_cache():
    llm_budget.remember_source("nemotron-super")
    assert llm_budget.last_source() == "nemotron-super"
    llm_budget.remember_source("cache")
    assert llm_budget.last_source() == "nemotron-super"
    st = llm_budget.status()
    assert st["lastSource"] == "nemotron-super"


def test_mode_off_forbids_every_call(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_LLM_MODE", "off")
    for tier in ("fast", "write", "judge"):
        assert llm_budget.allow(tier) is False


def test_on_demand_forbids_background_but_allows_request(monkeypatch):
    monkeypatch.delenv("NAVIGUIDE_LLM_MODE", raising=False)
    monkeypatch.setenv("NAVIGUIDE_LLM_DAILY_TOKENS_WRITE", "1000")
    assert llm_budget.mode() == "on-demand"
    assert llm_budget.allow("write") is True, "une action de l'utilisateur peut appeler"
    with llm_budget.background():
        assert llm_budget.allow("write") is False, "l'arrière-plan ne dépense rien"
    assert llm_budget.allow("write") is True
    monkeypatch.setenv("NAVIGUIDE_LLM_BACKGROUND", "1")
    assert llm_budget.allow("write") is False, "processus marqué arrière-plan (remplisseur)"


def test_mode_all_allows_background(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_LLM_MODE", "all")
    monkeypatch.setenv("NAVIGUIDE_LLM_DAILY_TOKENS_WRITE", "1000")
    with llm_budget.background():
        assert llm_budget.allow("write") is True


def test_judge_cap_is_zero_by_default(monkeypatch):
    monkeypatch.delenv("NAVIGUIDE_LLM_DAILY_TOKENS_JUDGE", raising=False)
    assert llm_budget.daily_cap("judge") == 0
    assert llm_budget.allow("judge") is False
