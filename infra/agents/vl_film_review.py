#!/usr/bin/env python3
"""Revue VL du mouvement du film (lot VR1). Éteinte par défaut.

N'appelle VL que si NAVIGUIDE_VL_REVIEW=1 et si le diff touche le script,
la voix, la caméra, le bateau ou le sous-titre. La boucle (run_lots.py)
ne l'appelle pas. Le réviseur de nuit lit les lignes « - [ ] KO : … »
et pose les lots RC — pas un canal à part.

Passeur : Token Factory (décision du porteur, 17 oct.). CI et run_lots
n'appellent toujours pas. Clé NEBIUS_API_KEY, modèle nvidia/Nemotron-3.5-Super-VL.

Usage (poste) :
    NAVIGUIDE_VL_REVIEW=1 python3 infra/agents/vl_film_review.py \\
        --images shot1.jpg --telemetry telemetry.json --subtitle-file sub.txt \\
        --diff-files src/map/filmCamera.js src/engine/replay.js
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

ENV_FLAG = "NAVIGUIDE_VL_REVIEW"
ENV_URL = "NAVIGUIDE_VL_URL"
ENV_KEY = "NAVIGUIDE_VL_KEY"
ENV_MODEL = "NAVIGUIDE_VL_MODEL"
ENV_FILE = Path.home() / ".config" / "naviguide" / "simulator.env"
TF_URL = "https://api.tokenfactory.nebius.com/v1/chat/completions"
TF_MODEL = "nvidia/Nemotron-3.5-Super-VL"

# Ligne que le réviseur de nuit doit voir — hors titre 🤖, hors « — KO ».
KO_LINE_RE = re.compile(r"^\s*[-*]\s*\[\s*\]\s*KO\s*:\s+\S")

# Diff qui autorise un appel VL (lot VR1 : script, replay, caméra, voix, sous-titre).
FILM_TOUCH_RE = re.compile(
    r"film_script\.py|(?:^|/)replay\.js|filmCamera\.js|"
    r"useReplayVoice\.js|useReplay\.js|film_discours\.py|"
    r"film-cinematique|"
    r"subtitle|sous[-_]?titre|voix|(?:^|/)voice",
    re.I,
)

_REQUIRED_VL_HOST = re.compile(r"tokenfactory\.nebius\.com", re.I)
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
_PROPER_RE = re.compile(
    r"\b([A-ZÉÈÊÀÂÎÔÙÛÇ][a-zàâäéèêëïîôùûüç]{2,}"
    r"(?:-[A-ZÉÈÊÀÂÎÔÙÛÇ]?[a-zàâäéèêëïîôùûüç]+)+|"
    r"[A-ZÉÈÊÀÂÎÔÙÛÇ][a-zàâäéèêëïîôùûüç]{3,})\b"
)

# Sujets que VL a le droit de juger.
_MOVEMENT_RE = re.compile(
    r"saccade|d[eé]croch|zoom|calage|cal[ée]|fluid|"
    r"cam[eé]ra|bateau|sous[- ]?titre|subtitle|frame|fps|"
    r"\bpan\b|gliss|fig[eé]|gel|à-coup|acoup|jitter|"
    r"playhead|centre|écran|ecran",
    re.I,
)

# Faits de mer : toujours rejetés, même s'ils figurent dans le sous-titre.
_SEA_DENY = frozenset({
    "vent", "vents", "vague", "vagues", "courant", "courants", "mer", "mers",
    "houle", "meteo", "orage", "alize", "alizes", "milles", "mille", "noeud",
    "noeuds", "kn", "nm", "zee", "aire", "amp", "port", "ports", "quai",
    "escale", "escales", "ile", "iles", "golfe", "detroit", "cap", "rade",
    "rochelle", "ajaccio", "noumea", "brisbane", "francisco", "gibraltar",
    "aden", "malacca", "pitre", "caraibes", "atlantique", "pacifique",
    "mediterranee", "suez", "panama", "vendres",
})

_SMALL = frozenset({
    "la", "le", "les", "une", "un", "des", "du", "de", "au", "aux",
    "the", "a", "an", "of", "and", "or",
})


def _fold(text: str) -> str:
    return unicodedata.normalize("NFD", text or "").encode("ascii", "ignore").decode("ascii").lower()


def _numbers(text: str) -> set[str]:
    out: set[str] = set()
    for m in _NUM_RE.findall(text or ""):
        try:
            out.add(format(float(m.replace(",", ".")), "g"))
        except ValueError:
            continue
    return out


def collect_movement_kos(comments: list[dict] | None) -> list[str]:
    """Lignes « - [ ] KO : … » dans n'importe quel commentaire, y compris hors 🤖."""
    out: list[str] = []
    for c in comments or []:
        for ln in (c.get("body") or "").splitlines():
            s = ln.strip()
            if KO_LINE_RE.match(s):
                out.append(s)
    return list(dict.fromkeys(out))


