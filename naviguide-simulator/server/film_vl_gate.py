"""Un verdict Super VL ne compte que si chaque défaut daté est sur l'image.

Le passage qui envoie la vidéo au modèle n'est pas dans ce dépôt : ce module
ne l'appelle pas, ne lit aucune clé et n'ouvre aucune connexion. Il tranche
un rapport déjà écrit. L'essai plus fin que 720p à 5 images par seconde est
noté ici ; il ne relance pas le modèle.
"""
from __future__ import annotations

import io
import re
import unicodedata
from typing import Any, Callable, Mapping

BASELINE_HEIGHT = 720
BASELINE_FPS = 5
TRIAL_HEIGHT = 1080
TRIAL_FPS = 10

# Même seuil que la capture du film : page blanche = luminance > 250 et variance < 16.
WHITE_MEAN_ABOVE = 250.0
WHITE_VARIANCE_BELOW = 16.0
# Écran noir : presque aucune lumière, image plate. Une vue de l'application
# autour de 26 de luminance et 86 de variance n'y entre pas.
BLACK_MEAN_BELOW = 12.0
BLACK_VARIANCE_BELOW = 16.0

VERDICT_PASS = "PASS"
VERDICT_KO = "KO"
VERDICT_REFUSE = "REFUSE"

_VERDICT_RE = re.compile(r"VERDICT\s*:\s*(PASS|KO)\b", re.I)
_DEFECT_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\[\s*\]\s*)?(\d{1,2}):([0-5]\d)\s*[:：\-–—]\s*(.+?)\s*$"
)
_SEVERITY_RE = re.compile(r"\s*[—–-]\s*(bloquant|mineur)\s*$", re.I)
_DATE_RE = re.compile(
    r"\b(\d{1,2})(?:er)?\s+([A-Za-zÀ-ÿ]{3,})\b|\b([A-Za-zÀ-ÿ]{3,})\s+(\d{1,2})(?:er)?\b",
    re.I,
)
_PROPER_RE = re.compile(r"\b([A-ZÉÈÊÀÂÎÔÙÛÇ][A-Za-zÀ-ÿ-]{3,})\b")
_QUOTE_RE = re.compile(r"[«\"]([^»\"]{4,})[»\"]")
_EMPTY_RE = re.compile(
    r"^(?:rien|ras|ok|nothing|no defect|aucun|aucun defaut|aucun probleme)\.?$"
)
_BLACK_RE = re.compile(
    r"\b(?:ecran noir|ecrans noirs|image noire|black screen|fond noir)\b"
)
_WHITE_RE = re.compile(
    r"(?:about:blank)|(?:\b(?:carte blanche|carte vide|ecran blanc|image blanche|"
    r"white screen|page blanche|fond blanc)\b)"
)

_MONTHS = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
_NOT_A_NAME = frozenset({
    "ecran", "ecrans", "noir", "noire", "noirs", "black", "screen", "screens",
    "image", "images", "carte", "blanche", "blanc", "white", "blank", "about",
    "page", "fond", "pass", "verdict", "bloquant", "mineur", "rien",
})


class ReviewRefused(RuntimeError):
    """Le rapport ne compte pas : un PASS cite un défaut absent de l'image, ou un KO n'en a aucun de confirmé."""

    def __init__(self, settled: dict):
        self.settled = settled
        super().__init__(settled.get("reason") or "revue refusée")


def _fold(text: str) -> str:
    return unicodedata.normalize("NFD", text or "").encode("ascii", "ignore").decode("ascii").lower()


def is_white_frame(mean: float, variance: float) -> bool:
    return float(mean) > WHITE_MEAN_ABOVE and float(variance) < WHITE_VARIANCE_BELOW


def is_black_frame(mean: float, variance: float) -> bool:
    return float(mean) < BLACK_MEAN_BELOW and float(variance) < BLACK_VARIANCE_BELOW


def scale_filter(height: int, fps: int) -> str:
    """Filtre ffmpeg. La base historique est ``scale=-2:720,fps=5``."""
    h, f = int(height), int(fps)
    if h <= 0 or f <= 0:
        raise ValueError("hauteur et cadence doivent être positives")
    return f"scale=-2:{h},fps={f}"


def ffmpeg_encode_cmd(src: str, dst: str, *, height: int, fps: int) -> list[str]:
    """Commande d'un morceau muet. N'est pas exécutée par la revue."""
    return [
        "ffmpeg", "-nostdin", "-loglevel", "error", "-y",
        "-i", str(src), "-an",
        "-vf", scale_filter(height, fps),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(dst),
    ]


