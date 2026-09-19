"""Short ici() story. Cascade NIM → OpenRouter (± :online) → Claude.

Mirrors backend/app/core/llm.py + judge.complete_json_cascade.
Not Nemotron. Not Token Factory. Not Tavily. Thinking OFF.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

_DIR = Path(__file__).resolve().parent
_BACKEND_ENV = _DIR.parents[1] / "backend" / ".env"
load_dotenv()
if _BACKEND_ENV.exists():
    load_dotenv(_BACKEND_ENV, override=False)

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
NIM_MODEL = "openai/gpt-oss-20b"
OR_MODEL = os.environ.get("OPENROUTER_MODEL") or "openai/gpt-4o-mini"
CLAUDE_MODEL = "claude-haiku-4-5"
MAX_TOKENS = 400
TIMEOUT = httpx.Timeout(25.0, connect=8.0)

_FENCE_RE = re.compile(r"^```(?:json|text)?\s*|\s*```$", re.M)


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def nvidia_key() -> str:
    return _env("NVIDIA_API_KEY")


def openrouter_key() -> str:
    return _env("OPENROUTER_API_KEY")


def anthropic_key() -> str:
    return _env("ANTHROPIC_API_KEY")


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


def _clean_text(txt: str | None) -> str:
    s = _FENCE_RE.sub("", (txt or "").strip()).strip()
    return s


# Sentences about the machinery never reach the visitor (revue du 19 sept.).
_META_RE = re.compile(
    r"(\bjug[eé]e?s?\b|\bjuge\b|\bclass[ée]e?s?\b|classif|\bidentifiant|\bidentifier\b|\bID\b|"
    r"s[ée]v[ée]rit|\bseverity\b|\bplayhead\b|\bDOI\b|aucune (?:information|donn[ée]e)|"
    r"no (?:additional|further|extra) (?:information|data|details?)|is (?:not )?(?:provided|available) in this report|"
    r"n[’']est (?:pas )?(?:fournie?|disponible)s? dans ce rapport|\bevent type\b|type d[’']?[ée]v[ée]nement|"
    r"\bLOA\b|tirant d[’']eau|\bdraft\b|briefing nautique|skipper\.used|r[èe]gles? de croisi[èe]re|cruise rules|"
    r"\bwatch\b|\bimm[ée]diate\b|d[ée]cision a [ée]t[ée] prise|the decision was taken)",
    re.IGNORECASE,
)
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[^\s])")
_MD_RE = re.compile(r"[*_#>`]+")
MAX_SENTENCES = 2
MAX_CHARS = 320


def _is_title(line: str) -> bool:
    """A heading (« Briefing nautique – La Rochelle ») : short, no sentence end."""
    s = line.strip().rstrip(":")
    return bool(s) and len(s) < 80 and not re.search(r"[.!?…]$", s)


def tidy_story(text: str | None, fallback: str | None = None) -> str:
    """Keep the fact, drop the machinery. Empty → the local phrase (or "")."""
    lines = [
        re.sub(r"^\s*(?:[-•*]|\d+[.)])\s+", "", _MD_RE.sub("", ln)).strip()
        for ln in _clean_text(text).split("\n")
    ]
    raw = " ".join(ln for ln in lines if ln and not _is_title(ln))
    raw = re.sub(r"\s{2,}", " ", raw).strip()
    if not raw:
        return (fallback or "").strip()
    kept = [s.strip() for s in _SENT_SPLIT_RE.split(raw) if s.strip() and not _META_RE.search(s)]
    out = " ".join(kept[:MAX_SENTENCES]).strip()
    if len(out) > MAX_CHARS:
        cut = out[:MAX_CHARS]
        out = cut[: cut.rfind(" ")].rstrip(" ,;:") + "…" if " " in cut else cut
    return out or (fallback or "").strip()


def _openai_text(data: dict[str, Any] | None) -> str:
    msg = ((data or {}).get("choices") or [{}])[0].get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return _clean_text(content)
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict):
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
    system: str, user: str, client: httpx.AsyncClient, *, online: bool
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
        "max_tokens": MAX_TOKENS,
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
    return text, "openrouter-online" if online else "openrouter"


async def _call_claude(system: str, user: str, client: httpx.AsyncClient) -> tuple[str, str]:
    key = anthropic_key()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY missing")
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": MAX_TOKENS,
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
    return text, "claude"


async def write_story(
    body: dict[str, Any] | None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """NIM → OR (± :online) → Claude. Never Tavily. Never Nemotron."""
    event = slim_event(body)
    page, page_url = need_page(body)
    system, user = build_prompt(event if not page else {**event, "pageUrl": page_url}, page_url)
    own = client is None
    http = client or httpx.AsyncClient(timeout=TIMEOUT)
    last = "no_llm_backend"
    try:
        if page:
            steps = (
                (lambda: _call_openrouter(system, user, http, online=True),),
                (lambda: _call_openrouter(system, user, http, online=False),),
                (lambda: _call_claude(system, user, http),),
            )
        else:
            steps = (
                (lambda: _call_nim(system, user, http),),
                (lambda: _call_openrouter(system, user, http, online=False),),
                (lambda: _call_claude(system, user, http),),
            )
        fallback = (body or {}).get("phrase") if isinstance((body or {}).get("phrase"), str) else None
        for (step,) in steps:
            try:
                text, engine = await step()
                tidy = tidy_story(text, fallback)
                if not tidy:
                    raise RuntimeError(f"{engine} only machinery")
                if tidy == (fallback or "").strip() and tidy != _clean_text(text).strip():
                    engine = f"{engine}+local"
                return {
                    "status": "ready",
                    "text": tidy,
                    "engine": engine,
                    "cascade": "nim-or-claude",
                    "tavily": None,
                    "nvidia": engine,
                }
            except Exception as exc:
                last = str(exc)[:160]
        return {
            "status": "failed",
            "reason": last,
            "cascade": "nim-or-claude",
            "tavily": None,
            "nvidia": None,
            "text": None,
        }
    finally:
        if own:
            await http.aclose()