def film_diff_touches(paths: list[str] | None) -> bool:
    return any(FILM_TOUCH_RE.search(p or "") for p in (paths or []))


def paths_from_name_list(text: str) -> list[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip() and not ln.startswith("#")]


def _env_file_values(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for ln in raw.splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        out[k.strip()] = v.strip().strip("'").strip('"')
    return out


def _setting(name: str) -> str:
    """os.environ d'abord (tests), sinon simulator.env (NEBIUS_API_KEY pour VL)."""
    if name in os.environ:
        return (os.environ.get(name) or "").strip()
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return ""
    vals = _env_file_values(ENV_FILE)
    if name in (ENV_KEY, "NEBIUS_API_KEY"):
        return (vals.get(ENV_KEY) or vals.get("NEBIUS_API_KEY") or "").strip()
    return (vals.get(name) or "").strip()


def vl_review_enabled() -> bool:
    """Éteint si la variable manque, si elle n'est pas 1, ou en CI (CI et run_lots n'appellent pas)."""
    if (os.environ.get("CI") or "").strip().lower() in ("1", "true", "yes"):
        return False
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return (os.environ.get(ENV_FLAG) or "").strip() == "1"
    return _setting(ENV_FLAG) == "1"


def build_vl_prompt(telemetry: object, subtitle: str) -> str:
    blob = telemetry if isinstance(telemetry, str) else json.dumps(telemetry, ensure_ascii=False, default=str)
    return (
        "Tu juges UNIQUEMENT le mouvement d'un film (saccade, décrochage, zoom, calage, fluidité).\n"
        "Interdit : fait de mer, nom de lieu, météo, distance, cap, nœuds, tout nombre absent de la télémétrie.\n"
        "Sortie : uniquement des lignes « - [ ] KO : … ». Rien d'autre. Pas de titre, pas de paragraphe.\n"
        "Si rien ne cloche, n'écris rien.\n"
        "\n## Télémétrie\n"
        f"{blob[:12000]}\n"
        "\n## Sous-titre (calage seulement, pas une source de noms)\n"
        f"{(subtitle or '')[:4000]}\n"
    )


def _invents_place(body: str) -> bool:
    folded = _fold(body)
    for word in _SEA_DENY:
        if re.search(rf"\b{re.escape(word)}\b", folded):
            return True
    for m in _PROPER_RE.finditer(body or ""):
        word = m.group(1)
        if word.lower() in _SMALL or _MOVEMENT_RE.search(word):
            continue
        return True
    return False


def sanitize_vl_comment(raw: str, telemetry: object, subtitle: str = "") -> str:
    """Ne garde que des lignes « - [ ] KO : … » de mouvement, sans mer ni chiffre inventé.

    `subtitle` est accepté pour l'appelant ; il n'autorise aucun nom (les faits de mer restent interdits).
    """
    del subtitle  # jamais une source de toponymes
    blob = telemetry if isinstance(telemetry, str) else json.dumps(telemetry, ensure_ascii=False, default=str)
    allowed = _numbers(blob)
    kept: list[str] = []
    for ln in (raw or "").splitlines():
        s = ln.strip()
        if not KO_LINE_RE.match(s):
            continue
        body = re.sub(r"^[-*]\s*\[\s*\]\s*KO\s*:\s*", "", s).strip()
        if not _MOVEMENT_RE.search(body):
            continue
        if _invents_place(body):
            continue
        nums = _numbers(body)
        if nums and not nums.issubset(allowed):
            continue
        kept.append(s)
    return "\n".join(dict.fromkeys(kept))


def call_vl(prompt: str, images: list[str]) -> str:
    """Appel OpenAI-compatible Token Factory. Clé hors dépôt (NEBIUS_API_KEY)."""
    url = _setting(ENV_URL) or TF_URL
    if not url:
        raise RuntimeError(f"{ENV_URL} absent : viser {TF_URL}")
    if not _REQUIRED_VL_HOST.search(url):
        raise RuntimeError(
            "la revue VL passe par Token Factory (décision du porteur, 17 oct.) : "
            f"URL {url!r} refusée"
        )
    key = _setting(ENV_KEY) or _setting("NEBIUS_API_KEY")
    if not key:
        raise RuntimeError("NEBIUS_API_KEY / NAVIGUIDE_VL_KEY absent (Token Factory)")
    model = _setting(ENV_MODEL) or TF_MODEL
    content: list[dict] = [{"type": "text", "text": prompt}]
    for path in images or []:
        p = Path(path)
        if not p.is_file():
            continue
        raw = p.read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "max_tokens": 400,
        "reasoning_effort": "none",
        "chat_template_kwargs": {"enable_thinking": False},
    }
    headers = {"Content-Type": "application/json", "User-Agent": "bim-vl-film-review"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"VL HTTP {e.code}: {detail}") from e
    choices = data.get("choices") or []
    if not choices:
        return ""
    msg = (choices[0].get("message") or {}).get("content") or ""
    return msg if isinstance(msg, str) else str(msg)


