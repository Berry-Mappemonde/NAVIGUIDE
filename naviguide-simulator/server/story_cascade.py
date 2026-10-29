"""Short ici() story. Cascade Token Factory → OpenRouter → Claude → rules.

Order (porteur, 20 sept.): Token Factory first (hackathon), then NIM
(`integrate.api.nvidia.com`), then OpenRouter, then Claude. Never Tavily here.
Thinking OFF. No figure invented: filter_numbers on every LLM sentence.
`translate(text, lang)` (Lightning) pour l'anglais — mêmes gardes.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

import llm_budget
import tf_catalog
from ai_transparency import with_ai_transparency

log = logging.getLogger("naviguide-simulator.story-cascade")

_DIR = Path(__file__).resolve().parent
_BACKEND_ENV = _DIR.parents[1] / "backend" / ".env"
load_dotenv()
if _BACKEND_ENV.exists():
    load_dotenv(_BACKEND_ENV, override=False)

TOKENFACTORY_BASE = (
    os.environ.get("NAVIGUIDE_TF_BASE") or "https://api.tokenfactory.nebius.com/v1"
).rstrip("/")
TOKENFACTORY_URL = f"{TOKENFACTORY_BASE}/chat/completions"
# Nano stays on the EU host even if NAVIGUIDE_TF_BASE points elsewhere.
TOKENFACTORY_EU_BASE = (
    os.environ.get("NAVIGUIDE_TF_BASE_EU")
    or "https://api.tokenfactory.nebius.com/v1"
).rstrip("/")
# Cookbook Ultra: https://api.tokenfactory.us-central1.nebius.com/v1/
TOKENFACTORY_ULTRA_BASE = (
    os.environ.get("NAVIGUIDE_TF_BASE_ULTRA")
    or "https://api.tokenfactory.us-central1.nebius.com/v1"
).rstrip("/")
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
NIM_MODEL = "openai/gpt-oss-20b"
OR_MODEL = os.environ.get("OPENROUTER_MODEL") or "openai/gpt-4o-mini"
CLAUDE_MODEL = "claude-haiku-4-5"
MAX_TOKENS = 400
TIMEOUT = httpx.Timeout(25.0, connect=8.0)
TIMEOUT_ULTRA = httpx.Timeout(45.0, connect=8.0)
DEFAULT_PROVIDERS = ("tokenfactory", "nim", "openrouter", "claude")
CACHE_NS = "llm-cache"
CACHE_TTL_S = 24 * 3600.0
TF_PARALLEL_DEFAULT = 4
KNOWN_SOURCES = frozenset({
    "nemotron-nano", "nemotron-lightning", "nemotron-super", "nemotron-super-vl",
    "nemotron-ultra",
    "openrouter", "claude", "rules", "budget", "cache",
})


def tf_timeout(tier: str) -> httpx.Timeout:
    """Timeout par palier pour Token Factory (garde de latence, C1-a).

    Jamais `None` : avec httpx 0.28, `timeout=None` coupe tout délai et un
    appel lent bloquait la visite des juges.
    deep/judge : lit NAVIGUIDE_TF_TIMEOUT_ULTRA_S (float > 0), défaut 45.0
    autres paliers : lit NAVIGUIDE_TF_TIMEOUT_S, défaut 25.0
    Valeurs invalides/≤0 → défaut.
    Retourne httpx.Timeout(seconds, connect=min(8.0, seconds)).
    """
    t = llm_budget.normalize_tier(tier)
    if t in {"deep", "judge"}:
        raw = _env("NAVIGUIDE_TF_TIMEOUT_ULTRA_S")
        default = 45.0
    else:
        raw = _env("NAVIGUIDE_TF_TIMEOUT_S")
        default = 25.0
    try:
        val = float(raw) if raw else default
    except (TypeError, ValueError):
        val = default
    if val <= 0:
        val = default
    connect = min(8.0, val)
    return httpx.Timeout(val, connect=connect)


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
    r"|SEUL JSON de faits"
    r"|I need to answer using ONLY"
    r"|using ONLY the JSON"
    r"|The JSON does not"
    r"|JSON does not contain"
    r"|JSON does not hold"
    r"|It lists:",
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
    re.compile(r"^\s*I need to answer using ONLY[^.!?…\n]*[.!?…]?\s*", re.IGNORECASE),
    re.compile(r"^\s*It lists:\s*", re.IGNORECASE),
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


_FR_UNITS = {
    "zéro": 0, "zero": 0, "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
    "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "onze": 11, "douze": 12,
    "treize": 13, "quatorze": 14, "quinze": 15, "seize": 16, "vingt": 20, "vingts": 20,
    "trente": 30, "quarante": 40, "cinquante": 50, "soixante": 60,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}
_NUM_HUNDRED = {"cent", "cents", "hundred", "hundreds"}
_NUM_THOUSAND = {"mille", "thousand", "thousands"}
_NUM_LINK = {"et", "and"}
# Mots seuls trop ambigus pour être des nombres (« un bateau », « un mille » nautique,
# « bateau neuf », « one of »).
_NUM_ALONE_SKIP = {"un", "une", "neuf", "one", "mille"}
_NUM_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]+|[\s\-]+|[^A-Za-zÀ-ÿ\s\-]+")


def _words_value(words: list[str]) -> int:
    total, cur, prev = 0, 0, ""
    for w in words:
        if w in _NUM_HUNDRED:
            cur = max(1, cur) * 100
        elif w in _NUM_THOUSAND:
            total += max(1, cur) * 1000
            cur = 0
        elif w in ("vingt", "vingts") and prev == "quatre" and cur % 100 == 4:
            cur += 76
        else:
            cur += _FR_UNITS[w]
        prev = w
    return total + cur


def spelled_numbers_to_digits(text: str) -> str:
    """« cent soixante-dix-sept » → « 177 » : les nombres en lettres comparés en chiffres.

    Sans cela, un modèle qui épelle un chiffre (173 → « cent soixante-dix-sept »)
    passait le garde-fou des nombres.
    """
    toks = _NUM_WORD_RE.findall(text or "")
    out: list[str] = []
    i = 0
    while i < len(toks):
        low = toks[i].lower()
        if low in _FR_UNITS or low in _NUM_HUNDRED or low in _NUM_THOUSAND:
            words, j, last = [low], i + 1, i
            while j < len(toks):
                t = toks[j].lower()
                if t.strip(" -") == "" and "\n" not in t:
                    j += 1
                    continue
                if t in _NUM_LINK and j + 2 < len(toks) and toks[j + 2].lower() in _FR_UNITS:
                    j += 1
                    continue
                if t in _FR_UNITS or t in _NUM_HUNDRED or t in _NUM_THOUSAND:
                    # « un mille » / « deux milles » : le mille nautique n'est pas 1000.
                    if t == "mille" and (j + 1 >= len(toks) or not any(
                        toks[k].lower() in _FR_UNITS or toks[k].lower() in _NUM_HUNDRED
                        for k in range(j + 1, min(j + 3, len(toks)))
                    )) and words[-1] in ("un", "une"):
                        break
                    words.append(t)
                    last = j
                    j += 1
                    continue
                break
            if len(words) == 1 and words[0] in _NUM_ALONE_SKIP:
                out.append(toks[i])
                i += 1
                continue
            try:
                out.append(str(_words_value(words)))
            except KeyError:
                out.append("".join(toks[i:last + 1]))
            i = last + 1
            continue
        out.append(toks[i])
        i += 1
    return "".join(out)


_GROUPED_NUM_RE = re.compile(r"\b\d{1,3}(?:[ ,\u202f\u00a0]\d{3})+\b")


def _numbers_spoken(text: str) -> set[str]:
    norm = spelled_numbers_to_digits(text or "")
    norm = _GROUPED_NUM_RE.sub(lambda m: re.sub(r"\D", "", m.group(0)), norm)
    # « 8 393 » vaut 8393 seulement : « 393 » seul n'est pas un fait.
    return _numbers(norm)


# Verdict JSON d'un relecteur : il cite des chiffres pour décrire une faute, il n'en
# publie aucun. Le filtre des nombres le viderait (« rules » → lu comme un pass).
NO_NUMBER_FILTER = object()


def filter_numbers(answer: str, facts: Any, *, spelled: bool = False) -> tuple[str, int]:
    """Drop every sentence whose figures are not already in `facts`.

    Same contract as logbook_chat.filter_numbers: a year or a time present
    in the facts is allowed. Returns (text, dropped).
    """
    blob = facts if isinstance(facts, str) else json.dumps(facts, ensure_ascii=False, default=str)
    allowed = _numbers_spoken(blob) if spelled else _numbers(blob)
    kept, dropped = [], 0
    for s in _SENT_SPLIT_RE.split(answer or ""):
        s = s.strip()
        if not s:
            continue
        norm = spelled_numbers_to_digits(s) if spelled else s
        norm = norm if not spelled else _GROUPED_NUM_RE.sub(lambda m: re.sub(r"\D", "", m.group(0)), norm)
        nums = _numbers(norm)
        if nums and not nums.issubset(allowed):
            dropped += 1
            continue
        kept.append(s)
    return " ".join(kept), dropped


def expand_spoken_units(text: str, lang: str = "fr") -> str:
    """« nm » lu « nanometres » : on écrit l'unité en toutes lettres."""
    en = str(lang or "").lower().startswith("en")
    unit = "nautical miles" if en else "milles nautiques"
    out = re.sub(r"(\d+(?:[.,]\d+)?)\s*nm\b", rf"\1 {unit}", text or "", flags=re.I)
    return re.sub(r"\bnm\b", unit, out, flags=re.I)


