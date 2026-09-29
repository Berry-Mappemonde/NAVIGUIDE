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

TIERS = ("fast", "write", "judge")

# Tokens / jour — resserrés le 28 sept. (facture Nebius du mois : 6,58 $ sur 60 $ de crédits, dont 5,19 $ de
# Nemotron Ultra pour un badge que personne ne voyait) : fast ≈ 0,05 $/j, write ≈ 0,08 $/j, judge 0.
DEFAULT_CAPS = {
    "fast": 200_000,
    "write": 150_000,
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


def llm_allowed_here() -> bool:
    """Le mode autorise-t-il un appel payant ICI (avant même le plafond) ?"""
    m = mode()
    if m == "off":
        return False
    if m == "all":
        return True
    return not in_background()

# $/million tokens (entrée, sortie) — plan § 0.
PRICES_PER_M = {
    "fast": (0.06, 0.24),
    "write": (0.30, 0.90),
    "judge": (1.00, 3.00),
}

DEFAULT_MODELS = {
    "fast": "nvidia/Nemotron-3_5-Lightning",
    "write": "nvidia/nemotron-3-super-120b-a12b",
    "judge": "nvidia/Nemotron-3-Ultra-550b-a55b",
}

DEFAULT_MAX_TOKENS = {
    "fast": 256,
    "write": 400,
    "judge": 512,
}

SOURCE_FOR_TIER = {
    "fast": "nemotron-lightning",
    "write": "nemotron-super",
    "judge": "nemotron-ultra",
}

_ENV_CAP = {
    "fast": "NAVIGUIDE_LLM_DAILY_TOKENS_FAST",
    "write": "NAVIGUIDE_LLM_DAILY_TOKENS_WRITE",
    "judge": "NAVIGUIDE_LLM_DAILY_TOKENS_JUDGE",
}
_ENV_MODEL = {
    "fast": "NAVIGUIDE_TF_MODEL_FAST",
    "write": "NAVIGUIDE_TF_MODEL_WRITE",
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
    if not llm_allowed_here():
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
    return out
