"""Short ici() story. Cascade Token Factory → OpenRouter → Claude → rules.

Order (porteur, 20 sept.): Token Factory first (hackathon), then NIM
(`integrate.api.nvidia.com`), then OpenRouter, then Claude. Never Tavily here.
Thinking OFF. No figure invented: filter_numbers on every LLM sentence.
Lot L6 : `translate(text, lang)` (Lightning) pour l'anglais — mêmes gardes.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

import llm_budget

_DIR = Path(__file__).resolve().parent
_BACKEND_ENV = _DIR.parents[1] / "backend" / ".env"
load_dotenv()
if _BACKEND_ENV.exists():
    load_dotenv(_BACKEND_ENV, override=False)

TOKENFACTORY_BASE = (
    os.environ.get("NAVIGUIDE_TF_BASE") or "https://api.tokenfactory.nebius.com/v1"
).rstrip("/")
TOKENFACTORY_URL = f"{TOKENFACTORY_BASE}/chat/completions"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
NIM_MODEL = "openai/gpt-oss-20b"
OR_MODEL = os.environ.get("OPENROUTER_MODEL") or "openai/gpt-4o-mini"
CLAUDE_MODEL = "claude-haiku-4-5"
MAX_TOKENS = 400
TIMEOUT = httpx.Timeout(25.0, connect=8.0)
DEFAULT_PROVIDERS = ("tokenfactory", "nim", "openrouter", "claude")
CACHE_NS = "llm-cache"
CACHE_TTL_S = 24 * 3600.0
TF_PARALLEL_DEFAULT = 4
KNOWN_SOURCES = frozenset({
    "nemotron-lightning", "nemotron-super", "nemotron-ultra",
    "openrouter", "claude", "rules", "budget", "cache",
})

_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
_INFLIGHT: dict[str, asyncio.Future] = {}
_INFLIGHT_GUARD: asyncio.Lock | None = None
_TF_SEMA: asyncio.Semaphore | None = None

_FENCE_RE = re.compile(r"^```(?:json|text)?\s*|\s*```$", re.M)
_THINK_BLOCK_RE = re.compile(r"<think\b[^>]*>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINK_OPEN_RE = re.compile(r"<think\b[^>]*>.*\Z", re.IGNORECASE | re.DOTALL)
_PROMPT_LEAK_RE = re.compile(
    r"translate a sailing-log paragraph|Keep every number"
    r"|You write the text of one card"
    r"|Tu écris le texte d.une carte"
    r"|present a port of call"
    r"|Tu présentes une escale"
    r"|sailing crew arriving"
    r"|THREE plain sentences"
    r"|TROIS phrases simples"
    r"|analyze user input"
    r"|here'?s a thinking process"
    r"|thinking process:"
    # Formes vues le 22 sept. (fiche Pointe-à-Pitre + journal) et traductions.
    r"|Input:\s*A large JSON"
    r"|large JSON object"
    r"|Un grand objet JSON"
    r"|Un gros objet JSON"
    r"|What'?s for the boat"
    r"|What is there for the boat"
    r"|ce qu.il y a pour le bateau"
    r"|Qu.y a-t-il pour le bateau"
    r"|\bTask\s*:"
    r"|T[âa]che\s*:"
    r"|Present a scale stop"
    r"|Present a stop/escales"
    r"|Present a stop to"
    r"|You are the logbook"
    r"|Tu es le journal de bord"
    r"|ONLY the JSON of facts"
    r"|SEUL JSON de faits",
    re.IGNORECASE,
)
_PREAMBLE_LEAD_RES = (
    re.compile(
        r"^\s*\*\*[^*]*(?:analyze\s+user\s+input|task\s*:|constraints?\s*:|"
        r"request\s*:|thinking\s+off)[^*]*\*\*\s*",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*analyze\s+user\s+input:?\s*", re.IGNORECASE),
    re.compile(r"^\s*task\s*:\s*[^\n]*\n?", re.IGNORECASE),
    re.compile(r"^\s*[-•*]\s*task\s*:\s*[^\n]*\n?", re.IGNORECASE),
    re.compile(r"^\s*t[âa]che\s*:\s*[^\n]*\n?", re.IGNORECASE),
    re.compile(r"^\s*[-•*]\s*t[âa]che\s*:\s*[^\n]*\n?", re.IGNORECASE),
    re.compile(r"^\s*input\s*:\s*[^\n]*\n?", re.IGNORECASE),
    re.compile(r"^\s*entr[ée]e\s*:\s*[^\n]*\n?", re.IGNORECASE),
    re.compile(r"^\s*constraints?\s*:\s*[^\n]*\n?", re.IGNORECASE),
    re.compile(r"^\s*request\s*:\s*[^\n]*\n?", re.IGNORECASE),
    re.compile(r"^\s*thinking\s+off:?\s*", re.IGNORECASE),
    re.compile(r"^\s*wait,\s+[^.!?…\n]*[.!?…]?\s*", re.IGNORECASE),
    re.compile(r"^\s*let\s+me\s+[^.!?…\n]*[.!?…]?\s*", re.IGNORECASE),
    re.compile(r"^\s*the\s+user\s+says\s+[^.!?…\n]*[.!?…]?\s*", re.IGNORECASE),
    re.compile(r"^\s*here'?s a thinking process\s*:?\s*[^.!?…\n]*[.!?…]?\s*", re.IGNORECASE),
)


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def nvidia_key() -> str:
    return _env("NVIDIA_API_KEY")


def openrouter_key() -> str:
    return _env("OPENROUTER_API_KEY")


def anthropic_key() -> str:
    return _env("ANTHROPIC_API_KEY")


def nebius_key() -> str:
    return _env("NEBIUS_API_KEY")


def providers() -> list[str]:
    raw = (_env("NAVIGUIDE_LLM_PROVIDERS") or ",".join(DEFAULT_PROVIDERS)).lower()
    alias = {
        "tf": "tokenfactory",
        "tokenfactory": "tokenfactory",
        "nebius": "tokenfactory",
        "nemotron": "tokenfactory",
        "openrouter": "openrouter",
        "or": "openrouter",
        "claude": "claude",
        "anthropic": "claude",
        "nim": "nim",
        "nvidia": "nim",
    }
    out: list[str] = []
    for part in raw.split(","):
        name = alias.get(part.strip())
        if name and name not in out:
            out.append(name)
    return out or list(DEFAULT_PROVIDERS)


def reset_runtime() -> None:
    """Tests: drop in-flight futures and the Token Factory semaphore."""
    global _TF_SEMA, _INFLIGHT_GUARD
    _INFLIGHT.clear()
    _TF_SEMA = None
    _INFLIGHT_GUARD = None


def _inflight_lock() -> asyncio.Lock:
    global _INFLIGHT_GUARD
    if _INFLIGHT_GUARD is None:
        _INFLIGHT_GUARD = asyncio.Lock()
    return _INFLIGHT_GUARD


def _tf_limiter() -> asyncio.Semaphore:
    global _TF_SEMA
    if _TF_SEMA is None:
        n = 4
        try:
            n = max(1, int(_env("NAVIGUIDE_TF_PARALLEL") or TF_PARALLEL_DEFAULT))
        except ValueError:
            n = TF_PARALLEL_DEFAULT
        _TF_SEMA = asyncio.Semaphore(n)
    return _TF_SEMA


def _cache_ttl_s() -> float:
    raw = _env("NAVIGUIDE_LLM_CACHE_TTL_S")
    if not raw:
        return CACHE_TTL_S
    try:
        return max(0.0, float(raw))
    except ValueError:
        return CACHE_TTL_S


def prompt_cache_key(
    system: str, user: str, tier: str, *, online: bool = False, max_tokens: int | None = None,
) -> str:
    model = llm_budget.model_for(tier)
    extra = f"\n{max_tokens}" if max_tokens else ""
    blob = f"{tier}\n{model}\n{int(online)}\n{','.join(providers())}\n{system}\n{user}{extra}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _numbers(text: str) -> set[str]:
    out: set[str] = set()
    for m in _NUM_RE.findall(text or ""):
        try:
            out.add(format(float(m.replace(",", ".")), "g"))
        except ValueError:
            continue
    return out


def filter_numbers(answer: str, facts: Any) -> tuple[str, int]:
    """Drop every sentence whose figures are not already in `facts`.

    Same contract as logbook_chat.filter_numbers: a year or a time present
    in the facts is allowed. Returns (text, dropped).
    """
    blob = facts if isinstance(facts, str) else json.dumps(facts, ensure_ascii=False, default=str)
    allowed = _numbers(blob)
    kept, dropped = [], 0
    for s in _SENT_SPLIT_RE.split(answer or ""):
        s = s.strip()
        if not s:
            continue
        nums = _numbers(s)
        if nums and not nums.issubset(allowed):
            dropped += 1
            continue
        kept.append(s)
    return " ".join(kept), dropped


def _apply_filter(text: str, facts: Any, *, keep_if_empty: bool = False) -> str:
    if facts is None:
        return text
    out, _ = filter_numbers(text, facts)
    if not out and keep_if_empty:
        return text
    return out


def _estimate_tokens(system: str, user: str, text: str) -> tuple[int, int]:
    prompt = max(1, (len(system) + len(user) + 8) // 4)
    completion = max(1, (len(text) + 3) // 4) if text else 0
    return prompt, completion


def _usage_tokens(data: dict[str, Any] | None, system: str, user: str, text: str) -> tuple[int, int]:
    usage = (data or {}).get("usage") or {}
    try:
        pt = int(usage.get("prompt_tokens") or 0)
        ct = int(usage.get("completion_tokens") or 0)
    except (TypeError, ValueError):
        pt = ct = 0
    if pt <= 0 and ct <= 0:
        return _estimate_tokens(system, user, text)
    return max(0, pt), max(0, ct)


def slim_event(body: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(body or {})
    raw.pop("tavily", None)
    raw["tavily"] = None
    raw.setdefault("nvidia", None)
    blob = json.dumps(raw, ensure_ascii=False, default=str)
    if len(blob) > 4000:
        blob = blob[:4000]
        raw = {"event": raw.get("event"), "truncated": True, "json": blob, "tavily": None}
    return raw


def need_page(body: dict[str, Any] | None) -> tuple[bool, str | None]:
    raw = body or {}
    url = raw.get("pageUrl") or raw.get("page_url")
    if not raw.get("needPage") and not raw.get("need_page"):
        return False, None
    if not isinstance(url, str):
        return False, None
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        return False, None
    return True, url


def has_skipper_orders(body: dict[str, Any] | None) -> bool:
    """True when the event carries the skipper thresholds that made it switch."""
    skipper = (body or {}).get("skipper")
    if not isinstance(skipper, dict):
        return False
    used = skipper.get("used")
    return isinstance(used, list) and any(isinstance(u, dict) and "value" in u for u in used)


def build_prompt(body: dict[str, Any], page_url: str | None = None) -> tuple[str, str]:
    """Sober card text (revue du porteur, 19 sept. 2026) : the fact and its
    source, one or two sentences, nothing about the machinery."""
    lang = (body.get("lang") or "fr").lower()
    en = lang.startswith("en")
    system = (
        "You write the text of one card shown to a sailor, from a JSON event already collected. "
        "ONE or TWO plain sentences: the fact, the figure(s) from the JSON, the source or model "
        "(e.g. EMODnet, GFS, official port of entry). "
        "Forbidden: any word about the machinery — judge, judged, classified, severity, identifier, "
        "event type, reason, playhead, DOI, 'no additional information', the boat's name, length or draft, "
        "titles, lists, bold. Never invent wind, rain, or admin gold. Never fill a null. "
        "Thinking OFF. No tools. No world search."
        if en else
        "Tu écris le texte d’une carte montrée à un marin, à partir d’un JSON d’événement déjà collecté. "
        "UNE ou DEUX phrases simples : le fait, le ou les chiffres du JSON, la source ou le modèle "
        "(EMODnet, GFS, port d’entrée officiel…). "
        "Interdit : tout mot sur la machinerie — juge, jugé, classé, sévérité, identifiant, type d’événement, "
        "raison, playhead, DOI, « aucune information supplémentaire », le nom, la longueur ou le tirant d’eau "
        "du bateau, les titres, les listes, le gras. N’invente ni vent, ni pluie, ni Gold admin. "
        "Ne remplis jamais un null. Thinking OFF. Pas d’outil. Pas de recherche monde."
    )
    if has_skipper_orders(body):
        # The threshold that made the card switch, once, in passing.
        system += (
            " If skipper.used holds the threshold that triggered this card, say it once in passing "
            "(e.g. 'for a limit set at 15 m'). No other number."
            if en else
            " Si skipper.used contient le seuil qui a déclenché cette carte, dis-le une fois, en passant "
            "(ex. « pour un seuil fixé à 15 m »). Aucun autre chiffre."
        )
    extra = ""
    if page_url:
        extra = (
            f"\nRead only this official page already in the pack: {page_url}. Do not search the world."
            if en else
            f"\nLis seulement cette page officielle déjà dans le sac : {page_url}. Ne cherche pas le monde."
        )
    user = (
        f"{'Event JSON' if en else 'JSON d’événement'} (tavily is always null):\n"
        f"{json.dumps(slim_event(body), ensure_ascii=False, default=str)}\n"
        f"{extra}"
    )
    return system, user


def _strip_think(txt: str) -> str:
    """Drop <think>…</think>; an unclosed <think> cuts from that tag."""
    s = _THINK_BLOCK_RE.sub("", txt or "")
    return _THINK_OPEN_RE.sub("", s).strip()


def _strip_preamble(txt: str) -> str:
    """Drop a leading model-meta preamble until the first real sentence."""
    s = (txt or "").strip()
    changed = True
    while s and changed:
        changed = False
        for pat in _PREAMBLE_LEAD_RES:
            m = pat.match(s)
            if m:
                s = s[m.end():].strip()
                changed = True
                break
    return s


def _clean_text(txt: str | None) -> str:
    s = _strip_think(txt or "")
    s = _FENCE_RE.sub("", s.strip()).strip()
    s = _strip_preamble(s)
    if _PROMPT_LEAK_RE.search(s):
        return ""
    return s


# Sentences about the machinery never reach the visitor (revue du 19 sept.).
_META_RE = re.compile(
    r"(\bjug[eé]e?s?\b|\bjuge\b|\bclass[ée]e?s?\b|classif|\bidentifiant|\bidentifier\b|\bID\b|"
    r"s[ée]v[ée]rit|\bseverity\b|\bplayhead\b|\bDOI\b|aucune (?:information|donn[ée]e)|"
    r"no (?:additional|further|extra) (?:information|data|details?)|is (?:not )?(?:provided|available) in this report|"
    r"n[’']est (?:pas )?(?:fournie?|disponible)s? dans ce rapport|\bevent type\b|type d[’']?[ée]v[ée]nement|"
    r"\bLOA\b|tirant d[’']eau|\bdraft\b|briefing nautique|skipper\.used|r[èe]gles? de croisi[èe]re|cruise rules|"
    r"\bwatch\b|\bimm[ée]diate\b|d[ée]cision a [ée]t[ée] prise|the decision was taken|"
    r"analyze user input|thinking off|wait, let me|translate a sailing-log)",
    re.IGNORECASE,
)
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[^\s])")
_MD_RE = re.compile(r"[*_#>`]+")
MAX_SENTENCES = 2
MAX_CHARS = 320


def _is_en(lang: str | None) -> bool:
    return str(lang or "").lower().startswith("en")


TRANSLATE_SYSTEM = (
    "You translate a sailing-log paragraph from French to English. "
    "Keep every number, unit, proper name, date and [[ev:…]] / [[ch:…]] tag exactly as written. "
    "Do not add, drop or invent a figure. No title, no list, no bold. Thinking OFF."
)


def _translate_max_tokens(text: str, override: int | None) -> int:
    if override:
        return max(32, int(override))
    return min(1200, max(256, (len(text or "") // 2) + 80))


async def translate(
    text: str,
    lang: str,
    client: httpx.AsyncClient | None = None,
    *,
    facts: Any = None,
    max_tokens: int | None = None,
) -> tuple[str, str]:
    """U9: FR → EN via Lightning (`tier=fast`). Numbers, names, dates stay.

    `filter_numbers` compares the translation to the source text (or `facts`).
    Other languages are a no-op (`source=rules`). Display label: i18n
    `storySourceLightning` — « Nemotron 3.5 Lightning · Token Factory ».
    """
    src = (text or "").strip()
    if not src:
        return "", "rules"
    if not _is_en(lang):
        return src, "rules"
    user = f"French text:\n{src}"
    out, source = await cascade_text(
        TRANSLATE_SYSTEM,
        user,
        client,
        tier="fast",
        fallback=src,
        facts=facts if facts is not None else src,
        max_tokens=_translate_max_tokens(src, max_tokens),
    )
    cleaned = _clean_text(out)
    if not cleaned:
        return (_clean_text(src) or ""), "rules"
    return cleaned, source


def _is_title(line: str) -> bool:
    """A heading (« Briefing nautique – La Rochelle ») : short, no sentence end."""
    s = line.strip().rstrip(":")
    return bool(s) and len(s) < 80 and not re.search(r"[.!?…]$", s)


def tidy_story(
    text: str | None,
    fallback: str | None = None,
    *,
    max_sentences: int = MAX_SENTENCES,
    max_chars: int = MAX_CHARS,
) -> str:
    """Keep the fact, drop the machinery. Empty → the local phrase (or "").
    Cards keep the defaults (2 sentences); an escale paragraph asks for more."""
    lines = [
        re.sub(r"^\s*(?:[-•*]|\d+[.)])\s+", "", _MD_RE.sub("", ln)).strip()
        for ln in _clean_text(text).split("\n")
    ]
    raw = " ".join(ln for ln in lines if ln and not _is_title(ln))
    raw = re.sub(r"\s{2,}", " ", raw).strip()
    if not raw:
        return (fallback or "").strip()
    kept = [s.strip() for s in _SENT_SPLIT_RE.split(raw) if s.strip() and not _META_RE.search(s)]
    out = " ".join(kept[:max_sentences]).strip()
    if len(out) > max_chars:
        cut = out[:max_chars]
        out = cut[: cut.rfind(" ")].rstrip(" ,;:") + "…" if " " in cut else cut
    return out or (fallback or "").strip()


def _openai_text(data: dict[str, Any] | None) -> str:
    """Read message.content only — never reasoning_content (Nemotron thinking)."""
    msg = ((data or {}).get("choices") or [{}])[0].get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return _clean_text(content)
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict):
                if p.get("type") in {"reasoning", "thinking"}:
                    continue
                parts.append(p.get("text") or "")
            elif isinstance(p, str):
                parts.append(p)
        return _clean_text("".join(parts))
    return ""


def _claude_text(data: dict[str, Any] | None) -> str:
    parts = []
    for block in (data or {}).get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text") or "")
        elif isinstance(block, str):
            parts.append(block)
    return _clean_text("\n".join(parts))


async def _call_tokenfactory(
    system: str, user: str, tier: str, client: httpx.AsyncClient,
    *,
    max_tokens: int | None = None,
) -> tuple[str, str]:
    key = nebius_key()
    if not key:
        raise RuntimeError("NEBIUS_API_KEY missing")
    t = llm_budget.normalize_tier(tier)
    model = llm_budget.model_for(t)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens or llm_budget.max_tokens_for(t),
        "temperature": 0.4,
        "stream": False,
        "reasoning_effort": "low",
        "chat_template_kwargs": {"thinking": False},
    }
    async with _tf_limiter():
        r = await client.post(
            TOKENFACTORY_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
    if r.status_code >= 400:
        raise RuntimeError(f"tokenfactory HTTP {r.status_code}")
    data = r.json()
    text = _openai_text(data)
    if not text:
        raise RuntimeError("tokenfactory empty")
    pt, ct = _usage_tokens(data, system, user, text)
    llm_budget.record(t, pt, ct)
    source = llm_budget.source_for(t)
    llm_budget.remember_source(source)
    return text, source


async def _call_nim(system: str, user: str, client: httpx.AsyncClient) -> tuple[str, str]:
    key = nvidia_key()
    if not key:
        raise RuntimeError("NVIDIA_API_KEY missing")
    payload = {
        "model": NIM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": MAX_TOKENS,
        "stream": False,
        "temperature": 0.6,
        "top_p": 0.7,
        "reasoning_effort": "low",
        "chat_template_kwargs": {"thinking": False},
    }
    r = await client.post(
        NVIDIA_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"nvidia HTTP {r.status_code}")
    text = _openai_text(r.json())
    if not text:
        raise RuntimeError("nvidia empty")
    return text, f"nvidia-{NIM_MODEL.split('/')[-1]}"


async def _call_openrouter(
    system: str, user: str, client: httpx.AsyncClient, *, online: bool,
    max_tokens: int | None = None,
) -> tuple[str, str]:
    key = openrouter_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    model = f"{OR_MODEL}:online" if online else OR_MODEL
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens or MAX_TOKENS,
        "temperature": 0.4,
    }
    r = await client.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"openrouter HTTP {r.status_code}")
    text = _openai_text(r.json())
    if not text:
        raise RuntimeError("openrouter empty")
    llm_budget.remember_source("openrouter")
    return text, "openrouter"


async def _call_claude(
    system: str, user: str, client: httpx.AsyncClient, *, max_tokens: int | None = None,
) -> tuple[str, str]:
    key = anthropic_key()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY missing")
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens or MAX_TOKENS,
        "temperature": 0,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    r = await client.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=payload,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"claude HTTP {r.status_code}")
    text = _claude_text(r.json())
    if not text:
        raise RuntimeError("claude empty")
    llm_budget.remember_source("claude")
    return text, "claude"


def _cache_get(key: str) -> tuple[str, str] | None:
    import pearl_store  # noqa: PLC0415

    ttl = _cache_ttl_s()
    if ttl <= 0:
        return None
    hit = pearl_store.kv_get(CACHE_NS, key, ttl)
    val = (hit or {}).get("value")
    if not isinstance(val, dict):
        return None
    text = val.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    cleaned = _clean_text(text)
    if not cleaned:
        pearl_store.kv_delete(CACHE_NS, key)
        return None
    if cleaned != text:
        pearl_store.kv_put(CACHE_NS, key, {"text": cleaned, "source": val.get("source") or "cache"})
    return cleaned, "cache"


def _cache_put(key: str, text: str, source: str) -> None:
    import pearl_store  # noqa: PLC0415

    if not text or source in {"budget", "rules"}:
        return
    pearl_store.kv_put(CACHE_NS, key, {"text": text, "source": source})


async def _cascade_once(
    system: str,
    user: str,
    http: httpx.AsyncClient,
    *,
    online: bool,
    tier: str,
    facts: Any,
    fallback: str | None,
    max_tokens: int | None = None,
) -> tuple[str, str]:
    cache_key = prompt_cache_key(system, user, tier, online=online, max_tokens=max_tokens)
    hit = _cache_get(cache_key)
    if hit:
        return hit[0], "cache"
    if not llm_budget.allow(tier):
        text = _apply_filter(fallback or "", facts if facts is not None else user, keep_if_empty=True)
        return text, "budget"

    last = "no_llm_backend"
    steps: list[Any] = []
    for name in providers():
        if name == "tokenfactory":
            steps.append(lambda: _call_tokenfactory(system, user, tier, http, max_tokens=max_tokens))
        elif name == "openrouter":
            steps.append(lambda: _call_openrouter(system, user, http, online=online, max_tokens=max_tokens))
        elif name == "claude":
            steps.append(lambda: _call_claude(system, user, http, max_tokens=max_tokens))
        elif name == "nim":
            steps.append(lambda: _call_nim(system, user, http))

    for step in steps:
        try:
            text, source = await step()
            text = _apply_filter(text, facts if facts is not None else user)
            if _clean_text(text):
                if source in KNOWN_SOURCES:
                    _cache_put(cache_key, text, source)
                return text, source if source in KNOWN_SOURCES else (
                    "openrouter" if source.startswith("openrouter") else source
                )
            last = f"{source} empty"
        except Exception as exc:
            last = str(exc)[:160]

    if fallback is not None:
        text = _apply_filter(fallback, facts if facts is not None else user, keep_if_empty=True)
        return text, "rules"
    raise RuntimeError(last)


async def cascade_text(
    system: str,
    user: str,
    client: httpx.AsyncClient | None = None,
    *,
    online: bool = False,
    tier: str = "write",
    fallback: str | None = None,
    facts: Any = None,
    max_tokens: int | None = None,
) -> tuple[str, str]:
    """Cache SQLite → Token Factory → OpenRouter → Claude → rules.

    Returns `(text, source)` with source in KNOWN_SOURCES. `fallback is None`
    keeps the old contract (raise when no backend). A string fallback — even
    empty — yields `source=rules` after every provider failed. Never Tavily.
    """
    own = client is None
    http = client or httpx.AsyncClient(timeout=TIMEOUT)
    t = llm_budget.normalize_tier(tier)
    key = prompt_cache_key(system, user, t, online=online, max_tokens=max_tokens)
    try:
        async with _inflight_lock():
            existing = _INFLIGHT.get(key)
            if existing is not None:
                waiter = True
            else:
                waiter = False
                loop = asyncio.get_running_loop()
                fut: asyncio.Future = loop.create_future()
                _INFLIGHT[key] = fut
        if waiter:
            return await existing
        try:
            try:
                result = await _cascade_once(
                    system, user, http, online=online, tier=t, facts=facts, fallback=fallback,
                    max_tokens=max_tokens,
                )
                if not fut.done():
                    fut.set_result(result)
            except Exception as exc:
                if not fut.done():
                    fut.set_exception(exc)
            return await fut
        finally:
            async with _inflight_lock():
                if _INFLIGHT.get(key) is fut:
                    _INFLIGHT.pop(key, None)
    finally:
        if own:
            await http.aclose()


async def write_story(
    body: dict[str, Any] | None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Cascade cible (lot L1) : Token Factory → OpenRouter → Claude → règles.

    Langue EN (lot L6 / U9) : le récit est d'abord rédigé en FR, puis traduit
    par Lightning — les nombres restent ceux des faits, jamais un chiffre nouveau.
    """
    event = slim_event(body)
    want_en = _is_en((body or {}).get("lang"))
    if want_en:
        event = {**event, "lang": "fr"}
    page, page_url = need_page(body)
    system, user = build_prompt(event if not page else {**event, "pageUrl": page_url}, page_url)
    fallback = (body or {}).get("phrase") if isinstance((body or {}).get("phrase"), str) else None
    try:
        text, source = await cascade_text(
            system, user, client, online=page, tier="write",
            fallback=fallback if fallback is not None else "",
            facts=event,
        )
    except Exception as exc:
        return {
            "status": "failed",
            "reason": str(exc)[:160],
            "cascade": "tokenfactory-openrouter-claude",
            "tavily": None,
            "nvidia": None,
            "text": None,
            "source": "rules",
            "engine": None,
        }
    tidy = tidy_story(text, fallback)
    if not tidy:
        return {
            "status": "failed",
            "reason": f"{source} only machinery",
            "cascade": "tokenfactory-openrouter-claude",
            "tavily": None,
            "nvidia": None,
            "text": None,
            "source": source,
            "engine": source,
        }
    used_local = tidy == (fallback or "").strip() and tidy != _clean_text(text).strip()
    if want_en and tidy and not used_local:
        tidy, source = await translate(tidy, "en", client, facts=tidy)
        if not tidy:
            return {
                "status": "failed",
                "reason": f"{source} empty translation",
                "cascade": "tokenfactory-openrouter-claude",
                "tavily": None,
                "nvidia": None,
                "text": None,
                "source": source,
                "engine": source,
            }
    engine = source
    if used_local:
        engine = f"{source}+local"
    return {
        "status": "ready",
        "text": tidy,
        "engine": engine,
        "source": source,
        "cascade": "tokenfactory-openrouter-claude",
        "tavily": None,
        "nvidia": source if source.startswith("nemotron-") else engine,
    }