def split_short_sentences(text: str, max_len: int = 160) -> str:
    """Phrases courtes et complètes — jamais de coupure au milieu."""
    parts = [p.strip() for p in _SENT_SPLIT_RE.split(text or "") if p.strip()]
    out: list[str] = []
    for part in parts:
        chunk = part if part.endswith((".", "!", "?", "…")) else f"{part}."
        if len(chunk) <= max_len:
            out.append(chunk)
            continue
        bits = [b.strip() for b in re.split(r"(?<=[;:])\s+", chunk) if b.strip()]
        if len(bits) > 1:
            rejoined = " ".join(
                b if b.endswith((".", "!", "?", "…", ";", ":")) else f"{b}." for b in bits
            )
            # « cap sur X : N milles » — sans progrès le recollage reboucle (film_script
            # évitait le « : » pour ça). On garde la phrase entière.
            if rejoined.strip() == chunk.strip():
                out.append(chunk)
                continue
            out.extend(split_short_sentences(rejoined, max_len))
            continue
        out.append(chunk)
    return " ".join(out)


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
_WORD_RE = re.compile(r"[0-9A-Za-zÀ-ÿ]+")
# Marqueurs de raisonnement. Une phrase douteuse ne devient pas le texte visiteur.
_REASON_MARK_RE = re.compile(
    r"\bthe\s+user\b"
    r"|\bwe\s+need\b"
    r"|\blet['’]?s\b"
    r"|\bokay\b"
    r"|\bok\b"
    r"|\bi\s+should\b"
    r"|\bmaybe\b"
    r"|\bjson\b"
    r"|l['’]utilisateur"
    r"|l['’]utilisatrice"
    r"|\busager\b"
    r"|nous\s+devons"
    r"|il\s+nous\s+faut"
    r"|il\s+faut\b"
    r"|on\s+a\s+besoin"
    r"|on\s+doit\b"
    r"|on\s+me\s+demande"
    r"|\ballons\b"
    r"|\bvoyons\b"
    r"|d['’]accord"
    r"|je\s+dois"
    r"|je\s+devrais"
    r"|je\s+vais\s+écrire"
    r"|i\s+will\s+write"
    r"|i\s+am\s+asked"
    r"|final\s+answer"
    r"|r[ée]ponse\s+finale"
    r"|\btranslation\b"
    r"|\btraduction\b"
    r"|here\s+is\s+the\s+translation"
    r"|voici\s+la\s+traduction"
    r"|une\s+ou\s+deux\s+phrases"
    r"|one\s+or\s+two\s+plain\s+sentences"
    r"|phrases?\s+simples"
    r"|peut[- ]être",
    re.IGNORECASE,
)
_FR_WORD_RE = re.compile(
    r"\b(?:le|la|les|un|une|des|du|au|aux|est|sont|dans|pour|avec|que|qui|"
    r"cette|ces|pas|plus|par|vers|chez|où|ou|de)\b",
    re.IGNORECASE,
)
_FR_ACCENT_RE = re.compile(r"[àâäéèêëïîôùûüçœæ]")
_EN_WORD_RE = re.compile(
    r"\b(?:the|a|an|is|are|of|and|to|for|with|about|from|this|that|was|were|off)\b",
    re.IGNORECASE,
)
_MD_RE = re.compile(r"[*_#>`]+")
_EN_EMPHASIS_RE = re.compile(r"\*{2,}|_{2,}")
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
    """FR → EN via Lightning (`tier=fast`). Numbers, names, dates stay.

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
    result = await cascade_text(
        TRANSLATE_SYSTEM,
        user,
        client,
        tier="fast",
        fallback=src,
        facts=facts if facts is not None else src,
        max_tokens=_translate_max_tokens(src, max_tokens),
        lang="en",
    )
    out, source = result
    cleaned = _EN_EMPHASIS_RE.sub("", _clean_text(out))
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    if not cleaned:
        return _as_result(_clean_text(src) or "", "rules", tier="fast")
    res = _as_result(
        cleaned, source,
        model=str(getattr(result, "model", "") or ""),
        tier=str(getattr(result, "tier", "") or "fast"),
    )
    if getattr(result, "cache_hit", False):
        res.cache_hit = True
    return res


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


def _tf_url(tier: str) -> str:
    """Nano is pinned to the EU host. Lightning / Super stay on the default
    TF host. Ultra uses us-central1 (Nebius cookbook) unless
    NAVIGUIDE_TF_BASE_ULTRA is set."""
    t = llm_budget.normalize_tier(tier)
    if t in {"deep", "judge"}:
        base = (
            _env("NAVIGUIDE_TF_BASE_ULTRA") or TOKENFACTORY_ULTRA_BASE
        ).rstrip("/")
        return f"{base}/chat/completions"
    if t == "nano":
        base = (_env("NAVIGUIDE_TF_BASE_EU") or TOKENFACTORY_EU_BASE).rstrip("/")
        return f"{base}/chat/completions"
    return TOKENFACTORY_URL


def tf_base(tier: str) -> str:
    """Hôte Token Factory (`…/v1`) qui sert ce palier — celui de `_tf_url`."""
    url = _tf_url(tier)
    suffix = "/chat/completions"
    return url[: -len(suffix)] if url.endswith(suffix) else url.rsplit("/", 2)[0]


# Garde de disponibilité (C1-b) : si l'id d'un palier manque au catalogue de
# son hôte, on essaie ces paliers Token Factory, dans l'ordre. Ce sont d'autres
# Nemotron TF (jamais NIM / OpenRouter ici) ; la réponse garde la source et le
# modèle du palier qui a vraiment répondu.
GUARD_SUBSTITUTES: dict[str, tuple[str, ...]] = {
    "nano": ("fast", "write"),
    "fast": ("write",),
    "write": ("fast",),
    "deep": ("write", "fast"),
    "judge": ("write", "fast"),
}


async def _guarded_tier(tier: str, client: httpx.AsyncClient) -> str:
    """Palier à appeler après la garde du catalogue.

    Inconnu (catalogue illisible, garde coupée) : on garde le palier demandé.
    Absent : premier remplaçant présent dans le catalogue de son hôte et dans
    le budget du jour, compté dans `modelGuard.missing`. Aucun remplaçant :
    RuntimeError, la cascade passe au repli suivant (déjà étiqueté).
    """
    t = llm_budget.normalize_tier(tier)
    key = nebius_key()
    if not tf_catalog.enabled() or not key:
        return t
    model = llm_budget.model_for(t)
    base = tf_base(t)
    await tf_catalog.ensure_fresh(base, key, client)
    if tf_catalog.has_model(base, model) is not False:
        return t
    for alt in GUARD_SUBSTITUTES.get(t, ()):
        alt_model = llm_budget.model_for(alt)
        alt_base = tf_base(alt)
        if alt_model.lower() == model.lower() and alt_base == base:
            continue
        await tf_catalog.ensure_fresh(alt_base, key, client)
        if tf_catalog.has_model(alt_base, alt_model) is True and llm_budget.allow(alt):
            llm_budget.record_model_missing(t, model, alt, alt_model)
            log.warning(
                "garde catalogue : %s absent de %s — palier %s servi par %s (%s)",
                model, base, t, alt, alt_model,
            )
            return alt
    llm_budget.record_model_missing(t, model)
    raise RuntimeError(f"tokenfactory model missing from catalog: {model} @ {base}")


class CascadeResult(tuple):
    """`(text, source)` plus the model id and tier that actually answered.

    Unpacking stays `text, source = result`. `model` is the id the server
    ran (or the one we sent). `tier` is nano / fast / write / deep / judge.
    """

    model: str
    tier: str

    def __new__(cls, text: str, source: str, model: str = "", tier: str = ""):
        self = super().__new__(cls, (text, source))
        self.model = str(model or "")
        self.tier = str(tier or "")
        return self


def _as_result(text: str, source: str, model: str = "", tier: str = "") -> CascadeResult:
    return CascadeResult(text, source, model=model, tier=tier)


def _exact_model(source: str, reported: str, requested: str) -> str:
    """Model id that matches the source.

    A fallback (NIM, OpenRouter, Claude) must not keep a Nemotron id: the
    badge would otherwise say Token Factory. Token Factory keeps the id the
    server echoed, or the id we sent.
    """
    got = (reported or "").strip()
    asked = (requested or "").strip()
    nemotron = "nemotron" in got.lower() or "lightning" in got.lower()
    if (source or "").strip().lower().startswith("nemotron"):
        return got if nemotron else (asked or got)
    if got and not nemotron:
        return got
    return asked or got


def _message_parts(raw: Any) -> list[tuple[str, str]]:
    """`(kind, text)` pairs. A bare string is kind `text`."""
    if isinstance(raw, str):
        return [("text", raw)]
    if isinstance(raw, dict):
        kind = str(raw.get("type") or "text")
        text = raw.get("text") if raw.get("text") is not None else raw.get("content")
        if not isinstance(text, str):
            text = "" if text is None else str(text)
        return [(kind, text)]
    if isinstance(raw, list):
        out: list[tuple[str, str]] = []
        for part in raw:
            out.extend(_message_parts(part))
        return out
    return []


def _parts_text(parts: list[tuple[str, str]], *, reasoning: bool = False) -> str:
    """Visitor text, or the reasoning parts when `reasoning` is set."""
    chunks: list[str] = []
    for kind, text in parts:
        k = kind.lower()
        if reasoning:
            if k in {"reasoning", "thinking"}:
                chunks.append(text)
        elif k not in {"reasoning", "thinking"}:
            chunks.append(text)
    return "".join(chunks)


def _words(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text or "")]


def _shares_prompt_span(sentence: str, prompt: str, n: int = 6) -> bool:
    """True when `n` consecutive words of the sentence are copied from the prompt."""
    sw = _words(sentence)
    pw = _words(prompt)
    if len(sw) < n or len(pw) < n:
        return False
    grams = {tuple(pw[i:i + n]) for i in range(len(pw) - n + 1)}
    return any(tuple(sw[i:i + n]) in grams for i in range(len(sw) - n + 1))


def _sentence_matches_lang(text: str, *, en: bool) -> bool:
    """Keep the sentence only when it is clearly the requested language.

    A tie, or no signal at all, is a doubt: reject.
    """
    fr = len(_FR_WORD_RE.findall(text or "")) + len(_FR_ACCENT_RE.findall(text or ""))
    en_n = len(_EN_WORD_RE.findall(text or ""))
    if fr <= 0 and en_n <= 0:
        return False
    if fr == en_n:
        return False
    return (en_n > fr) if en else (fr > en_n)


def _recover_reasoning_text(raw: Any, *, prompt: str = "", lang: str = "fr") -> str:
    """A plain sentence left beside an empty `content`.

    Lightning (and Ultra) often spend `max_tokens` on the trace and return
    `finish_reason=length` with an empty `content`. The answer then sits in
    `message.reasoning` or `reasoning_content`. The trace itself is never
    returned. A sentence is kept only when it has no reasoning marker, no
    6-word copy of the prompt, and it is in the requested language. Anything
    doubtful stays empty so the cascade can retry Super or fall back with an
    honest label.
    """
    if raw is None:
        return ""
    if isinstance(raw, str):
        blob = raw
    else:
        parts = _message_parts(raw)
        blob = _parts_text(parts, reasoning=True) or _parts_text(parts, reasoning=False)
    stripped = _strip_preamble(_strip_think(_FENCE_RE.sub("", blob or "")))
    want_en = _is_en(lang)
    kept: list[str] = []
    for sentence in _SENT_SPLIT_RE.split(stripped):
        sentence = sentence.strip()
        if not sentence:
            continue
        piece = _clean_text(sentence)
        if not piece or _PROMPT_LEAK_RE.search(piece) or _META_RE.search(piece):
            continue
        if _REASON_MARK_RE.search(piece):
            continue
        if _shares_prompt_span(piece, prompt):
            continue
        if not _sentence_matches_lang(piece, en=want_en):
            continue
        kept.append(piece)
        if len(kept) >= MAX_SENTENCES:
            break
    return " ".join(kept).strip()


def _openai_text(data: dict[str, Any] | None, *, prompt: str = "", lang: str = "fr") -> str:
    """Visitor text from a chat completion.

    `content` wins. When it is empty, Nemotron on Token Factory often spent
    the token budget on the trace (`finish_reason=length`, `max_tokens`
    covering thinking plus the answer) and left the sentence in
    `message.reasoning` (vLLM / Ultra) or `reasoning_content`. Only a sentence
    that passes `_recover_reasoning_text` may leave that field.
    """
    choice = ((data or {}).get("choices") or [{}])[0] or {}
    if not isinstance(choice, dict):
        choice = {}
    msg = choice.get("message") or {}
    if not isinstance(msg, dict):
        msg = {}
    content_parts = _message_parts(msg.get("content"))
    content = _clean_text(_parts_text(content_parts, reasoning=False))
    if content:
        return content
    for raw in (msg.get("reasoning"), msg.get("reasoning_content"), choice.get("reasoning")):
        recovered = _recover_reasoning_text(raw, prompt=prompt, lang=lang)
        if recovered:
            return recovered
    typed = _parts_text(content_parts, reasoning=True)
    if typed:
        return _recover_reasoning_text(typed, prompt=prompt, lang=lang)
    return ""


def _claude_text(data: dict[str, Any] | None) -> str:
    parts = []
    for block in (data or {}).get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text") or "")
        elif isinstance(block, str):
            parts.append(block)
    return _clean_text("\n".join(parts))


def _http_error(provider: str, response: httpx.Response) -> RuntimeError:
    """Keep the exact HTTP status and a short body — never swallow a 4xx/5xx."""
    body = " ".join((response.text or "").split())[:180]
    msg = f"{provider} HTTP {response.status_code}"
    if body:
        msg = f"{msg} {body}"
    return RuntimeError(msg)


def _tf_payload(system: str, user: str, tier: str, max_tokens: int | None = None) -> dict[str, Any]:
    """Token Factory HTTP body — not the Python SDK.

    `extra_body` is an OpenAI *client* argument that the SDK flattens. Sending
    it as a JSON field made Lightning 3.5 return empty content (tokenfactory
    empty → NIM). Lightning needs `reasoning_effort` and `enable_thinking` at
    the **root** of this dict (fast tier included) — confirmed on OVH 2026-10-17,
    issue #432.
    """
    t = llm_budget.normalize_tier(tier)
    payload = {
        "model": llm_budget.model_for(t),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens or llm_budget.max_tokens_for(t),
        "temperature": 0.4,
        "stream": False,
        "reasoning_effort": "none",
        "chat_template_kwargs": {"enable_thinking": False},
    }
    return payload


def _tf_fast_super_retry(exc: BaseException) -> bool:
    """Second essai Super (LT1) : vide, 5xx ou timeout — pas les 4xx."""
    if isinstance(exc, httpx.TimeoutException):
        return True
    msg = str(exc)
    if "tokenfactory empty" in msg:
        return True
    m = re.search(r"tokenfactory HTTP (\d{3})", msg)
    return bool(m and int(m.group(1)) >= 500)


async def _call_tokenfactory(
    system: str, user: str, tier: str, client: httpx.AsyncClient,
    *,
    max_tokens: int | None = None,
    cascade_tier: str | None = None,
    lang: str = "fr",
) -> tuple[str, str]:
    key = nebius_key()
    if not key:
        raise RuntimeError("NEBIUS_API_KEY missing")
    t = llm_budget.normalize_tier(tier)
    payload = _tf_payload(system, user, t, max_tokens)
    timeout = tf_timeout(t)
    sema = _tf_limiter()
    try:
        await asyncio.wait_for(sema.acquire(), timeout=timeout.read)
    except asyncio.TimeoutError as exc:
        # File d'attente du limiteur pleine trop longtemps : repli étiqueté.
        llm_budget.record_latency_timeout(t)
        raise RuntimeError("tokenfactory queue timeout") from exc
    started = time.monotonic()
    try:
        r = await client.post(
            _tf_url(t),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
        elapsed_ms = (time.monotonic() - started) * 1000.0
    except httpx.TimeoutException as exc:
        llm_budget.record_latency_timeout(t)
        raise RuntimeError(f"tokenfactory timeout after {int(timeout.read)} s") from exc
    finally:
        sema.release()
    if r.status_code >= 400:
        raise _http_error("tokenfactory", r)
    # Latence par palier du modèle appelé (C1-a) : aller-retour HTTP réussi.
    llm_budget.record_latency(t, elapsed_ms)
    data = r.json()
    text = _openai_text(data, prompt=f"{system}\n{user}", lang=lang)
    reported = str((data or {}).get("model") or "")
    source = llm_budget.source_for(t)
    model = _exact_model(source, reported, str(payload.get("model") or ""))
    pt, ct = _usage_tokens(data, system, user, text)
    if not text:
        # The trace was billed even though content is empty.
        llm_budget.record(t, pt, ct)
        choice = ((data or {}).get("choices") or [{}])[0]
        if not isinstance(choice, dict):
            choice = {}
        fr = choice.get("finish_reason") or "?"
        raise RuntimeError(f"tokenfactory empty finish={fr} ct={ct} model={model or '?'}")
    llm_budget.record(t, pt, ct)
    report_tier = cascade_tier if cascade_tier is not None else t
    llm_budget.remember_source(source, report_tier)
    llm_budget.remember_served_model(model, report_tier)
    llm_budget.clear_tier_errors(report_tier)
    return _as_result(text, source, model=model, tier=t)


async def _call_nim(
    system: str, user: str, client: httpx.AsyncClient, *, tier: str = "", lang: str = "fr",
) -> CascadeResult:
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
        raise _http_error("nvidia", r)
    data = r.json()
    text = _openai_text(data, prompt=f"{system}\n{user}", lang=lang)
    if not text:
        raise RuntimeError("nvidia empty")
    source = f"nvidia-{NIM_MODEL.split('/')[-1]}"
    model = _exact_model(source, str((data or {}).get("model") or ""), NIM_MODEL)
    return _as_result(text, source, model=model, tier=tier)


async def _call_openrouter(
    system: str, user: str, client: httpx.AsyncClient, *, online: bool,
    max_tokens: int | None = None,
    tier: str = "",
    lang: str = "fr",
) -> CascadeResult:
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
        raise _http_error("openrouter", r)
    data = r.json()
    text = _openai_text(data, prompt=f"{system}\n{user}", lang=lang)
    if not text:
        raise RuntimeError("openrouter empty")
    answered = _exact_model("openrouter", str((data or {}).get("model") or ""), model)
    return _as_result(text, "openrouter", model=answered, tier=tier)


async def _call_claude(
    system: str, user: str, client: httpx.AsyncClient, *, max_tokens: int | None = None,
    tier: str = "",
) -> CascadeResult:
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
        raise _http_error("claude", r)
    data = r.json()
    text = _claude_text(data)
    if not text:
        raise RuntimeError("claude empty")
    answered = _exact_model("claude", str((data or {}).get("model") or ""), CLAUDE_MODEL)
    return _as_result(text, "claude", model=answered, tier=tier)


class _OriginHit(CascadeResult):
    """Prompt-cache hit: `source` is the provider that wrote the text; flag `cache_hit`."""

    cache_hit = True


def _stored_origin(raw: Any) -> str:
    src = str(raw or "").strip()
    if not src or src == "cache":
        return ""
    return src


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
    origin = _stored_origin(val.get("source"))
    if not origin:
        return None
    stored_model = str(val.get("model") or "")
    if cleaned != text:
        pearl_store.kv_put(CACHE_NS, key, {"text": cleaned, "source": origin, "model": stored_model})
    return _OriginHit(cleaned, origin, model=stored_model)


def _cache_put(key: str, text: str, source: str, model: str = "") -> None:
    import pearl_store  # noqa: PLC0415

    origin = _stored_origin(source)
    if not text or not origin or source in {"budget", "rules"}:
        return
    pearl_store.kv_put(CACHE_NS, key, {"text": text, "source": origin, "model": model or ""})


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
    lang: str = "fr",
) -> tuple[str, str]:
    cache_key = prompt_cache_key(system, user, tier, online=online, max_tokens=max_tokens)
    hit = _cache_get(cache_key)
    if hit:
        return hit
    if not llm_budget.allow(tier):
        text = _apply_filter(fallback or "", facts if facts is not None else user, keep_if_empty=True)
        return _as_result(text, "budget", tier=llm_budget.normalize_tier(tier))

    last = "no_llm_backend"
    hops: list[tuple[str, Any]] = []
    norm_tier = llm_budget.normalize_tier(tier)
    asked_lang = "en" if _is_en(lang) else "fr"

    async def _tokenfactory_hop() -> tuple[str, str]:
        call_tier = await _guarded_tier(norm_tier, http)
        if call_tier != norm_tier:
            # Remplaçant étiqueté : source et modèle du palier qui répond.
            return await _call_tokenfactory(
                system, user, call_tier, http, max_tokens=max_tokens, cascade_tier=norm_tier,
                lang=asked_lang,
            )
        try:
            return await _call_tokenfactory(
                system, user, tier, http, max_tokens=max_tokens, cascade_tier=norm_tier,
                lang=asked_lang,
            )
        except Exception as exc:
            if norm_tier == "nano":
                # Repli étiqueté : Lightning (source nemotron-lightning), puis
                # le maillon NIM du tour de providers si Lightning échoue aussi.
                if not llm_budget.allow("fast"):
                    raise
                log.warning("cascade nano: %s — repli Lightning", exc)
                return await _call_tokenfactory(
                    system, user, "fast", http, max_tokens=max_tokens, cascade_tier=norm_tier,
                    lang=asked_lang,
                )
            if norm_tier != "fast" or not _tf_fast_super_retry(exc):
                raise
            llm_budget.record_retry_super()
            budget = max_tokens if max_tokens is not None else llm_budget.max_tokens_for(norm_tier)
            super_mt = max(int(budget), 400)
            return await _call_tokenfactory(
                system, user, "write", http, max_tokens=super_mt, cascade_tier=norm_tier,
                lang=asked_lang,
            )

    for name in providers():
        if name == "tokenfactory":
            hops.append((name, _tokenfactory_hop))
        elif name == "openrouter":
            hops.append((name, lambda: _call_openrouter(
                system, user, http, online=online, max_tokens=max_tokens, tier=norm_tier,
                lang=asked_lang,
            )))
        elif name == "claude":
            hops.append((name, lambda: _call_claude(
                system, user, http, max_tokens=max_tokens, tier=norm_tier,
            )))
        elif name == "nim":
            hops.append((name, lambda: _call_nim(
                system, user, http, tier=norm_tier, lang=asked_lang,
            )))

    failures: list[dict[str, str]] = []
    for name, step in hops:
        try:
            result = await step()
            text, source = result
            if facts is not NO_NUMBER_FILTER:
                text = _apply_filter(text, facts if facts is not None else user)
            if _clean_text(text):
                if failures:
                    llm_budget.remember_cascade_errors(failures, tier=norm_tier)
                if name in llm_budget.FALLBACK_PROVIDERS:
                    llm_budget.record_fallback(name, norm_tier)
                    llm_budget.remember_source(name, norm_tier)
                public = source if source in KNOWN_SOURCES else (
                    "openrouter" if source.startswith("openrouter") else source
                )
                model = str(getattr(result, "model", "") or "")
                answered_tier = str(getattr(result, "tier", "") or norm_tier)
                # NIM returns `nvidia-<model>` (not in KNOWN_SOURCES). Cache it
                # anyway: a gale is written live to the story store, but the
                # same prompt must not re-hit the GPU (RG18 + RG19 deep tier).
                if public in KNOWN_SOURCES or str(public).startswith("nvidia-"):
                    _cache_put(cache_key, text, public, model=model)
                return _as_result(text, public, model=model, tier=answered_tier)
            last = f"{name} empty"
            log.warning("cascade %s: empty after filter", name)
            failures.append({"provider": name, "reason": last})
        except Exception as exc:
            last = str(exc)[:240]
            log.warning("cascade %s: %r", name, exc)
            failures.append({"provider": name, "reason": last})

    if failures:
        llm_budget.remember_cascade_errors(failures, tier=norm_tier)

    if fallback is not None:
        text = _apply_filter(fallback, facts if facts is not None else user, keep_if_empty=True)
        return _as_result(text, "rules", tier=norm_tier)
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
    lang: str = "fr",
) -> tuple[str, str]:
    """Cache SQLite → Token Factory → OpenRouter → Claude → rules.

    Returns `(text, source)` with source in KNOWN_SOURCES. `fallback is None`
    keeps the old contract (raise when no backend). A string fallback — even
    empty — yields `source=rules` after every provider failed. Never Tavily.
    """
    import offline
    if offline.enabled():
        if fallback is None:
            raise offline.OfflineError("NAVIGUIDE_OFFLINE=1")
        return (fallback or ""), "rules"
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
                    max_tokens=max_tokens, lang=lang,
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


_DEEP_STORY_TYPES = frozenset({
    "stop", "stop-arrival", "arrival", "escale", "wind-gale", "cyclone-nearby",
    "depth-alert", "marina-refuge", "cyclone",
})


def story_tier(body: dict[str, Any] | None) -> str:
    """Ultra for stopovers and major alerts; Super for the rest of the narrative."""
    if not isinstance(body, dict):
        return "write"
    typ = str(body.get("type") or body.get("event") or "").strip().lower()
    if typ in _DEEP_STORY_TYPES:
        return "deep"
    if str(body.get("severity") or "").strip().lower() == "alert":
        return "deep"
    return "write"


@with_ai_transparency
async def write_story(
    body: dict[str, Any] | None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Cascade cible : Token Factory → OpenRouter → Claude → règles.

    Langue EN : le récit est d'abord rédigé en FR, puis traduit
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
        drafted = await cascade_text(
            system, user, client, online=page, tier=story_tier(body),
            fallback=fallback if fallback is not None else "",
            facts=event,
            lang="fr",
        )
        text, source = drafted
        model = str(getattr(drafted, "model", "") or "")
        tier_name = str(getattr(drafted, "tier", "") or story_tier(body))
        cache_hit = bool(getattr(drafted, "cache_hit", False))
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
            "cache_hit": False,
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
            "cache_hit": cache_hit,
        }
    used_local = tidy == (fallback or "").strip() and tidy != _clean_text(text).strip()
    if want_en and tidy and not used_local:
        translated = await translate(tidy, "en", client, facts=tidy)
        tidy, source = translated
        if getattr(translated, "model", ""):
            model = str(translated.model)
        if getattr(translated, "tier", ""):
            tier_name = str(translated.tier)
        cache_hit = bool(getattr(translated, "cache_hit", False))
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
                "cache_hit": cache_hit,
            }
    engine = source
    if used_local:
        engine = f"{source}+local"
    out: dict[str, Any] = {
        "status": "ready",
        "text": tidy,
        "engine": engine,
        "source": source,
        "tier": tier_name,
        "cascade": "tokenfactory-openrouter-claude",
        "tavily": None,
        "nvidia": source if source.startswith("nemotron-") else engine,
        "cache_hit": cache_hit,
    }
    # Exact model id of the call that produced the text. A local phrase and
    # rules/budget/cache do not borrow a Nemotron id.
    if model and not used_local and source not in {"rules", "budget", "cache"}:
        out["model"] = model
    return out