def _as_int(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} doit être un entier")
    if value < 0:
        raise ValueError(f"{name} doit être positif ou nul")
    return value


def note_definition_trial(
    *,
    baseline_misreadings: int | None = None,
    trial_misreadings: int | None = None,
    measured_baseline: Mapping[str, Any] | None = None,
    measured_trial: Mapping[str, Any] | None = None,
) -> dict:
    """Note l'essai 1080p à 10 i/s. ``paid_calls`` reste 0 : aucun second passage.

    ``misreadings_decreased`` reste vide tant que les deux comptes ne sont pas
    fournis. Un compte absent n'est pas remplacé par une valeur.
    """
    if TRIAL_HEIGHT <= BASELINE_HEIGHT or TRIAL_FPS <= BASELINE_FPS:
        raise RuntimeError("l'essai doit dépasser 720p et 5 i/s")
    decreased: bool | None = None
    base_n = trial_n = None
    if baseline_misreadings is not None or trial_misreadings is not None:
        if baseline_misreadings is None or trial_misreadings is None:
            decreased = None
            if baseline_misreadings is not None:
                base_n = _as_int("baseline_misreadings", baseline_misreadings)
            if trial_misreadings is not None:
                trial_n = _as_int("trial_misreadings", trial_misreadings)
        else:
            base_n = _as_int("baseline_misreadings", baseline_misreadings)
            trial_n = _as_int("trial_misreadings", trial_misreadings)
            decreased = trial_n < base_n
    measured: dict[str, Any] = {}
    if measured_baseline is not None or measured_trial is not None:
        if not measured_baseline or not measured_trial:
            raise ValueError("les deux mesures d'encodage sont requises ensemble")
        bh = _as_int("measured_baseline.height", int(measured_baseline["height"]))
        th = _as_int("measured_trial.height", int(measured_trial["height"]))
        bf = float(measured_baseline["fps"])
        tf = float(measured_trial["fps"])
        if isinstance(measured_baseline["fps"], bool) or isinstance(measured_trial["fps"], bool):
            raise TypeError("fps doit être un nombre")
        if th <= bh:
            raise ValueError("la mesure d'essai doit être plus haute que la base")
        if tf <= bf:
            raise ValueError("la mesure d'essai doit être plus rapide que la base")
        measured = {
            "baseline_height": bh,
            "baseline_fps": bf,
            "trial_height": th,
            "trial_fps": tf,
        }
    note = (
        f"Essai {TRIAL_HEIGHT}p à {TRIAL_FPS} i/s, base {BASELINE_HEIGHT}p à {BASELINE_FPS} i/s."
    )
    if measured:
        note += (
            f" Mesuré : essai {measured['trial_height']}p à {measured['trial_fps']:g} i/s,"
            f" base {measured['baseline_height']}p à {measured['baseline_fps']:g} i/s."
        )
    note += " Aucun appel payant."
    if decreased is None:
        note += " Mauvaises lectures non mesurées."
    elif decreased:
        note += f" Mauvaises lectures : {base_n} puis {trial_n}. Elles diminuent."
    else:
        note += f" Mauvaises lectures : {base_n} puis {trial_n}. Elles ne diminuent pas."
    return {
        "baseline_height": BASELINE_HEIGHT,
        "baseline_fps": BASELINE_FPS,
        "trial_height": TRIAL_HEIGHT,
        "trial_fps": TRIAL_FPS,
        "baseline_vf": scale_filter(BASELINE_HEIGHT, BASELINE_FPS),
        "trial_vf": scale_filter(TRIAL_HEIGHT, TRIAL_FPS),
        "paid_calls": 0,
        "baseline_misreadings": base_n if baseline_misreadings is not None else None,
        "trial_misreadings": trial_n if trial_misreadings is not None else None,
        "misreadings_decreased": decreased,
        "measured": measured or None,
        "note": note,
    }


def _luminance(png: bytes) -> tuple[float, float]:
    from PIL import Image

    image = Image.open(io.BytesIO(png)).convert("RGB")
    pixels = list(image.get_flattened_data())
    n = len(pixels)
    if n == 0:
        raise ValueError("image vide")
    acc = 0.0
    acc2 = 0.0
    for r, g, b in pixels:
        y = 0.2126 * r + 0.7152 * g + 0.0722 * b
        acc += y
        acc2 += y * y
    mean = acc / n
    variance = max(0.0, acc2 / n - mean * mean)
    return mean, variance


