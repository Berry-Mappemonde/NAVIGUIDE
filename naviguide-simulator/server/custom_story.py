"""Moments d'un voyage perso (lot DM8A) — même pipeline que l'officiel, à la demande.

Contrat (DM8B / DM8C) :
  moments_for_voyage(voyage, *, budget_nm=2000) →
    {status, moments, coverageNm, totalNm, fingerprint, computedAt, skipped}

- empreinte sha1 courte (points 1e-4, t0, polaire / facteur, ICI_REV) ;
- cache kv namespace ``custom-moments``, TTL 7 jours ;
- au plus ``budget_nm`` milles de perles par appel, reprise au suivant ;
- un seul calcul à la fois par processus (verrou) ; les autres → preparing ;
- aucun LLM ; le stock officiel n'est ni lu ni écrit.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from ici_warm import SAMPLE_NM, sample_route_nm

log = logging.getLogger("naviguide-simulator.custom-story")

NS = "custom-moments"
TTL_S = 7 * 86400.0
DEFAULT_BUDGET_NM = 2000.0
RADIUS_NM = 30.0
# Un sac riche froid coûte 1–8 s : sans borne de temps, GET /moments tenait
# plusieurs minutes (La Rochelle → Horta, 55 perles). Reprise au poll suivant.
MAX_CHUNK_S = float(os.environ.get("NAVIGUIDE_CUSTOM_MOMENTS_CHUNK_S") or 12.0)

_COMPUTE_LOCK = threading.Lock()


def _now_iso() -> str:
    from voyage_clock import to_iso  # noqa: PLC0415
    return to_iso(datetime.now(timezone.utc))


def _ici_rev() -> str:
    try:
        from official_store import ICI_REV, MOMENTS_REV  # noqa: PLC0415
        return f"{ICI_REV}:{MOMENTS_REV}"
    except Exception:
        try:
            from ici_engine import PEARL_REV  # noqa: PLC0415
            return str(PEARL_REV)
        except Exception:
            return "rg3"


def _speed_factor() -> float:
    try:
        from voyage_clock import polar_efficiency  # noqa: PLC0415
        return round(float(polar_efficiency()), 4)
    except Exception:
        return 1.0


def voyage_fingerprint(voyage: dict) -> str:
    """sha1 court de (points 1e-4, t0, polaire / facteur de vitesse, ICI_REV)."""
    points: list[list[float]] = []
    for p in voyage.get("points") or []:
        if not isinstance(p, dict):
            continue
        try:
            points.append([round(float(p["lat"]), 4), round(float(p["lon"]), 4)])
        except (KeyError, TypeError, ValueError):
            continue
    marks: list[list] = []
    for m in voyage.get("marks") or []:
        if not isinstance(m, dict):
            continue
        try:
            nm = m.get("nm")
            if nm is None:
                nm = m.get("filmNm") or 0
            marks.append([str(m.get("name") or ""), round(float(nm), 1)])
        except (TypeError, ValueError):
            continue
    blob = json.dumps(
        {
            "points": points,
            "marks": marks,
            "t0": str(voyage.get("t0") or ""),
            "polar": str(voyage.get("expedition_id") or ""),
            "speedFactor": _speed_factor(),
            "startAt": str(voyage.get("startAt") or ""),
            "iciRev": _ici_rev(),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


def _pointer_key(voyage_id: str) -> str:
    return f"id:{voyage_id}"


def drop_cached_moments(voyage_id: str) -> None:
    """Supprime l'entrée custom-moments d'un voyage purgé. Jamais d'exception."""
    if not voyage_id:
        return
    try:
        import pearl_store  # noqa: PLC0415
        hit = pearl_store.kv_get(NS, _pointer_key(voyage_id))
        fp = None
        if hit:
            val = hit.get("value")
            if isinstance(val, str):
                fp = val
            elif isinstance(val, dict):
                fp = val.get("fingerprint")
        pearl_store.kv_delete(NS, _pointer_key(voyage_id))
        if fp:
            pearl_store.kv_delete(NS, fp)
    except Exception as exc:
        log.warning("purge custom-moments %s : %s", voyage_id, exc)


def _load_entry(fp: str) -> Optional[dict]:
    import pearl_store  # noqa: PLC0415
    hit = pearl_store.kv_get(NS, fp, max_age_s=TTL_S)
    if not hit:
        return None
    val = hit.get("value")
    return val if isinstance(val, dict) else None


