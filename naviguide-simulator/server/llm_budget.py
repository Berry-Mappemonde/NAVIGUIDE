"""Budget journalier des appels LLM (lot L1, plan Nemotron § 0 / § 3).

Compteurs par niveau (`fast` / `write` / `judge`) dans `pearl_store.kv`,
clé logique `llm-budget:<date>:<tier>`. Au plafond : aucun appel réseau
(la cascade rend `source=budget`). L’USD est une estimation d’après la
grille Token Factory du 20 sept. 2026, jamais un chiffre produit par un modèle.
"""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

NS = "llm-budget"
LAST_SOURCE_NS = "llm"
LAST_SOURCE_KEY = "last-source"
LAST_ERROR_KEY = "last-error"

TIERS = ("fast", "write", "deep", "judge")

# Tokens / jour — resserrés le 28 sept. (facture Nebius du mois : 6,58 $ sur 60 $ de crédits, dont 5,19 $ de
# Nemotron Ultra pour un badge que personne ne voyait) : fast ≈ 0,05 $/j, write ≈ 0,08 $/j, judge 0.
DEFAULT_CAPS = {
    "fast": 200_000,
    "write": 150_000,
    "deep": 80_000,
    "judge": 0,
}

# Mode LLM (NAVIGUIDE_LLM_MODE) — décision du porteur du 28 sept. : « Nemotron seulement quand je le dis ou
# quand c'est utile ».
#   off        : aucun appel payant, jamais (agents de lot, CI, machines de dev).
#   on-demand  : (défaut) seulement sur une action de l'utilisateur — question au chat, clic « Rédigé » —
#                jamais en arrière-plan (préchauffage des récits, écriture du film, phrase de la revue,
#                remplisseur du stock).
#   all        : tout, comme avant (à poser explicitement sur le poste pour une démo complète).
_MODES = ("off", "on-demand", "all")
_BACKGROUND: ContextVar[bool] = ContextVar("naviguide_llm_background", default=False)
# RG11A : le remplisseur écrit le rédigé comme une étape « sur demande différée »
# (on-demand + processus arrière-plan). Mode off reste interdit.
_DEFERRED: ContextVar[bool] = ContextVar("naviguide_llm_deferred", default=False)


def mode() -> str:
    raw = (os.environ.get("NAVIGUIDE_LLM_MODE") or "on-demand").strip().lower().replace("_", "-")
    return raw if raw in _MODES else "on-demand"


def in_background() -> bool:
    """Vrai dans une tâche d'arrière-plan (préchauffage, remplisseur) — ou dans un processus lancé avec
    NAVIGUIDE_LLM_BACKGROUND=1 (le remplisseur du stock)."""
    if (os.environ.get("NAVIGUIDE_LLM_BACKGROUND") or "").strip() in ("1", "true", "yes"):
        return True
    return bool(_BACKGROUND.get())


@contextmanager
def background():
    """À poser autour d'un travail d'arrière-plan : sous le mode on-demand, la cascade n'appelle rien."""
    token = _BACKGROUND.set(True)
    try:
        yield
    finally:
        _BACKGROUND.reset(token)


@contextmanager
def deferred_demand():
    """Écriture du rédigé par le remplisseur : étape « sur demande différée ».

    Autorise le palier *write* même si le processus est marqué arrière-plan,
    tant que le mode n'est pas `off`. Les paliers fast / judge restent bloqués.
    """
    token = _DEFERRED.set(True)
    try:
        yield
    finally:
        _DEFERRED.reset(token)


def llm_allowed_here(tier: str | None = None) -> bool:
    """Le mode autorise-t-il un appel payant ICI (avant même le plafond) ?"""
    m = mode()
    if m == "off":
        return False
    if m == "all":
        return True
    if _DEFERRED.get() and (tier is None or normalize_tier(tier) == "write"):
        return True
    return not in_background()

# $/million tokens (entrée, sortie) — plan § 0.
PRICES_PER_M = {
    "fast": (0.06, 0.24),
    "write": (0.30, 0.90),
    "deep": (1.00, 3.00),
    "judge": (1.00, 3.00),
}

DEFAULT_MODELS = {
    "fast": "nvidia/Nemotron-3_5-Lightning",
    "write": "nvidia/nemotron-3-super-120b-a12b",
    "deep": "nvidia/Nemotron-3-Ultra-550b-a55b",
    "judge": "nvidia/Nemotron-3-Ultra-550b-a55b",
}