def read_png(png: bytes, visible_text: str = "") -> dict:
    """Luminance calculée sur les pixels. ``visible_text`` est la lecture de cette image, pas un second modèle."""
    if not isinstance(png, (bytes, bytearray)) or not png:
        raise TypeError("png requis")
    raw = bytes(png)
    try:
        mean, variance = _luminance(raw)
    except Exception as exc:
        raise ValueError("image illisible") from exc
    return {
        "png": raw,
        "mean": mean,
        "variance": variance,
        "visible_text": visible_text or "",
    }


def _dates(text: str) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    for match in _DATE_RE.finditer(text or ""):
        if match.group(1):
            day_s, month_s = match.group(1), match.group(2)
        else:
            month_s, day_s = match.group(3), match.group(4)
        month = _MONTHS.get(_fold(month_s))
        if month is None:
            continue
        day = int(day_s)
        if 1 <= day <= 31:
            found.append((day, month))
    return found


def _visual(desc: str) -> str | None:
    folded = _fold(desc)
    black = _BLACK_RE.search(folded) is not None
    white = _WHITE_RE.search(folded) is not None
    if black and white:
        return "contradiction"
    if black:
        return "black"
    if white:
        return "white"
    return None


def _names(desc: str) -> list[str]:
    quoted = [m.group(1).strip() for m in _QUOTE_RE.finditer(desc or "")]
    proper = [m.group(1) for m in _PROPER_RE.finditer(desc or "")]
    out: list[str] = []
    seen: set[str] = set()
    for raw in quoted + proper:
        folded = _fold(raw)
        if len(folded) < 4 or folded in _MONTHS or folded in _NOT_A_NAME:
            continue
        if folded in seen:
            continue
        seen.add(folded)
        out.append(raw)
    return out


def _parse_line(line: str) -> dict | None:
    match = _DEFECT_RE.match(line or "")
    if not match:
        return None
    desc = _SEVERITY_RE.sub("", match.group(3)).strip()
    if _EMPTY_RE.match(_fold(desc)):
        return None
    minute = int(match.group(1))
    second = int(match.group(2))
    return {
        "t_s": minute * 60 + second,
        "mmss": f"{minute:02d}:{second:02d}",
        "description": desc,
        "visual": _visual(desc),
        "dates": _dates(desc),
        "names": _names(desc),
    }


def parse_dated_defects(text: str) -> list[dict]:
    defects: list[dict] = []
    for line in (text or "").splitlines():
        item = _parse_line(line)
        if item is not None:
            defects.append(item)
    return defects


def _word_in(haystack: str, word: str) -> bool:
    folded = _fold(word)
    if not folded:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(folded)}(?![a-z0-9])", _fold(haystack)) is not None


def _frame_at(frames: Mapping[Any, Any] | Callable[[int], Any] | None, t_s: int) -> Any:
    if frames is None:
        return None
    if callable(frames) and not isinstance(frames, Mapping):
        return frames(t_s)
    if isinstance(frames, Mapping):
        if t_s in frames:
            return frames[t_s]
        return frames.get(str(t_s))
    return None


def _normalize_frame(raw: Any) -> dict | None:
    """Relit les pixels. Une luminance fournie sans image ne confirme ni le noir ni le blanc."""
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        try:
            return read_png(bytes(raw))
        except ValueError:
            return {"mean": None, "variance": None, "visible_text": "", "unreadable": True}
    if not isinstance(raw, Mapping):
        return None
    text = str(raw.get("visible_text") or "")
    png = raw.get("png")
    if isinstance(png, (bytes, bytearray)):
        try:
            return read_png(bytes(png), text)
        except ValueError:
            return {"mean": None, "variance": None, "visible_text": text, "unreadable": True}
    return {"mean": None, "variance": None, "visible_text": text, "unreadable": True}