def _save_entry(fp: str, voyage_id: str | None, entry: dict) -> None:
    import pearl_store  # noqa: PLC0415
    pearl_store.kv_put(NS, fp, entry)
    if voyage_id:
        pearl_store.kv_put(NS, _pointer_key(voyage_id), fp)


def _public(entry: dict) -> dict:
    return {
        "status": entry.get("status") or "preparing",
        "moments": list(entry.get("moments") or []),
        "coverageNm": float(entry.get("coverageNm") or 0),
        "totalNm": float(entry.get("totalNm") or 0),
        "fingerprint": str(entry.get("fingerprint") or ""),
        "computedAt": entry.get("computedAt") or _now_iso(),
        "skipped": int(entry.get("skipped") or 0),
        **({"voyageId": entry["voyageId"]} if entry.get("voyageId") else {}),
    }


def preparing_payload(voyage: dict | None = None, *, fingerprint: str = "",
                      reason: str | None = None) -> dict:
    vid = (voyage or {}).get("voyageId")
    out = {
        "status": "preparing",
        "moments": [],
        "coverageNm": 0.0,
        "totalNm": 0.0,
        "fingerprint": fingerprint or (voyage_fingerprint(voyage) if voyage else ""),
        "computedAt": _now_iso(),
        "skipped": 0,
    }
    if vid:
        out["voyageId"] = vid
    if reason:
        out["reason"] = str(reason)
    return out


def _clock_for(voyage: dict) -> Optional[dict]:
    clock = voyage.get("clock") if isinstance(voyage.get("clock"), dict) else None
    if clock and (clock.get("vertices") or []):
        return clock
    t0 = voyage.get("t0")
    if not t0:
        return None
    try:
        from voyage_clock import build_voyage_clock  # noqa: PLC0415
    except Exception:
        return None
    polar_raw = None
    try:
        from polar_api import _load_polar_data  # noqa: PLC0415
        polar = _load_polar_data(voyage.get("expedition_id") or "")
        polar_raw = {
            "twa_rows": list(polar.twa_rows),
            "tws_cols": list(polar.tws_cols),
            "matrix": polar.matrix.tolist(),
        }
    except Exception:
        polar_raw = None
    try:
        return build_voyage_clock(
            voyage.get("points") or [],
            voyage.get("marks") or [],
            t0,
            polar_raw=polar_raw,
            start_at=voyage.get("startAt") or "la-rochelle",
            wind_fn=None,
        )
    except Exception as exc:
        log.warning("horloge perso : %s", exc)
        return None


def _bag_key(lat: float, lon: float) -> str:
    from ici_engine import thin_cache_key  # noqa: PLC0415
    return thin_cache_key(lat, lon, RADIUS_NM)


def _resolve_bag(
    lat: float,
    lon: float,
    bag_fn: Optional[Callable[[float, float], Any]],
    skipped_keys: set[str],
) -> tuple[Optional[dict], bool]:
    """(bag | None, called_fill). None = sauter la perle."""
    from ici_engine import thin_cache_get, thin_cache_put  # noqa: PLC0415

    key = _bag_key(lat, lon)
    if key in skipped_keys:
        return None, False
    cached = thin_cache_get(key)
    if cached is not None:
        return cached, False
    try:
        if bag_fn is not None:
            bag = bag_fn(lat, lon)
        else:
            from ici_warm import get_pearl_bag  # noqa: PLC0415
            bag = get_pearl_bag(lat, lon)
    except Exception as exc:
        log.debug("sac /ici perso %.4f,%.4f : %s", lat, lon, exc)
        skipped_keys.add(key)
        return None, True
    if not isinstance(bag, dict):
        skipped_keys.add(key)
        return None, True
    try:
        thin_cache_put(key, bag, "thin", lat, lon)
    except Exception:
        pass
    return bag, True


