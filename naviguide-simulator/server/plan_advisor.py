"""Conseil par décalage de date (lot R10b, contrat PLAN_ICI § 3.1–3.2).

Candidats d ∈ {−21, −14, −7, 0, +7, +14, +21} sur le départ de la jambe,
propagés aux escales suivantes (jours à quai conservés). Score = Σ weight
des alertes + 0,3 × |d| + 0,02 × extraNm — constantes fixes, exposées
dans la réponse (info-bulle R10d). Corridor / extraNm : R10c.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from plan_alerts import (
    _as_day,
    _as_dt,
    _f,
    _leg_points,
    _ready_plan,
    evaluate_plan,
    haversine_nm,
    plan_from_voyage,
)
from plan_review import PLANNED_KNOTS
from voyage_clock import to_iso

log = logging.getLogger("naviguide-simulator.plan-advisor")

SHIFT_DAYS = (-21, -14, -7, 0, 7, 14, 21)
WEIGHT_SHIFT_PER_DAY = 0.3
WEIGHT_EXTRA_NM = 0.02
WEIGHTS = {"shiftPerDay": WEIGHT_SHIFT_PER_DAY, "extraNm": WEIGHT_EXTRA_NM}
CORRIDOR_REFERENCE = "reference"
MONTHS_FR = (
    "", "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)

_JOBS: dict[str, dict] = {}
_JOB_LOCK = threading.Lock()
_JOB_THREADS: dict[str, threading.Thread] = {}


def clear_advice_jobs() -> None:
    with _JOB_LOCK:
        _JOBS.clear()
        _JOB_THREADS.clear()


def prepare_plan(plan: dict, *, now: Any = None) -> dict:
    if not isinstance(plan, dict):
        return {"legs": [], "skipper_thresholds": {}}
    if _ready_plan(plan):
        return plan
    if plan.get("clock") or plan.get("voyageId") or plan.get("pearls"):
        return plan_from_voyage(plan, now=now, thresholds=plan.get("skipper_thresholds"))
    return plan


def _now_dt(raw: Any) -> datetime:
    return raw if isinstance(raw, datetime) else _as_dt(raw or datetime.now(timezone.utc))


def _arrive_dt(leg: dict) -> datetime:
    raw = leg.get("arriveIso") or leg.get("arrive")
    if raw:
        return _as_dt(raw)
    depart = _as_dt(leg.get("departIso") or leg.get("depart"))
    kn = _f(leg.get("kn") or leg.get("plannedKnots")) or PLANNED_KNOTS
    kn = kn if kn > 0 else PLANNED_KNOTS
    pts = [p for p in _leg_points(leg) if p.get("lat") is not None and p.get("lon") is not None]
    nm = 0.0
    if pts:
        last, first = pts[-1], pts[0]
        if last.get("sailNm") is not None:
            nm = max(0.0, float(last["sailNm"]) - float(first.get("sailNm") or 0))
        else:
            for i in range(1, len(pts)):
                nm += haversine_nm(
                    float(pts[i - 1]["lat"]), float(pts[i - 1]["lon"]),
                    float(pts[i]["lat"]), float(pts[i]["lon"]),
                )
    return depart + timedelta(hours=nm / kn)


def _is_frozen(leg: dict, now: datetime) -> bool:
    return _arrive_dt(leg) <= now


def shift_plan(plan: dict, leg_idx: int, days: int) -> dict:
    """Décale le départ de `leg_idx` et toutes les jambes suivantes ; holdDays inchangé."""
    out = copy.deepcopy(plan)
    delta = timedelta(days=int(days))
    for i, leg in enumerate(out.get("legs") or []):
        if i < leg_idx:
            continue
        dep = _as_dt(leg.get("departIso") or leg.get("depart"))
        arr = _arrive_dt(leg)
        new_dep, new_arr = dep + delta, arr + delta
        leg["depart"] = new_dep.strftime("%Y-%m-%d")
        leg["arrive"] = new_arr.strftime("%Y-%m-%d")
        leg["departIso"] = to_iso(new_dep)
        leg["arriveIso"] = to_iso(new_arr)
    return out


def cascade_stops(base: dict, shifted: dict, leg_idx: int) -> list[dict]:
    out = []
    for i, (was, now) in enumerate(zip(base.get("legs") or [], shifted.get("legs") or [])):
        if i < leg_idx:
            continue
        out.append({
            "stop": now.get("to"),
            "was": _as_day(was.get("arriveIso") or was.get("arrive") or _arrive_dt(was)),
            "now": _as_day(now.get("arriveIso") or now.get("arrive") or _arrive_dt(now)),
        })
    return out


def score_of(total_weight: float, days: int, extra_nm: float) -> float:
    return float(total_weight) + WEIGHT_SHIFT_PER_DAY * abs(int(days)) + WEIGHT_EXTRA_NM * float(extra_nm)


def _day_fr(iso: str) -> str:
    d = date.fromisoformat(str(iso)[:10])
    label = "1er" if d.day == 1 else str(d.day)
    return f"{label} {MONTHS_FR[d.month]}"


def _parts(iso: str) -> tuple[int, int, int]:
    d = date.fromisoformat(str(iso)[:10])
    return d.day, d.month, d.year


def advice_facts(
    *,
    frm: str,
    to: str,
    days: int,
    depart_was: str,
    depart_now: str,
    alerts_before: int,
    alerts_after: int,
    total_before: int,
    total_after: int,
    extra_nm: float,
    cascade: list[dict],
) -> list[str]:
    """Faits textuels : chaque nombre de la phrase gabarit y figure."""
    was_d, was_m, was_y = _parts(depart_was)
    now_d, now_m, now_y = _parts(depart_now)
    facts = [
        f"jambe {frm} → {to}",
        f"décalage {int(days)} jours (absolu {abs(int(days))})",
        f"départ {depart_was} → {depart_now}",
        f"jour {was_d} → {now_d}",
        f"mois {was_m} → {now_m}",
        f"année {was_y} → {now_y}",
        f"alertes {int(alerts_before)} → {int(alerts_after)}",
        f"total {int(total_before)} → {int(total_after)}",
        f"extraNm {int(round(float(extra_nm)))}",
        f"poids {WEIGHT_SHIFT_PER_DAY} par jour, {WEIGHT_EXTRA_NM} par nm",
    ]
    for row in cascade:
        facts.append(f"{row.get('stop')} {row.get('was')} → {row.get('now')}")
    return facts


def advice_sentence(
    *,
    frm: str,
    days: int,
    depart_was: str,
    depart_now: str,
    alerts_before: int,
    alerts_after: int,
    extra_nm: float,
) -> str:
    """Phrase gabarit : jambe, décalage, alertes avant/après, cascade. Nombres ⊂ facts."""
    if int(days) == 0:
        head = f"Rester au départ de {frm} le {_day_fr(depart_was)}"
    else:
        head = f"Partir de {frm} le {_day_fr(depart_now)} plutôt que le {_day_fr(depart_was)}"
    if int(alerts_before) == int(alerts_after):
        mid = f"{int(alerts_after)} alertes sur cette jambe"
    else:
        mid = f"{int(alerts_after)} alertes au lieu de {int(alerts_before)} sur cette jambe"
    extra = int(round(float(extra_nm)))
    if extra:
        mid += f" (+{extra} nm)"
    abs_d = abs(int(days))
    if int(days) > 0:
        tail = f"toutes les escales suivantes reculent de {abs_d} jours"
    elif int(days) < 0:
        tail = f"toutes les escales suivantes avancent de {abs_d} jours"
    else:
        tail = "aucun décalage des escales suivantes"
    return f"{head} : {mid} ; {tail}."


def _leg_alert_count(evaluated: dict, idx: int) -> int:
    for leg in evaluated.get("legs") or []:
        if int(leg.get("idx") if leg.get("idx") is not None else -1) == idx:
            return len(leg.get("alerts") or [])
    if 0 <= idx < len(evaluated.get("legs") or []):
        return len(evaluated["legs"][idx].get("alerts") or [])
    return 0


def _pack_candidate(
    *,
    src: dict,
    shifted: dict,
    evaluated: dict,
    baseline: dict,
    leg_idx: int,
    days: int,
    extra_nm: float,
) -> dict:
    legs = src.get("legs") or []
    chosen = legs[leg_idx]
    frm, to = chosen.get("from"), chosen.get("to")
    depart_was = _as_day(chosen.get("departIso") or chosen.get("depart"))
    shifted_leg = (shifted.get("legs") or [])[leg_idx]
    depart_now = _as_day(shifted_leg.get("departIso") or shifted_leg.get("depart"))
    alerts_before = _leg_alert_count(baseline, leg_idx)
    alerts_after = _leg_alert_count(evaluated, leg_idx)
    total_before = int(baseline.get("total") or 0)
    total_after = int(evaluated.get("total") or 0)
    cascade = cascade_stops(src, shifted, leg_idx)
    facts = advice_facts(
        frm=frm, to=to, days=days, depart_was=depart_was, depart_now=depart_now,
        alerts_before=alerts_before, alerts_after=alerts_after,
        total_before=total_before, total_after=total_after,
        extra_nm=extra_nm, cascade=cascade,
    )
    sentence = advice_sentence(
        frm=frm, days=days, depart_was=depart_was, depart_now=depart_now,
        alerts_before=alerts_before, alerts_after=alerts_after, extra_nm=extra_nm,
    )
    return {
        "shiftDays": int(days),
        "corridor": CORRIDOR_REFERENCE,
        "extraNm": int(round(float(extra_nm))),
        "alertsBefore": alerts_before,
        "alertsAfter": alerts_after,
        "totalBefore": total_before,
        "totalAfter": total_after,
        "score": score_of(total_after, days, extra_nm),
        "cascade": cascade,
        "facts": facts,
        "sentence": sentence,
        "sentenceSource": "rules",
    }


def advise(plan: dict, leg_idx: int, *, now: Any = None, climatology: dict | None = None) -> dict:
    """Meilleur décalage + 3 alternatives. Déterministe, sans LLM."""
    src = prepare_plan(plan, now=now)
    legs = src.get("legs") or []
    if not (0 <= int(leg_idx) < len(legs)):
        raise ValueError(f"jambe {leg_idx} absente ({len(legs)} jambes)")
    now_dt = _now_dt(now)
    shifts = (0,) if _is_frozen(legs[int(leg_idx)], now_dt) else SHIFT_DAYS
    extra_nm = 0.0
    baseline = evaluate_plan(src, now=now_dt, climatology=climatology)
    packed = []
    for days in shifts:
        shifted = src if days == 0 else shift_plan(src, int(leg_idx), days)
        evaluated = baseline if days == 0 else evaluate_plan(shifted, now=now_dt, climatology=climatology)
        packed.append(_pack_candidate(
            src=src, shifted=shifted, evaluated=evaluated, baseline=baseline,
            leg_idx=int(leg_idx), days=int(days), extra_nm=extra_nm,
        ))
    packed.sort(key=lambda c: (c["score"], abs(c["shiftDays"]), c["extraNm"], c["shiftDays"]))
    best = packed[0]
    alternatives = packed[1:4]
    return {
        "leg": int(leg_idx),
        "weights": dict(WEIGHTS),
        "best": best,
        "alternatives": alternatives,
    }


def _job_key(plan: dict, leg_idx: int, now: datetime) -> str:
    src = prepare_plan(plan, now=now)
    legs = []
    for leg in src.get("legs") or []:
        pts = [
            [round(float(p["lat"]), 3), round(float(p["lon"]), 3)]
            for p in _leg_points(leg) if p.get("lat") is not None and p.get("lon") is not None
        ]
        legs.append({
            "from": leg.get("from"), "to": leg.get("to"),
            "depart": _as_day(leg.get("departIso") or leg.get("depart")),
            "holdDays": leg.get("holdDays"), "points": pts,
        })
    payload = {"legs": legs, "leg": int(leg_idx), "now": now.strftime("%Y-%m-%d")}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def request_advice(
    plan: dict,
    leg_idx: int,
    *,
    now: Any = None,
    climatology: dict | None = None,
    rewrite: Callable[[dict], dict] | None = None,
) -> dict:
    """Réponse immédiate : `{status: pending}` ou le conseil `done` (tâche de fond)."""
    src = prepare_plan(plan, now=now)
    if not (0 <= int(leg_idx) < len(src.get("legs") or [])):
        raise ValueError(f"jambe {leg_idx} absente ({len(src.get('legs') or [])} jambes)")
    now_dt = _now_dt(now)
    key = _job_key(src, int(leg_idx), now_dt)
    with _JOB_LOCK:
        hit = _JOBS.get(key)
        if hit and hit.get("status") == "done":
            return copy.deepcopy(hit)
        running = _JOB_THREADS.get(key)
        if hit and hit.get("status") == "pending" and running and running.is_alive():
            return {"status": "pending", "leg": int(leg_idx), "weights": dict(WEIGHTS)}
        _JOBS[key] = {"status": "pending", "leg": int(leg_idx), "weights": dict(WEIGHTS)}

        def _run() -> None:
            try:
                out = advise(src, int(leg_idx), now=now_dt, climatology=climatology)
                if rewrite:
                    out = rewrite(out)
                out["status"] = "done"
            except Exception as exc:
                log.warning("conseil dates : %s", exc)
                try:
                    out = advise(src, int(leg_idx), now=now_dt, climatology=climatology)
                    out["status"] = "done"
                except Exception as exc2:
                    out = {"status": "done", "leg": int(leg_idx), "weights": dict(WEIGHTS), "error": str(exc2)}
            with _JOB_LOCK:
                _JOBS[key] = out

        thread = threading.Thread(target=_run, name=f"plan-advice-{leg_idx}", daemon=True)
        _JOB_THREADS[key] = thread
        thread.start()
    return {"status": "pending", "leg": int(leg_idx), "weights": dict(WEIGHTS)}