DEFAULT_MAX_TOKENS = {
    "fast": 512,
    "write": 400,
    # NVIDIA Ultra Day-0: max_tokens caps thinking + answer; 512 is too small
    # if enable_thinking stays on. Official Ultra example uses 2048.
    "deep": 2048,
    "judge": 2048,
}

SOURCE_FOR_TIER = {
    "fast": "nemotron-lightning",
    "write": "nemotron-super",
    "deep": "nemotron-ultra",
    "judge": "nemotron-ultra",
}

_ENV_CAP = {
    "fast": "NAVIGUIDE_LLM_DAILY_TOKENS_FAST",
    "write": "NAVIGUIDE_LLM_DAILY_TOKENS_WRITE",
    "deep": "NAVIGUIDE_LLM_DAILY_TOKENS_DEEP",
    "judge": "NAVIGUIDE_LLM_DAILY_TOKENS_JUDGE",
}
_ENV_MODEL = {
    "fast": "NAVIGUIDE_TF_MODEL_FAST",
    "write": "NAVIGUIDE_TF_MODEL_WRITE",
    "deep": "NAVIGUIDE_TF_MODEL_DEEP",
    "judge": "NAVIGUIDE_TF_MODEL_JUDGE",
}

_LOCK = threading.Lock()


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def normalize_tier(tier: str | None) -> str:
    t = (tier or "write").strip().lower()
    return t if t in TIERS else "write"


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def daily_cap(tier: str) -> int:
    t = normalize_tier(tier)
    return _env_int(_ENV_CAP[t], DEFAULT_CAPS[t])


def model_for(tier: str) -> str:
    t = normalize_tier(tier)
    return (os.environ.get(_ENV_MODEL[t]) or DEFAULT_MODELS[t]).strip() or DEFAULT_MODELS[t]


def max_tokens_for(tier: str) -> int:
    t = normalize_tier(tier)
    return _env_int(f"NAVIGUIDE_TF_MAX_TOKENS_{t.upper()}", DEFAULT_MAX_TOKENS[t]) or DEFAULT_MAX_TOKENS[t]


def source_for(tier: str) -> str:
    return SOURCE_FOR_TIER[normalize_tier(tier)]


def estimate_usd(tier: str, prompt_tokens: int, completion_tokens: int) -> float:
    inn, out = PRICES_PER_M[normalize_tier(tier)]
    usd = (max(0, int(prompt_tokens)) / 1_000_000.0) * inn + (
        max(0, int(completion_tokens)) / 1_000_000.0
    ) * out
    return round(usd, 8)