def _advance(
    voyage: dict,
    samples: list[dict],
    entry: dict,
    *,
    budget_nm: float,
    bag_fn: Optional[Callable[[float, float], Any]],
) -> dict:
    from moment_journal import rows_from_voyage  # noqa: PLC0415

    total_nm = float(samples[-1]["sailNm"]) if samples else 0.0
    done = int(entry.get("done") or 0)
    skipped_keys = set(entry.get("skippedKeys") or [])
    skipped = int(entry.get("skipped") or 0)

    if done >= len(samples):
        entry["status"] = "ready"
        entry["coverageNm"] = total_nm
        entry["totalNm"] = total_nm
        entry["computedAt"] = _now_iso()
        return entry

    budget = float(budget_nm) if budget_nm and budget_nm > 0 else SAMPLE_NM
    base_nm = float(samples[done].get("sailNm") or 0)
    limit_nm = base_nm + budget
    chunk_s = float(MAX_CHUNK_S) if MAX_CHUNK_S and MAX_CHUNK_S > 0 else 1e9
    deadline = time.monotonic() + chunk_s

    def _pearl(sample: dict) -> Optional[dict]:
        try:
            lat, lon = float(sample["lat"]), float(sample["lon"])
        except (KeyError, TypeError, ValueError):
            return None
        bag, _called = _resolve_bag(lat, lon, bag_fn, skipped_keys)
        if bag is None:
            return None
        pearl = dict(bag)
        pearl.setdefault("lat", lat)
        pearl.setdefault("lon", lon)
        pearl.setdefault("sailNm", sample.get("sailNm"))
        pearl.setdefault("at", {"lat": lat, "lon": lon})
        return pearl

    bags: list[dict] = []
    # Reprise : les perles déjà vues sont dans le cache perles ; on les relit
    # pour reconstruire les diffs, sans rappeler le sac.
    for sample in samples[:done]:
        pearl = _pearl(sample)
        if pearl is not None:
            bags.append(pearl)

    end = done
    while end < len(samples):
        sample = samples[end]
        sail = float(sample.get("sailNm") or 0)
        if end > done and sail > limit_nm:
            break
        if end > done and time.monotonic() >= deadline:
            break
        pearl = _pearl(sample)
        if pearl is None:
            skipped += 1
        else:
            bags.append(pearl)
        end += 1

    clock = _clock_for(voyage) or {}
    voy = {
        **voyage,
        "clock": clock,
        "pearls": bags,
    }
    vid = str(voyage.get("voyageId") or "custom")
    try:
        rows = rows_from_voyage(vid, voy)
    except Exception as exc:
        log.warning("moments perso : %s", exc)
        rows = []

    coverage = float(samples[end - 1]["sailNm"]) if end else 0.0
    ready = end >= len(samples)
    entry.update({
        "status": "ready" if ready else "preparing",
        "moments": rows,
        "coverageNm": coverage if not ready else total_nm,
        "totalNm": total_nm,
        "fingerprint": entry.get("fingerprint") or voyage_fingerprint(voyage),
        "computedAt": _now_iso(),
        "skipped": skipped,
        "skippedKeys": sorted(skipped_keys),
        "done": end,
        "voyageId": voyage.get("voyageId"),
    })
    return entry


def moments_for_voyage(
    voyage: dict,
    *,
    budget_nm: float = DEFAULT_BUDGET_NM,
    bag_fn: Optional[Callable[[float, float], Any]] = None,
) -> dict:
    """Calcule (ou relit) les moments du voyage perso. Jamais 500, jamais de LLM."""
    if not isinstance(voyage, dict):
        return preparing_payload(None, reason="voyage absent")
    fp = voyage_fingerprint(voyage)
    cached = _load_entry(fp)
    if cached and cached.get("status") == "ready":
        return _public(cached)

    if not _COMPUTE_LOCK.acquire(blocking=False):
        if cached:
            body = _public(cached)
            body["status"] = "preparing"
            return body
        return preparing_payload(voyage, fingerprint=fp)

    try:
        cached = _load_entry(fp)
        if cached and cached.get("status") == "ready":
            return _public(cached)
        samples = sample_route_nm(voyage.get("points") or [])
        entry = cached or {
            "status": "preparing",
            "moments": [],
            "coverageNm": 0.0,
            "totalNm": float(samples[-1]["sailNm"]) if samples else 0.0,
            "fingerprint": fp,
            "computedAt": _now_iso(),
            "skipped": 0,
            "skippedKeys": [],
            "done": 0,
            "voyageId": voyage.get("voyageId"),
        }
        if not samples:
            entry.update({
                "status": "ready",
                "coverageNm": 0.0,
                "totalNm": 0.0,
                "computedAt": _now_iso(),
            })
            _save_entry(fp, voyage.get("voyageId"), entry)
            return _public(entry)
        entry = _advance(voyage, samples, entry, budget_nm=budget_nm, bag_fn=bag_fn)
        _save_entry(fp, voyage.get("voyageId"), entry)
        return _public(entry)
    except Exception as exc:
        log.warning("moments_for_voyage : %s", exc)
        return preparing_payload(voyage, fingerprint=fp, reason=str(exc))
    finally:
        _COMPUTE_LOCK.release()