def review_film(
    *,
    images: list[str] | None,
    telemetry: object,
    subtitle: str,
    diff_files: list[str] | None,
    vl_call=None,
) -> str:
    """Produit le commentaire (lignes KO seulement). Chaîne vide si éteint ou hors film."""
    if not vl_review_enabled():
        return ""
    if not film_diff_touches(diff_files):
        return ""
    raw = (vl_call or call_vl)(build_vl_prompt(telemetry, subtitle), list(images or []))
    return sanitize_vl_comment(raw, telemetry, subtitle)


def parse_cinematique_log(text: str) -> dict:
    """Nombres extraits du stdout de film-cinematique.mjs — seuls chiffres autorisés dans les KO."""
    out: dict = {"log": (text or "")[:4000]}
    fps = re.search(r"→\s*([\d.]+)\s*fps", text or "")
    if fps:
        out["fps"] = float(fps.group(1))
    p95 = re.search(r"p95\s+([\d.]+)\s*ms", text or "")
    if p95:
        out["dt_ms_p95"] = float(p95.group(1))
    mx = re.search(r"max\s+([\d.]+)\s*ms", text or "")
    if mx:
        out["dt_ms_max"] = float(mx.group(1))
    over = re.search(r"frames > 34 ms : \d+ \(([\d.]+)\s*%\)", text or "")
    if over:
        out["frames_over_34ms_pct"] = float(over.group(1))
    zboat = re.search(r"nuls \(< 0,05 px\) (\d+) \(([\d.]+)\s*%\)", text or "")
    if zboat:
        out["boat_zero_n"] = int(zboat.group(1))
        out["boat_zero_pct"] = float(zboat.group(2))
    zcam = re.search(r"caméra : pas nuls (\d+) \(([\d.]+)\s*%\)", text or "")
    if zcam:
        out["camera_zero_n"] = int(zcam.group(1))
        out["camera_zero_pct"] = float(zcam.group(2))
    noadv = re.search(r"frames sans avance (\d+)", text or "")
    if noadv:
        out["frames_no_advance"] = int(noadv.group(1))
    return out


