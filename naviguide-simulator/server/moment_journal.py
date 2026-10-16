"""Journal des moments du voyage officiel (lot R9a, contrat PLAN_ICI § 2.1).

Pour chaque perle dans l'ordre de la route : build_moment → signature.
Une ligne seulement quand la signature change. `changes` = diff_moments(prev, cur)
avec un score 1–3. Table dérivée SQLite (`pearl_store.moments`), remplie en
tâche de fond après le réchauffage des perles, jamais au démarrage.
"""
from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone
from typing import Any

from moment import build_moment, signature

log = logging.getLogger("naviguide-simulator.moments")

SCORE_ESCALE = 3
SCORE_ALERT_ON = 3
SCORE_APPROCHE = 3
SCORE_ZEE = 2
SCORE_STATION = 2
SCORE_REGIME = 1
SCORE_AMP = 1
SCORE_PROJECT = 1
SCORE_ALERT_OFF = 1
PROJECT_NEAR_NM = 30.0
APPROACH_NM_FLOOR = 80.0
APPROACH_FRAC = 0.10
_GENERIC_TITLES = frozenset({
    "station croisée", "station", "stations", "croisée", "croisee",
    "marina croisée", "marina", "marinas",
    "aire marine protégée", "amp", "mpa",
    "formalités d'entrée", "ports d'entrée", "port d'entrée",
    "autour du bateau",
})
_NO_DATA_RE = re.compile(
    r"aucun port d'entr[ée]e|no official port of entry|n'est connu",
    re.I,
)
_DIST_PAREN_RE = re.compile(
    r"\s*\(\s*\d+(?:[.,]\d+)?\s*(?:nm|milles?|km)[^)]*\)\s*",
    re.I,
)
_LIST_PREFIX_RE = re.compile(
    r"^(?:ports? d'entr[ée]e|formalit[ée]s d'entr[ée]e|entr[ée]e dans)\s*:?\s*",
    re.I,
)


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _parse_iso(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        raw = raw + "T23:59:59Z"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _iso_le(left: Any, right: Any) -> bool:
    a, b = _parse_iso(left), _parse_iso(right)
    if a is not None and b is not None:
        return a <= b
    return str(left or "") <= str(right or "")


def _alert_map(moment: dict | None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for alert in (moment or {}).get("alerts") or []:
        if isinstance(alert, dict) and alert.get("id"):
            out[str(alert["id"])] = alert
    return out


def _zee(moment: dict | None) -> dict:
    here = (moment or {}).get("here") if isinstance((moment or {}).get("here"), dict) else {}
    zee = here.get("zee") if isinstance(here.get("zee"), dict) else {}
    return zee


def _entry(moment: dict | None) -> dict:
    here = (moment or {}).get("here") if isinstance((moment or {}).get("here"), dict) else {}
    entry = here.get("entry")
    if entry is None:
        entry = _zee(moment).get("entry")
    return entry if isinstance(entry, dict) else {}


def _mpa_keys(moment: dict | None) -> dict[str, dict]:
    here = (moment or {}).get("here") if isinstance((moment or {}).get("here"), dict) else {}
    out: dict[str, dict] = {}
    try:
        from ici_engine import is_fishing_amp, spoken_amp_name  # noqa: PLC0415
    except Exception:
        is_fishing_amp = lambda _item: False  # noqa: E731
        spoken_amp_name = lambda raw, **_k: str(raw or "")  # noqa: E731
    for item in here.get("mpa") or []:
        if not isinstance(item, dict):
            continue
        if is_fishing_amp(item):
            continue
        key = str(item.get("siteId") or item.get("site_id") or item.get("id") or item.get("name") or "")
        if key:
            spoken = spoken_amp_name(item.get("name") or key)
            out[key] = {**item, "name": spoken or item.get("name") or key}
    return out


def _around_by_kind(moment: dict | None, kind: str) -> list[dict]:
    out: list[dict] = []
    for item in (moment or {}).get("around") or []:
        if isinstance(item, dict) and item.get("kind") == kind:
            out.append(item)
    return out


def _around_titles(moment: dict | None) -> list[str]:
    return [
        str(item.get("title") or "")
        for item in (moment or {}).get("around") or []
        if isinstance(item, dict) and item.get("title")
    ]


def _change(kind: str, score: int, title: str, fact: str) -> dict:
    return {"kind": kind, "score": score, "title": str(title or "").strip(), "fact": str(fact or "").strip()}


def _is_generic_title(title: str, kind: str = "") -> bool:
    t = re.sub(r"\s+", " ", str(title or "")).strip().casefold()
    if not t:
        return True
    if t in _GENERIC_TITLES:
        return True
    k = str(kind or "").casefold()
    return bool(k) and (t == k or t == f"{k} croisée" or t == f"{k} croisee")


def named_title(title: Any, fact: Any, kind: str = "") -> str:
    """Nom réel, ou vide (silence). Jamais le type à la place du nom."""
    for raw in (title, fact):
        s = re.sub(r"\s+", " ", str(raw or "")).strip()
        if not s or _NO_DATA_RE.search(s) or _is_generic_title(s, kind):
            continue
        s = _LIST_PREFIX_RE.sub("", s).strip(" :")
        s = _DIST_PAREN_RE.sub("", s).strip()
        s = re.sub(
            r"^(station|marina|aire marine protégée|amp)\s+",
            "",
            s,
            flags=re.I,
        ).strip()
        if s and not _is_generic_title(s, kind):
            return s
    return ""


def _zee_place(name: Any) -> str:
    s = _LIST_PREFIX_RE.sub("", str(name or "").strip()).strip(" :")
    return s


def _stop_title(name: str) -> str:
    """Nom d'escale seul — titre de bulle, sans « Approche de »."""
    return re.sub(r"\s*\([^)]*\)\s*", " ", str(name or "")).strip()


ESCALE_MARK_NEAR_NM = 80.0


def _nm(lat1: Any, lon1: Any, lat2: Any, lon2: Any) -> float | None:
    try:
        p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
        dphi = math.radians(float(lat2) - float(lat1))
        dlamb = math.radians(float(lon2) - float(lon1))
    except (TypeError, ValueError):
        return None
    a = math.sin(dphi / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlamb / 2.0) ** 2
    return 2.0 * 3440.065 * math.asin(min(1.0, math.sqrt(a)))


def _place_key(name: Any) -> str:
    return _stop_title(str(name or "")).casefold()


def _pos_of(moment: dict | None) -> tuple[float | None, float | None]:
    pos = (moment or {}).get("pos") if isinstance((moment or {}).get("pos"), dict) else {}
    return _as_float(pos.get("lat")), _as_float(pos.get("lon"))


def nearest_mark_name(
    marks: list | None, lat: Any, lon: Any, *, limit_nm: float = ESCALE_MARK_NEAR_NM,
) -> str | None:
    """Marque la plus proche des coords, ou None si trop loin. Jamais un nom inventé."""
    if lat is None or lon is None:
        return None
    best_name, best_d = None, float(limit_nm)
    for mark in marks or []:
        if not isinstance(mark, dict) or not mark.get("name"):
            continue
        dist = _nm(lat, lon, mark.get("lat"), mark.get("lon"))
        if dist is not None and dist < best_d:
            best_d = dist
            best_name = str(mark.get("name"))
    return best_name


def _escale_place(cur: dict | None, fallback: Any, marks: list | None) -> str:
    """Nom d'escale : marque sous les coords, sinon le `to` atteint — jamais un prev_to déjà quitté."""
    lat, lon = _pos_of(cur)
    near = nearest_mark_name(marks, lat, lon)
    if near:
        return _stop_title(near)
    return _stop_title(str(fallback or ""))


def _approach_threshold(leg_nm: float | None) -> float:
    span = float(leg_nm) if leg_nm and leg_nm > 0 else APPROACH_NM_FLOOR
    return max(APPROACH_NM_FLOOR, APPROACH_FRAC * span)


def diff_moments(prev: dict | None, cur: dict | None, *, marks: list | None = None) -> list[dict]:
    """Différence entre deux Moments. Première ligne (prev vide) → []."""
    if not isinstance(cur, dict) or not prev:
        return []
    changes: list[dict] = []

    prev_leg = prev.get("leg") if isinstance(prev.get("leg"), dict) else {}
    cur_leg = cur.get("leg") if isinstance(cur.get("leg"), dict) else {}
    prev_to, cur_to = prev_leg.get("to"), cur_leg.get("to")
    if prev_to and cur_to and prev_to != cur_to:
        arrived = _escale_place(cur, None, marks) or _stop_title(str(prev_to))
        if arrived:
            changes.append(_change(
                "escale", SCORE_ESCALE,
                f"Arrivée à {arrived}",
                f"{prev_to} → {cur_to}",
            ))
    rem = _as_float(cur_leg.get("remainingNm"))
    prev_rem = _as_float(prev_leg.get("remainingNm"))
    if (
        rem is not None and rem <= 1.0
        and (prev_rem is None or prev_rem > 1.0)
        and cur_to
        and not any(c.get("kind") == "escale" for c in changes)
    ):
        place = _escale_place(cur, cur_to, marks)
        if place:
            changes.append(_change(
                "escale", SCORE_ESCALE,
                f"Arrivée à {place}",
                f"Reste {rem} nm.",
            ))

    prev_alerts, cur_alerts = _alert_map(prev), _alert_map(cur)
    try:
        from ici_engine import is_fishing_amp  # noqa: PLC0415
    except Exception:
        is_fishing_amp = lambda _item: False  # noqa: E731
    for aid, alert in cur_alerts.items():
        if aid not in prev_alerts:
            if is_fishing_amp(alert):
                continue
            changes.append(_change(
                "alert-on", SCORE_ALERT_ON,
                alert.get("title") or aid,
                alert.get("fact") or alert.get("title") or aid,
            ))
    for aid, alert in prev_alerts.items():
        if aid not in cur_alerts:
            changes.append(_change(
                "alert-off", SCORE_ALERT_OFF,
                alert.get("title") or aid,
                alert.get("fact") or alert.get("title") or aid,
            ))

    prev_mrgid, cur_mrgid = _zee(prev).get("mrgid"), _zee(cur).get("mrgid")
    cur_name = _zee_place(_zee(cur).get("name"))
    if cur_mrgid and cur_mrgid != prev_mrgid and cur_name:
        changes.append(_change("zee-enter", SCORE_ZEE, cur_name, cur_name))
    elif prev_mrgid and not cur_mrgid:
        prev_name = _zee_place(_zee(prev).get("name"))
        if prev_name:
            changes.append(_change(
                "zee-enter", SCORE_ZEE,
                "Haute mer",
                f"Sortie de {prev_name}.",
            ))
    elif _entry(prev) != _entry(cur) and not any(c.get("kind") == "zee-enter" for c in changes):
        ports = [str(p).strip() for p in (_entry(cur).get("ports") or []) if str(p).strip()]
        known = bool(_entry(cur).get("known"))
        port = named_title(ports[0] if ports else "", "", "port")
        if known and port:
            changes.append(_change("port", SCORE_ZEE, port, port))

    prev_sci = {item.get("fact") or item.get("title") for item in _around_by_kind(prev, "science")}
    for item in _around_by_kind(cur, "science"):
        key = item.get("fact") or item.get("title")
        title = named_title(item.get("title"), item.get("fact"), "station")
        if key and key not in prev_sci and title:
            changes.append(_change(
                "station", SCORE_STATION,
                title,
                item.get("fact") or title,
            ))

    prev_reg, cur_reg = prev_leg.get("regime"), cur_leg.get("regime")
    if cur_reg and cur_reg != prev_reg:
        label = {"hindcast": "hindcast", "forecast": "prévision", "climatology": "climatologie"}.get(
            str(cur_reg), str(cur_reg)
        )
        changes.append(_change(
            "regime", SCORE_REGIME,
            f"Régime {label}",
            f"{prev_reg or '—'} → {cur_reg}",
        ))

    prev_mpa = _mpa_keys(prev)
    cur_mpa = _mpa_keys(cur)

    def _amp_change(item: dict, key: str, event: str, *, nm: Any, inside: bool) -> dict:
        name = item.get("name") or key
        fact = f"{name} ({nm} nm)" if nm is not None else str(name)
        ch = _change("amp", SCORE_AMP, name, fact)
        if nm is not None:
            ch["nm"] = nm
        ch["event"] = event
        ch["inside"] = inside
        site = item.get("siteId") or item.get("site_id") or item.get("id")
        if site:
            ch["siteId"] = site
            ch["site_id"] = site
        if item.get("traffic"):
            ch["traffic"] = item.get("traffic")
        if item.get("entry") is not None:
            ch["entry"] = item.get("entry")
        if item.get("speed") is not None:
            ch["speed"] = item.get("speed")
        return ch

    for key, item in cur_mpa.items():
        prev_item = prev_mpa.get(key)
        inside = bool(item.get("inside"))
        was_inside = bool(prev_item.get("inside")) if prev_item else False
        if inside and not was_inside:
            changes.append(_amp_change(item, key, "enter", nm=0, inside=True))
        elif prev_item is None and not inside:
            nm = item.get("nm")
            changes.append(_amp_change(item, key, "nearby", nm=nm, inside=False))
    for key, item in prev_mpa.items():
        cur_item = cur_mpa.get(key)
        if not item.get("inside"):
            continue
        if cur_item is not None and cur_item.get("inside"):
            continue
        changes.append(_amp_change(item, key, "exit", nm=0, inside=False))

    if not changes:
        prev_titles, cur_titles = _around_titles(prev), _around_titles(cur)
        added = [t for t in cur_titles if t not in prev_titles]
        removed = [t for t in prev_titles if t not in cur_titles]
        if added or removed:
            item = next(
                (x for x in (cur.get("around") or []) if isinstance(x, dict) and x.get("title") in added),
                None,
            )
            kind = (item or {}).get("kind") or "station"
            score = SCORE_STATION if kind == "science" else SCORE_REGIME
            raw = added[0] if added else (removed[0] if removed else "")
            title = named_title(raw, (item or {}).get("fact"), kind)
            if title:
                fact = (item or {}).get("fact") or title
                changes.append(_change(kind if kind == "science" else kind, score, title, fact))

    return [c for c in changes if c.get("title") and c.get("fact")]


class _ClockIndex:
    """Sommets triés par sailNm + recherche dichotomique. Avant (27 sept.) : un `min` linéaire sur 8 878
    sommets pour chacune des 3 272 perles — 46 s de CPU dans l'API à chaque démarrage (profil cProfile)."""

    def __init__(self, vertices: list):
        import bisect  # noqa: PLC0415
        from collections import defaultdict  # noqa: PLC0415
        self._bisect = bisect
        rows = [v for v in (vertices or []) if isinstance(v, dict)]
        rows.sort(key=lambda v: float(v.get("sailNm") or 0))
        self.rows = rows
        self.keys = [float(v.get("sailNm") or 0) for v in rows]
        buckets: dict[int, list] = defaultdict(list)
        for vertex, key in zip(rows, self.keys):
            buckets[int(round(key))].append(vertex)
        self._buckets = buckets

    def near(self, sail_nm: float, lat: float | None = None, lon: float | None = None) -> dict:
        if not self.rows:
            return {}
        i = self._bisect.bisect_left(self.keys, sail_nm)
        cands = [j for j in (i - 1, i) if 0 <= j < len(self.rows)]
        best = min(cands, key=lambda j: abs(self.keys[j] - sail_nm))
        row = self.rows[best]
        if lat is None or lon is None:
            return row
        geo: list[dict] = []
        center = int(round(sail_nm))
        for key in (center - 1, center, center + 1):
            geo.extend(self._buckets.get(key) or [])
        if not geo:
            return row

        def dist(vertex: dict) -> float:
            d = _nm(lat, lon, vertex.get("lat"), vertex.get("lon"))
            return d if d is not None else 1e12

        return min(geo, key=dist)


def _clock_near(
    vertices: list, sail_nm: float, lat: float | None = None, lon: float | None = None,
) -> dict:
    if not vertices:
        return {}
    if isinstance(vertices, _ClockIndex):
        return vertices.near(sail_nm, lat, lon)
    return _ClockIndex(vertices).near(sail_nm, lat, lon)


def _legs_from_voyage(voy: dict) -> list[dict]:
    legs = [leg for leg in (voy.get("legs") or []) if isinstance(leg, dict)]
    if legs:
        return legs
    marks = [m for m in (voy.get("marks") or []) if isinstance(m, dict)]
    marks = sorted(marks, key=lambda m: float(m.get("nm") if m.get("nm") is not None else m.get("filmNm") or 0))
    out: list[dict] = []
    for left, right in zip(marks, marks[1:]):
        out.append({
            "from": left.get("name"),
            "to": right.get("name"),
            "fromNm": float(left.get("nm") if left.get("nm") is not None else left.get("filmNm") or 0),
            "toNm": float(right.get("nm") if right.get("nm") is not None else right.get("filmNm") or 0),
            "regime": "climatology",
        })
    return out


def _leg_at(
    legs: list[dict],
    sail_nm: float,
    pos: dict | None = None,
    marks: list | None = None,
) -> tuple[int, dict]:
    hits: list[tuple[int, dict]] = []
    for idx, jambe in enumerate(legs):
        lo, hi = _as_float(jambe.get("fromNm")), _as_float(jambe.get("toNm"))
        if lo is not None and hi is not None and lo <= sail_nm <= hi:
            hits.append((idx, jambe))
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        lat = _as_float((pos or {}).get("lat")) if isinstance(pos, dict) else None
        lon = _as_float((pos or {}).get("lon")) if isinstance(pos, dict) else None
        place = nearest_mark_name(marks, lat, lon)
        key = _place_key(place) if place else ""
        if key:
            named = [
                pair for pair in hits
                if key == _place_key(pair[1].get("to"))
                or key == _place_key(pair[1].get("from"))
                or key in str(pair[1].get("to") or "").casefold()
                or key in str(pair[1].get("from") or "").casefold()
            ]
            to_hits = [
                pair for pair in named
                if key == _place_key(pair[1].get("to"))
                or key in str(pair[1].get("to") or "").casefold()
            ]
            if to_hits or named:
                return (to_hits or named)[0]
            earlier_to = _place_key(hits[0][1].get("to"))
            if key != earlier_to and key not in str(hits[0][1].get("to") or "").casefold():
                return hits[-1]
        return hits[0]
    if not legs:
        return 0, {}
    first_lo = _as_float(legs[0].get("fromNm"))
    if first_lo is not None and sail_nm < first_lo:
        return 0, legs[0]
    return len(legs) - 1, legs[-1]


PLACE_NEAR_NM = 15.0          # une marina « croisée » : à moins de 15 nm de la route
COAST_NEAR_NM = 25.0          # ports / WPI → jalon de côte (RG2)
SCORE_PLACE = 2
_PLACE_LISTS = (
    ("marina", "marinas", PLACE_NEAR_NM),
    ("coast", "wpi", COAST_NEAR_NM),
    ("coast", "capitaineries", COAST_NEAR_NM),
)


def _norm_place(name: Any) -> str:
    return re.sub(r"\s+", " ", str(name or "")).strip().casefold()


def _new_places_nearby(pearl: dict, seen: set[tuple[str, str]]) -> list[dict]:
    """Marinas (15 nm) et ports / WPI (25 nm) du sac, pas encore cités → marina | coast.
    Sans nom, ou trop loin : rien. Aucun nom inventé."""
    nearby = pearl.get("nearby") if isinstance(pearl.get("nearby"), dict) else {}
    out: list[dict] = []
    for kind, field, limit in _PLACE_LISTS:
        title_kind = "port" if kind == "coast" else kind
        for item in nearby.get(field) or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name or _is_generic_title(name, title_kind) or len(name) > 40 or "|" in name:
                continue
            if re.search(r"\b(tour|excursion|activit|autorit[ée]s?|club nautique de plaisance|charter)\b", name, re.I):
                continue      # une activité ou une administration, pas un port
            nm = _as_float(item.get("nm"))
            if nm is not None and nm > limit:
                continue
            key = (kind, _norm_place(name))
            if key in seen:
                continue
            seen.add(key)
            fact = f"{name} ({nm:.0f} nm)" if nm is not None else name
            out.append(_change(kind, SCORE_PLACE, name, fact))
    return out


def _gold_rank(item: dict) -> int:
    return 0 if item.get("gold_on") in (True, 1, "1", "true", "True") else 1


def _new_projects_nearby(pearl: dict, seen: set[tuple[str, str]]) -> list[dict]:
    """Projets Blue Intelligence à ≤ 30 nm, une fois chacun. gold_on puis plus proche."""
    rows = [p for p in (pearl.get("projects") or []) if isinstance(p, dict) and p.get("name")]
    rows.sort(key=lambda p: (
        _gold_rank(p),
        _as_float(p.get("nm")) if _as_float(p.get("nm")) is not None else 999.0,
    ))
    out: list[dict] = []
    for item in rows:
        name = str(item.get("name") or "").strip()
        if not name or _is_generic_title(name, "project"):
            continue
        nm = _as_float(item.get("nm"))
        if nm is not None and nm > PROJECT_NEAR_NM:
            continue
        key = ("project", _norm_place(name))
        if key in seen:
            continue
        seen.add(key)
        fact = f"{name} ({nm:.0f} nm)" if nm is not None else name
        ch = _change("project", SCORE_PROJECT, name, fact)
        if nm is not None:
            ch["nm"] = nm
        if _gold_rank(item) == 0:
            ch["gold_on"] = True
        out.append(ch)
    return out


def _voyage_marks(voy: dict) -> list[dict]:
    """Marques d'horloge (datées) puis d'itinéraire — pas de doublon exact."""
    out: list[dict] = []
    seen: set[tuple] = set()
    clock = voy.get("clock") if isinstance(voy.get("clock"), dict) else {}
    for mark in list(clock.get("marks") or []) + list(voy.get("marks") or []):
        if not isinstance(mark, dict) or not mark.get("name"):
            continue
        key = (
            str(mark.get("name")),
            round(float(mark.get("lat") or 0), 3),
            round(float(mark.get("lon") or 0), 3),
            str(mark.get("iso") or mark.get("tHours") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(mark)
    return out


def _iso_from_matching_mark(marks: list | None, title: Any, t: Any) -> str | None:
    """ISO de la marque au même nom, la plus proche de t. Rien d'inventé."""
    place = re.sub(r"^arrivée à\s+", "", str(title or "").strip(), flags=re.I)
    key = _place_key(place)
    if not key:
        return None
    cands = []
    for mark in marks or []:
        if not isinstance(mark, dict) or not mark.get("iso"):
            continue
        name = str(mark.get("name") or "")
        if key != _place_key(name) and key not in name.casefold():
            continue
        cands.append(mark)
    if not cands:
        return None
    target = _parse_iso(t)

    def closeness(mark: dict) -> float:
        when = _parse_iso(mark.get("iso"))
        if target and when:
            return abs((when - target).total_seconds())
        return 1e18

    return str((min(cands, key=closeness) if target else cands[0]).get("iso") or "") or None


def _escale_duplicate_same_day(rows: list[dict], title: Any, t: Any) -> bool:
    day = str(t or "")[:10]
    if len(day) < 10:
        return False
    key = _place_key(re.sub(r"^arrivée à\s+", "", str(title or ""), flags=re.I))
    if not key:
        return False
    for row in rows:
        if str(row.get("t") or "")[:10] != day:
            continue
        for change in row.get("changes") or []:
            if not isinstance(change, dict) or change.get("kind") != "escale":
                continue
            other = _place_key(re.sub(r"^arrivée à\s+", "", str(change.get("title") or ""), flags=re.I))
            if other == key:
                return True
    return False


def _pearls_in_route_order(voy: dict) -> list[dict]:
    embedded = [p for p in (voy.get("pearls") or []) if isinstance(p, dict)]
    if embedded:
        return sorted(embedded, key=lambda p: float(p.get("sailNm") or 0))

    points = voy.get("points") or []
    if not points:
        return []
    try:
        from ici_engine import thin_cache_key  # noqa: PLC0415
        from ici_warm import sample_route_nm  # noqa: PLC0415
        import pearl_store  # noqa: PLC0415
    except Exception:
        return []
    out: list[dict] = []
    for sample in sample_route_nm(points):
        try:
            lat, lon = float(sample["lat"]), float(sample["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        row = pearl_store.get_pearl(thin_cache_key(lat, lon, 30.0))
        if not row or not isinstance(row.get("bag"), dict):
            continue
        bag = dict(row["bag"])
        bag.setdefault("lat", lat)
        bag.setdefault("lon", lon)
        bag.setdefault("sailNm", sample.get("sailNm"))
        bag.setdefault("at", {"lat": lat, "lon": lon})
        out.append(bag)
    return out


def _build_rows(voyage_id: str, voy: dict) -> list[dict]:
    pearls = _pearls_in_route_order(voy)
    vertices = (voy.get("clock") or {}).get("vertices") or []
    if not isinstance(vertices, list):
        vertices = []
    vertices = _ClockIndex(vertices)   # indexé une fois, interrogé 3 272 fois
    legs = _legs_from_voyage(voy)
    marks = _voyage_marks(voy)
    thresholds = voy.get("skipper_thresholds") if isinstance(voy.get("skipper_thresholds"), dict) else {
        "galeKt": 34.0,
        "hsAlertM": 3.0,
    }
    rows: list[dict] = []
    prev: dict | None = None
    seq = 0
    prev_rem_live: float | None = None
    prev_leg_idx: int | None = None
    seen_places: set[tuple[str, str]] = set()
    for pearl in pearls:
        sail = _as_float(pearl.get("sailNm"))
        at = pearl.get("at") if isinstance(pearl.get("at"), dict) else {}
        pearl_lat = _as_float(at.get("lat")) or _as_float(pearl.get("lat"))
        pearl_lon = _as_float(at.get("lon")) or _as_float(pearl.get("lon"))
        if sail is None:
            sail = 0.0
            clock_guess = {"lat": pearl_lat, "lon": pearl_lon}
        else:
            clock_guess = None
        clock = _clock_near(vertices, sail if sail is not None else 0.0, pearl_lat, pearl_lon)
        if clock_guess and not clock:
            clock = clock_guess
        if not isinstance(clock, dict):
            clock = {}
        if clock.get("mode") is None:
            clock = {**clock, "mode": voy.get("mode") or "follow"}
        pos = {"lat": pearl_lat, "lon": pearl_lon} if pearl_lat is not None else None
        leg_idx, jambe = _leg_at(
            legs, sail if sail is not None else 0.0, pos=pos, marks=marks,
        )
        cur = build_moment(pearl, clock, jambe, thresholds, lang="fr")
        sig = cur.get("signature") or signature(cur)
        to_nm = _as_float(jambe.get("toNm"))
        from_nm = _as_float(jambe.get("fromNm"))
        leg_nm = (to_nm - from_nm) if to_nm is not None and from_nm is not None else _as_float(jambe.get("legNm"))
        live_rem = (to_nm - sail) if to_nm is not None and sail is not None else None
        if prev_leg_idx is not None and leg_idx != prev_leg_idx and leg_nm is not None:
            prev_rem_live = float(leg_nm)
        cur_to = (cur.get("leg") or {}).get("to") if isinstance(cur.get("leg"), dict) else jambe.get("to")
        thr = _approach_threshold(leg_nm)
        approach_hit = (
            prev_rem_live is not None
            and live_rem is not None
            and bool(cur_to)
            and live_rem <= thr < prev_rem_live
            and live_rem > 1.0
        )
        # Marinas (15 nm) et jalons de côte (ports / WPI, 25 nm) : une fois chacun (RG2).
        # Projets BI à ≤ 30 nm (RG3).
        new_places = _new_places_nearby(pearl, seen_places)
        new_projects = _new_projects_nearby(pearl, seen_places)
        same_sig = prev is not None and sig == (prev.get("signature") or signature(prev))
        if same_sig and not approach_hit and not new_places and not new_projects:
            if live_rem is not None:
                prev_rem_live = live_rem
            prev_leg_idx = leg_idx
            continue
        # L'ancien « le port / la marina la plus proche a changé » répétait le même nom à chaque pas.
        changes = [
            c for c in diff_moments(prev, cur, marks=marks)
            if c.get("kind") not in {"marina", "port", "coast", "project"}
        ]
        changes.extend(new_places)
        changes.extend(new_projects)
        if approach_hit:
            title = _stop_title(str(cur_to))
            already = any(
                c.get("kind") == "approche"
                or (c.get("kind") == "escale" and title and title in (c.get("title") or ""))
                for c in changes
            )
            if not already:
                rem_nm = int(round(live_rem))
                changes.append(_change(
                    "approche", SCORE_APPROCHE, title,
                    f"Approche de {title}, reste {rem_nm} milles nautiques.",
                ))
        if live_rem is not None:
            prev_rem_live = live_rem
        prev_leg_idx = leg_idx
        t = cur.get("t")
        escale = next((c for c in changes if c.get("kind") == "escale"), None)
        if escale:
            snapped = _iso_from_matching_mark(marks, escale.get("title"), t)
            if snapped:
                t = snapped
            if _escale_duplicate_same_day(rows, escale.get("title"), t):
                changes = [c for c in changes if c.get("kind") != "escale"]
        rows.append({
            "voyageId": voyage_id,
            "seq": seq,
            "t": t,
            "pos": cur.get("pos") or {"lat": pearl_lat, "lon": pearl_lon},
            "legIdx": leg_idx,
            "signature": sig,
            "changes": changes,
            "moment": cur,
        })
        seq += 1
        prev = cur
    _attach_climo_changes(rows, voy.get("clock") if isinstance(voy.get("clock"), dict) else {})
    return rows


def _climo_row_dist(row: dict, event: dict) -> float:
    sail = _as_float(event.get("sailNm"))
    if sail is not None:
        pos = row.get("pos") if isinstance(row.get("pos"), dict) else {}
        moment = row.get("moment") if isinstance(row.get("moment"), dict) else {}
        here = moment.get("pos") if isinstance(moment.get("pos"), dict) else pos
        row_sail = _as_float((moment.get("leg") or {}).get("sailNm") if isinstance(moment.get("leg"), dict) else None)
        if row_sail is None:
            row_sail = _as_float(row.get("sailNm"))
        if row_sail is not None:
            return abs(row_sail - sail)
        lat, lon = _as_float((here or {}).get("lat")), _as_float((here or {}).get("lon"))
        ev_lat, ev_lon = _as_float(event.get("lat")), _as_float(event.get("lon"))
        if None not in (lat, lon, ev_lat, ev_lon):
            return abs(lat - ev_lat) + abs(lon - ev_lon)
    ev_t, row_t = _parse_iso(event.get("t") or event.get("iso")), _parse_iso(row.get("t"))
    if ev_t and row_t:
        return abs((ev_t - row_t).total_seconds())
    return 1e12


def _attach_climo_changes(rows: list[dict], clock: dict) -> None:
    """Pose les bascules d'horloge sur le moment le plus proche (date / sailNm)."""
    if not rows:
        return
    try:
        from climo_events import notable_climo_changes  # noqa: PLC0415
    except Exception:
        return
    seen = {str(c.get("id") or "") for row in rows for c in (row.get("changes") or []) if isinstance(c, dict)}
    for event in notable_climo_changes(clock):
        eid = str(event.get("id") or "")
        if eid and eid in seen:
            continue
        best = min(rows, key=lambda row: _climo_row_dist(row, event))
        changes = list(best.get("changes") or [])
        changes.append(event)
        best["changes"] = changes
        if eid:
            seen.add(eid)
        if event.get("t") and not best.get("t"):
            best["t"] = event["t"]


def _with_clock(voy: dict) -> dict:
    """Depuis RF2 l'horloge officielle vit dans le stock (famille climo), plus dans le JSON du voyage :
    sans elle, `_build_rows` ne peut dater aucune perle (27 sept. : 740 moments avec t = NULL, donc un
    film sans aucun événement). On la prend dans le stock quand le voyage ne l'a pas."""
    if isinstance(voy.get("clock"), dict) and (voy["clock"].get("vertices") or []):
        return voy
    try:
        from official_store import stored_clock  # noqa: PLC0415
        clock = stored_clock()
    except Exception:
        clock = None
    return {**voy, "clock": clock} if clock else voy


def rows_from_voyage(voyage_id: str, voy: dict) -> list[dict]:
    """Moments datés, même forme que le journal officiel. `voy['pearls']` si déjà chargées."""
    return _build_rows(voyage_id, voy)


def warm_moments(voyage_id: str, voy: dict | None = None) -> dict[str, Any]:
    """Parcourt les perles, n'écrit que les changements de signature. Idempotent.
    `voy` : le voyage déjà chargé (avec son horloge) ; sinon relu du disque, horloge du stock si besoin."""
    import pearl_store  # noqa: PLC0415
    from voyage_store import load_voyage  # noqa: PLC0415

    voy = voy if voy is not None else load_voyage(voyage_id)
    if voy is None:
        return {"voyageId": voyage_id, "count": 0, "status": "no-voyage"}
    voy = _with_clock(voy)
    try:
        rows = _build_rows(voyage_id, voy)
        if rows and not any(r.get("t") for r in rows):
            # Des moments sans date ne servent ni au Journal ni au film : mieux vaut le dire que les ranger.
            log.warning("warm_moments(%s) : %d moments sans date (horloge absente ?) — rien n'est écrit", voyage_id, len(rows))
            return {"voyageId": voyage_id, "count": pearl_store.count_moments(voyage_id), "status": "undated"}
        n = pearl_store.replace_moments(voyage_id, rows)
        return {"voyageId": voyage_id, "count": n, "status": "ready"}
    except Exception as exc:
        log.warning("warm_moments(%s) : %s", voyage_id, exc)
        return {"voyageId": voyage_id, "count": pearl_store.count_moments(voyage_id), "status": "error"}


def read_moments(voyage_id: str, until: str | None = None) -> list[dict]:
    """Lit le journal. `until` (ISO) coupe à t ≤ until (date seule = fin de ce jour UTC)."""
    import pearl_store  # noqa: PLC0415

    rows = pearl_store.list_moments(voyage_id)
    if until:
        rows = [row for row in rows if _iso_le(row.get("t"), until)]
    return rows
