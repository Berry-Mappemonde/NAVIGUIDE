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


def build_prompt(body: dict[str, Any], page_url: str | None = None) -> tuple[str, str]:
    lang = (body.get("lang") or "fr").lower()
    en = lang.startswith("en")
    system = (
        "You write one short nautical briefing from a JSON event already collected. "
        "4 to 6 sentences. Cite kind / period / DOI if present. "
        "Never invent wind, rain, or admin gold. Never fill a null. "
        "Thinking OFF. No tools. No world search."
        if en else
        "Tu rédiges un bref briefing nautique à partir d’un JSON d’événement déjà collecté. "
        "4 à 6 phrases. Cite kind / période / DOI s’ils sont là. "
        "N’invente ni vent, ni pluie, ni Gold admin. Ne remplis jamais un null. "
        "Thinking OFF. Pas d’outil. Pas de recherche monde."
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
        for (step,) in steps:
            try:
                text, engine = await step()
                return {
                    "status": "ready",
                    "text": text,
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
