"""Journal des moments du voyage officiel (lot R9a, contrat PLAN_ICI § 2.1).

Pour chaque perle dans l'ordre de la route : build_moment → signature.
Une ligne seulement quand la signature change. `changes` = diff_moments(prev, cur)
avec un score 1–3. Table dérivée SQLite (`pearl_store.moments`), remplie en
tâche de fond après le réchauffage des perles, jamais au démarrage.
"""
from __future__ import annotations

import logging
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
SCORE_ALERT_OFF = 1
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
    for item in here.get("mpa") or []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("site_id") or item.get("id") or item.get("name") or "")
        if key:
            out[key] = item
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


def _approach_threshold(leg_nm: float | None) -> float:
    span = float(leg_nm) if leg_nm and leg_nm > 0 else APPROACH_NM_FLOOR
    return max(APPROACH_NM_FLOOR, APPROACH_FRAC * span)


def diff_moments(prev: dict | None, cur: dict | None) -> list[dict]:
    """Différence entre deux Moments. Première ligne (prev vide) → []."""
    if not isinstance(cur, dict) or not prev:
        return []
    changes: list[dict] = []

    prev_leg = prev.get("leg") if isinstance(prev.get("leg"), dict) else {}
    cur_leg = cur.get("leg") if isinstance(cur.get("leg"), dict) else {}
    prev_to, cur_to = prev_leg.get("to"), cur_leg.get("to")
    if prev_to and cur_to and prev_to != cur_to:
        changes.append(_change(
            "escale", SCORE_ESCALE,
            f"Arrivée à {prev_to}",
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
        changes.append(_change(
            "escale", SCORE_ESCALE,
            f"Arrivée à {cur_to}",
            f"Reste {rem} nm.",
        ))

    prev_alerts, cur_alerts = _alert_map(prev), _alert_map(cur)
    for aid, alert in cur_alerts.items():
        if aid not in prev_alerts:
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
    for key, item in _mpa_keys(cur).items():
        if key in prev_mpa:
            continue
        name = item.get("name") or key
        nm = item.get("nm")
        fact = f"{name} ({nm} nm)" if nm is not None else str(name)
        changes.append(_change("amp", SCORE_AMP, name, fact))

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


def _clock_near(vertices: list, sail_nm: float) -> dict:
    if not vertices:
        return {}
    return min(
        (v for v in vertices if isinstance(v, dict)),
        key=lambda v: abs(float(v.get("sailNm") or 0) - sail_nm),
        default={},
    )


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


def _leg_at(legs: list[dict], sail_nm: float) -> tuple[int, dict]:
    for idx, jambe in enumerate(legs):
        lo, hi = _as_float(jambe.get("fromNm")), _as_float(jambe.get("toNm"))
        if lo is not None and hi is not None and lo <= sail_nm <= hi:
            return idx, jambe
    if not legs:
        return 0, {}
    first_lo = _as_float(legs[0].get("fromNm"))
    if first_lo is not None and sail_nm < first_lo:
        return 0, legs[0]
    return len(legs) - 1, legs[-1]


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
    legs = _legs_from_voyage(voy)
    thresholds = voy.get("skipper_thresholds") if isinstance(voy.get("skipper_thresholds"), dict) else {
        "galeKt": 34.0,
        "hsAlertM": 3.0,
    }
    rows: list[dict] = []
    prev: dict | None = None
    seq = 0
    prev_rem_live: float | None = None
    prev_leg_idx: int | None = None
    for pearl in pearls:
        sail = _as_float(pearl.get("sailNm"))
        if sail is None:
            at = pearl.get("at") if isinstance(pearl.get("at"), dict) else {}
            sail = 0.0
            clock_guess = {"lat": at.get("lat") or pearl.get("lat"), "lon": at.get("lon") or pearl.get("lon")}
        else:
            clock_guess = None
        clock = _clock_near(vertices, sail if sail is not None else 0.0)
        if clock_guess and not clock:
            clock = clock_guess
        if not isinstance(clock, dict):
            clock = {}
        if clock.get("mode") is None:
            clock = {**clock, "mode": voy.get("mode") or "follow"}
        leg_idx, jambe = _leg_at(legs, sail if sail is not None else 0.0)
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
        same_sig = prev is not None and sig == (prev.get("signature") or signature(prev))
        if same_sig and not approach_hit:
            if live_rem is not None:
                prev_rem_live = live_rem
            prev_leg_idx = leg_idx
            continue
        changes = diff_moments(prev, cur)
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
        rows.append({
            "voyageId": voyage_id,
            "seq": seq,
            "t": cur.get("t"),
            "pos": cur.get("pos") or {"lat": pearl.get("lat"), "lon": pearl.get("lon")},
            "legIdx": leg_idx,
            "signature": sig,
            "changes": changes,
            "moment": cur,
        })
        seq += 1
        prev = cur
    return rows


def warm_moments(voyage_id: str) -> dict[str, Any]:
    """Parcourt les perles, n'écrit que les changements de signature. Idempotent."""
    import pearl_store  # noqa: PLC0415
    from voyage_store import load_voyage  # noqa: PLC0415

    voy = load_voyage(voyage_id)
    if voy is None:
        return {"voyageId": voyage_id, "count": 0, "status": "no-voyage"}
    try:
        rows = _build_rows(voyage_id, voy)
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