def _verify_one(defect: dict, frame: dict | None) -> dict:
    reasons: list[str] = []
    if frame is None:
        reasons.append("pas d'image à cet instant")
        return {**defect, "verified": False, "why": " ; ".join(reasons)}
    visual = defect["visual"]
    if visual == "contradiction":
        reasons.append("écran noir et carte blanche dans la même ligne")
    elif visual == "black":
        if frame.get("unreadable") or frame.get("mean") is None:
            reasons.append("image illisible")
        elif not is_black_frame(frame["mean"], frame["variance"]):
            reasons.append("noir absent de l'image")
    elif visual == "white":
        if frame.get("unreadable") or frame.get("mean") is None:
            reasons.append("image illisible")
        elif not is_white_frame(frame["mean"], frame["variance"]):
            reasons.append("blanc absent de l'image")
    text = str(frame.get("visible_text") or "")
    on_image = set(_dates(text))
    for day, month in defect["dates"]:
        if (day, month) not in on_image:
            reasons.append(f"date {day} mois {month} absente de l'image")
    for name in defect["names"]:
        if not _word_in(text, name):
            reasons.append(f"{name} absent de l'image")
    if visual is None and not defect["dates"] and not defect["names"]:
        reasons.append("aucun signe vérifiable sur l'image")
    verified = not reasons
    return {**defect, "verified": verified, "why": "" if verified else " ; ".join(reasons)}


def _report_text(report: str | Mapping[str, Any]) -> tuple[str, str | None]:
    if isinstance(report, str):
        found = _VERDICT_RE.findall(report)
        return report, (found[-1].upper() if found else None)
    if not isinstance(report, Mapping):
        raise TypeError("rapport : texte ou dictionnaire")
    parts = report.get("parts") or []
    if parts:
        text = "\n".join(str((p or {}).get("content") or "") for p in parts)
    else:
        text = str(report.get("content") or "")
    verdict = report.get("verdict")
    if isinstance(verdict, str) and verdict.strip():
        return text, verdict.strip().upper()
    found = _VERDICT_RE.findall(text)
    return text, (found[-1].upper() if found else None)


def settle_review(
    report: str | Mapping[str, Any],
    frames: Mapping[Any, Any] | Callable[[int], Any] | None = None,
    *,
    baseline_misreadings: int | None = None,
    trial_misreadings: int | None = None,
    measured_baseline: Mapping[str, Any] | None = None,
    measured_trial: Mapping[str, Any] | None = None,
) -> dict:
    """Vérifie chaque défaut daté. Un PASS qui en cite un non vérifié est refusé.

    Un KO ne compte que s'il reste au moins un défaut confirmé sur l'image.
    """
    text, raw = _report_text(report)
    checked = [_verify_one(d, _normalize_frame(_frame_at(frames, d["t_s"]))) for d in parse_dated_defects(text)]
    unverified = [d for d in checked if not d["verified"]]
    verified = [d for d in checked if d["verified"]]
    trial = note_definition_trial(
        baseline_misreadings=baseline_misreadings,
        trial_misreadings=trial_misreadings,
        measured_baseline=measured_baseline,
        measured_trial=measured_trial,
    )
    if raw == VERDICT_PASS and unverified:
        bits = [f"{d['mmss']} {d['description']} ({d['why']})" for d in unverified]
        verdict, counts = VERDICT_REFUSE, False
        reason = "PASS refusé : " + " ; ".join(bits)
    elif raw == VERDICT_KO and not verified:
        bits = [f"{d['mmss']} {d['description']} ({d['why']})" for d in checked] or ["aucun défaut daté"]
        verdict, counts = VERDICT_REFUSE, False
        reason = "KO refusé : " + " ; ".join(bits)
    elif raw == VERDICT_PASS:
        verdict, counts = VERDICT_PASS, True
        reason = "PASS : chaque défaut daté est sur l'image" if checked else "PASS : aucun défaut daté"
    elif raw == VERDICT_KO:
        verdict, counts = VERDICT_KO, True
        reason = "KO : au moins un défaut daté est sur l'image"
    else:
        verdict, counts = VERDICT_REFUSE, False
        reason = "revue refusée : verdict absent ou inutilisable"
    return {
        "verdict": verdict,
        "raw_verdict": raw,
        "counts": counts,
        "reason": reason,
        "defects": checked,
        "definition_trial": trial,
    }


def accept_review(
    report: str | Mapping[str, Any],
    frames: Mapping[Any, Any] | Callable[[int], Any] | None = None,
    **trial_kwargs: Any,
) -> dict:
    """Lève ``ReviewRefused`` quand le rapport ne compte pas."""
    settled = settle_review(report, frames, **trial_kwargs)
    if not settled["counts"]:
        raise ReviewRefused(settled)
    return settled