def _empty() -> dict[str, Any]:
    return {"tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "calls": 0, "usd": 0.0}


def _kv_key(tier: str, day: str | None = None) -> str:
    return f"{day or today()}:{normalize_tier(tier)}"


def get_usage(tier: str, day: str | None = None) -> dict[str, Any]:
    import pearl_store  # noqa: PLC0415

    hit = pearl_store.kv_get(NS, _kv_key(tier, day))
    val = (hit or {}).get("value")
    if not isinstance(val, dict):
        return _empty()
    out = _empty()
    for k in out:
        try:
            out[k] = int(val[k]) if k != "usd" else float(val[k])
        except (TypeError, ValueError, KeyError):
            pass
    if out["tokens"] <= 0:
        out["tokens"] = int(out["prompt_tokens"]) + int(out["completion_tokens"])
    return out


def allow(tier: str) -> bool:
    """False si le mode l'interdit ici (off, ou arrière-plan en on-demand), ou si le compteur du jour est au
    plafond — dans les deux cas : aucun appel réseau, la cascade rend `source=budget`."""
    if not llm_allowed_here(tier):
        return False
    used = get_usage(tier)
    return int(used["tokens"]) < daily_cap(tier)


def record(tier: str, prompt_tokens: int, completion_tokens: int) -> dict[str, Any]:
    """Add one successful Token Factory call to today's counter."""
    import pearl_store  # noqa: PLC0415

    t = normalize_tier(tier)
    pt = max(0, int(prompt_tokens))
    ct = max(0, int(completion_tokens))
    add_usd = estimate_usd(t, pt, ct)
    with _LOCK:
        cur = get_usage(t)
        cur["prompt_tokens"] = int(cur["prompt_tokens"]) + pt
        cur["completion_tokens"] = int(cur["completion_tokens"]) + ct
        cur["tokens"] = int(cur["prompt_tokens"]) + int(cur["completion_tokens"])
        cur["calls"] = int(cur["calls"]) + 1
        cur["usd"] = round(float(cur["usd"]) + add_usd, 8)
        pearl_store.kv_put(NS, _kv_key(t), cur)
        return dict(cur)


def remember_source(source: str | None) -> None:
    """Last provider that produced a text (not `cache`, so the UI keeps the model)."""
    import pearl_store  # noqa: PLC0415

    src = (source or "").strip()
    if not src or src == "cache":
        return
    pearl_store.kv_put(LAST_SOURCE_NS, LAST_SOURCE_KEY, src)


def last_source() -> str | None:
    import pearl_store  # noqa: PLC0415

    hit = pearl_store.kv_get(LAST_SOURCE_NS, LAST_SOURCE_KEY)
    val = (hit or {}).get("value")
    return val if isinstance(val, str) and val.strip() else None


def remember_cascade_errors(hops: list[dict[str, str]]) -> None:
    """Every hop that failed in the last cascade (TF HTTP body first)."""
    import pearl_store  # noqa: PLC0415

    clean: list[dict[str, str]] = []
    for hop in hops or []:
        if not isinstance(hop, dict):
            continue
        prov = str(hop.get("provider") or "").strip()
        why = " ".join(str(hop.get("reason") or "").split())[:240]
        if prov or why:
            clean.append({"provider": prov, "reason": why})
    if not clean:
        return
    pearl_store.kv_put(LAST_SOURCE_NS, LAST_ERROR_KEY, clean)


def remember_cascade_error(provider: str, reason: str) -> None:
    remember_cascade_errors([{"provider": provider, "reason": reason}])


def last_errors() -> list[dict[str, str]] | None:
    import pearl_store  # noqa: PLC0415

    hit = pearl_store.kv_get(LAST_SOURCE_NS, LAST_ERROR_KEY)
    val = (hit or {}).get("value")
    if isinstance(val, list):
        out = [x for x in val if isinstance(x, dict) and (x.get("provider") or x.get("reason"))]
        return out or None
    if isinstance(val, dict) and (val.get("provider") or val.get("reason")):
        return [{"provider": str(val.get("provider") or ""), "reason": str(val.get("reason") or "")}]
    return None


def last_error() -> dict[str, str] | None:
    """Prefer Token Factory so a Lightning HTTP body stays visible after NIM."""
    errs = last_errors()
    if not errs:
        return None
    for item in errs:
        if item.get("provider") == "tokenfactory":
            return item
    return errs[0]


def _tavily_empty() -> dict[str, Any]:
    return {"credits": 0, "calls": 0}


def _tavily_key(day: str | None = None) -> str:
    return f"{day or today()}:tavily"


def tavily_usage(day: str | None = None) -> dict[str, Any]:
    """Credits consumed today (1 credit per Tavily HTTP call, lot L3)."""
    import pearl_store  # noqa: PLC0415

    hit = pearl_store.kv_get(NS, _tavily_key(day))
    val = (hit or {}).get("value")
    if not isinstance(val, dict):
        return _tavily_empty()
    out = _tavily_empty()
    for k in out:
        try:
            out[k] = int(val[k])
        except (TypeError, ValueError, KeyError):
            pass
    return out


DEFAULT_TAVILY_CAP = 80


def tavily_cap() -> int:
    return _env_int("NAVIGUIDE_TAVILY_DAILY_CREDITS", DEFAULT_TAVILY_CAP)


def allow_tavily() -> bool:
    """False when today's Tavily credits are at/over the cap — no network."""
    return int(tavily_usage()["credits"]) < tavily_cap()


def record_tavily(credits: int = 1) -> dict[str, Any]:
    """Add one Tavily search/extract call (1 credit / call)."""
    import pearl_store  # noqa: PLC0415

    add = max(0, int(credits))
    with _LOCK:
        cur = tavily_usage()
        cur["credits"] = int(cur["credits"]) + add
        cur["calls"] = int(cur["calls"]) + 1
        pearl_store.kv_put(NS, _tavily_key(), cur)
        return dict(cur)


def status() -> dict[str, Any]:
    """Shape for `/ici/warm/status` → `llm: {tier: {tokens, calls, usd}}`."""
    out: dict[str, Any] = {}
    for t in TIERS:
        u = get_usage(t)
        out[t] = {
            "tokens": int(u["tokens"]),
            "calls": int(u["calls"]),
            "usd": float(u["usd"]),
        }
    tv = tavily_usage()
    out["tavily"] = {"credits": int(tv["credits"]), "calls": int(tv["calls"])}
    src = last_source()
    if src:
        out["lastSource"] = src
    errs = last_errors()
    if errs:
        out["lastErrors"] = errs
        out["lastError"] = last_error()
    return out