def capture_film_motion(url: str, seconds: int = 15, sim_root: Path | None = None) -> tuple[dict, list[str]]:
    """Joue Revoir sur le poste, 15 s, sans voix. Retourne télémétrie + chemin de capture."""
    root = sim_root or Path(__file__).resolve().parents[2] / "naviguide-simulator"
    script = root / "scripts" / "film-cinematique.mjs"
    if not script.is_file():
        raise RuntimeError(f"script absent : {script}")
    shot = Path("/tmp/film-cinematique.png")
    env = {k: v for k, v in os.environ.items() if k != "PLAYWRIGHT_BROWSERS_PATH"}
    proc = subprocess.run(
        ["node", str(script), url, str(int(seconds))],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=max(60, int(seconds) + 40),
        env=env,
    )
    log = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(f"film-cinematique code {proc.returncode}: {log[-800:]}")
    images = [str(shot)] if shot.is_file() else []
    return parse_cinematique_log(log), images


def review_tranche(state, ids: list[str], http, recette_url: str = "http://127.0.0.1:5174/?view=suivre") -> str:
    """Capture le poste, appelle VL, poste les KO sur la tête. Chaîne vide si rien."""
    if not vl_review_enabled():
        return ""
    import run_lots as rl  # noqa: PLC0415

    paths: list[str] = []
    tip_num = None
    for lid in ids:
        num = rl.pr_number((state.done.get(lid) or {}).get("pr"))
        if not num:
            continue
        tip_num = num
        try:
            files = http.github(f"/repos/{rl.owner_repo(rl.DEFAULT_REPO)}/pulls/{num}/files?per_page=100") or []
        except Exception:
            files = []
        paths.extend(f.get("filename") or "" for f in files)
    if not film_diff_touches(paths) or not tip_num:
        return ""
    telemetry, images = capture_film_motion(recette_url)
    comment = review_film(
        images=images,
        telemetry=telemetry,
        subtitle="",
        diff_files=paths,
    )
    if not comment:
        return ""
    body = (
        "## Revue VL (mouvement)\n\n"
        "Nemotron VL, saccade / décrochage / zoom / calage / fluidité seulement. "
        "Pas un fait de mer. Le réviseur de nuit en fait un lot RC s'ils tiennent.\n\n"
        f"{comment}\n"
    )
    from post_pr_comment import post  # noqa: PLC0415
    return post(int(tip_num), body)


def movement_kos_section(comments: list[dict] | None) -> list[str]:
    """Bloc à coller dans le prompt du réviseur de nuit."""
    kos = collect_movement_kos(comments)
    if not kos:
        return []
    return [
        "## KO de mouvement",
        "",
        "- Ce sont des KO de mouvement, à transformer en lot RC s'ils tiennent, pas un canal à part. "
        "Saccade, décrochage, zoom, calage, fluidité seulement — aucun fait de mer. "
        "C'est toi qui poses les lots ; la boucle ne les exécute pas toute seule.",
        *[f"  {ln}" for ln in kos],
        "",
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", nargs="*", default=[], help="captures JPEG/PNG")
    ap.add_argument("--telemetry", help="JSON de télémétrie (film-cinematique.mjs)")
    ap.add_argument("--subtitle", default="", help="texte du sous-titre")
    ap.add_argument("--subtitle-file", help="fichier du sous-titre")
    ap.add_argument("--diff-files", nargs="*", default=[], help="fichiers touchés par le diff")
    ap.add_argument("--diff-names-file", help="liste de chemins (git diff --name-only)")
    args = ap.parse_args(argv)
    if not vl_review_enabled():
        print(f"{ENV_FLAG} absent ou ≠ 1 : éteint (la boucle ne l'appelle pas).", file=sys.stderr)
        return 0
    paths = list(args.diff_files)
    if args.diff_names_file:
        src = sys.stdin.read() if args.diff_names_file == "-" else Path(args.diff_names_file).read_text(encoding="utf-8")
        paths.extend(paths_from_name_list(src))
    if not film_diff_touches(paths):
        print("diff hors film : pas d'appel VL.", file=sys.stderr)
        return 0
    telemetry: object = {}
    if args.telemetry:
        telemetry = json.loads(Path(args.telemetry).read_text(encoding="utf-8"))
    subtitle = args.subtitle
    if args.subtitle_file:
        subtitle = Path(args.subtitle_file).read_text(encoding="utf-8")
    comment = review_film(
        images=args.images,
        telemetry=telemetry,
        subtitle=subtitle,
        diff_files=paths,
    )
    if comment:
        print(comment)
    return 0


if __name__ == "__main__":
    sys.exit(main())
