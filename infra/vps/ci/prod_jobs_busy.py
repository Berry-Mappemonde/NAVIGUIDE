#!/usr/bin/env python3
"""Sonde les files d'enrichissement / Complet / lot Review Proposer.

Sortie :
  0  — aucun run en cours (redémarrer blue-intelligence est sûr)
  10 — au moins un run occupe le processus uvicorn
  1  — l'API n'a pas répondu de façon exploitable (sauf connexion refusée :
       traité comme idle, le service est à l'arrêt)

Les GET Console sont publics. Le lot Review Proposer
(``/api/review/suggest/status``) exige ``X-Admin-Key`` en production :
la sonde lit ``ADMIN_KEY`` (env ou ``backend/.env`` sur le VPS).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

BUSY_EXIT = 10
ERROR_EXIT = 1

DEFAULT_BASE = "http://127.0.0.1:8001"
# Cloudflare Bot Fight bloque le UA par défaut de urllib (« Python-urllib/3.x »).
USER_AGENT = "BlueIntelligence-DeployProbe/1.0 (+https://blueintelligence.online)"

# Files Console / enrichissement qui vivent en mémoire dans uvicorn.
PROBE_PATHS = (
    "/api/swarm/status",
    "/api/projects/runs",
    "/api/marinas/build/status",
    "/api/marinas/enrich-batch/status",
    "/api/marinas/maps-place/status",
    "/api/anchorages/build/status",
    "/api/capitaineries/build/status",
    "/api/capitaineries/enrich-batch/status",
    "/api/poe/runs",
    "/api/poe/seeds/enrich/status",
    "/api/poe/seeds/mine-sources/status",
    "/api/poe/referential/status",
    "/api/poe/auto-refresh/status",
    "/api/amp/discover-visit-urls/status",
    "/api/science/build/status",
    "/api/review/suggest/status",
)

# Lectures Review : garde admin (voir app.main._ADMIN_GET_PREFIXES).
ADMIN_PROBE_PATHS = frozenset({"/api/review/suggest/status"})


def _truthy_id(value) -> bool:
    return bool(value) and value != "none"


def payload_reasons(data: dict) -> list[str]:
    """Pourquoi ce JSON indique un run en cours (liste vide = idle)."""
    reasons: list[str] = []
    if not isinstance(data, dict):
        return reasons
    if data.get("running") is True:
        reasons.append("running")
    if data.get("cycle_running") is True:
        reasons.append("cycle_running")
    ids = data.get("active_run_ids")
    if isinstance(ids, list) and any(_truthy_id(x) for x in ids):
        reasons.append("active_run_ids")
    if _truthy_id(data.get("active_run_id")):
        reasons.append("active_run_id")
    live = data.get("live")
    if isinstance(live, dict) and live.get("running") is True:
        reasons.append("live.running")
    run = data.get("run")
    if isinstance(run, dict) and run.get("state") in ("running", "started"):
        reasons.append("run.state")
    task = data.get("task")
    if isinstance(task, dict) and task.get("running") is True:
        reasons.append("task.running")
    return reasons


def needs_admin(path: str) -> bool:
    return path in ADMIN_PROBE_PATHS


def load_admin_key(explicit: str | None = None) -> str:
    """ADMIN_KEY explicite, sinon l'environnement, sinon backend/.env du VPS."""
    if explicit and explicit.strip():
        return explicit.strip()
    env = (os.environ.get("ADMIN_KEY") or "").strip()
    if env:
        return env
    app = os.environ.get("APP") or str(Path.home() / "blue-intelligence-map")
    env_file = Path(app) / "backend" / ".env"
    if not env_file.is_file():
        return ""
    for raw in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("ADMIN_KEY="):
            value = line.split("=", 1)[1].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value.strip()
    return ""


def is_http_unauthorized(exc: BaseException) -> bool:
    return isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403)


def is_http_gone(exc: BaseException) -> bool:
    """404 / 410 : endpoint retiré, on n'en déduit pas un run."""
    if isinstance(exc, urllib.error.HTTPError) and exc.code in (404, 410):
        return True
    return False


def is_connection_refused(exc: BaseException) -> bool:
    if isinstance(exc, ConnectionRefusedError):
        return True
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, ConnectionRefusedError):
            return True
        if isinstance(reason, OSError) and getattr(reason, "errno", None) in (111, 61):
            return True
        text = str(reason).lower()
        if "connection refused" in text:
            return True
    if isinstance(exc, OSError) and exc.errno in (111, 61):
        return True
    return False


def fetch_json(url: str, timeout: float, admin_key: str = "") -> dict:
    headers = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if admin_key:
        headers["X-Admin-Key"] = admin_key
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8") or "{}"
        data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"réponse non-objet: {type(data).__name__}")
    return data


def probe(base_url: str, timeout: float = 12.0,
          admin_key: str = "") -> tuple[int, list[dict]]:
    """Retourne (code_sortie, détail par chemin)."""
    base = base_url.rstrip("/")
    details: list[dict] = []
    busy_hits: list[dict] = []
    for path in PROBE_PATHS:
        url = f"{base}{path}"
        row: dict = {"path": path}
        key = admin_key if needs_admin(path) else ""
        try:
            data = fetch_json(url, timeout, admin_key=key)
        except json.JSONDecodeError as exc:
            return ERROR_EXIT, [{"path": path, "error": f"json: {exc}"}]
        except Exception as exc:
            if is_connection_refused(exc):
                return 0, [{"path": path, "idle": True, "note": "connexion refusée (service arrêté)"}]
            if is_http_gone(exc):
                details.append({"path": path, "skipped": True, "note": str(exc)})
                continue
            if is_http_unauthorized(exc) and needs_admin(path):
                if key:
                    return ERROR_EXIT, [{"path": path, "error": f"{type(exc).__name__}: {exc}"}]
                details.append({
                    "path": path, "skipped": True,
                    "note": "401 Review — ADMIN_KEY absente, lot Proposer invisible",
                })
                continue
            return ERROR_EXIT, [{"path": path, "error": f"{type(exc).__name__}: {exc}"}]
        reasons = payload_reasons(data)
        row["reasons"] = reasons
        if reasons:
            if _truthy_id(data.get("active_run_id")):
                row["active_run_id"] = data.get("active_run_id")
            if isinstance(data.get("active_run_ids"), list):
                row["active_run_ids"] = data.get("active_run_ids")
            busy_hits.append(row)
        details.append(row)
    if busy_hits:
        return BUSY_EXIT, busy_hits
    return 0, details


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE,
        help="Racine de l'API (défaut %(default)s)",
    )
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--json", action="store_true", help="Détail JSON sur stdout")
    parser.add_argument(
        "--admin-key",
        default="",
        help="Clé X-Admin-Key (sinon ADMIN_KEY ou backend/.env)",
    )
    args = parser.parse_args(argv)

    admin_key = load_admin_key(args.admin_key or None)
    code, details = probe(args.base_url, timeout=args.timeout, admin_key=admin_key)
    if args.json:
        json.dump({"exit": code, "base": args.base_url.rstrip("/"), "hits": details},
                  sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    elif code == BUSY_EXIT:
        print("BUSY — run d'enrichissement / Complet / lot Review Proposer en cours :")
        for row in details:
            extra = row.get("active_run_id") or row.get("active_run_ids") or ""
            print(f"  {row['path']}  {','.join(row.get('reasons') or [])}  {extra}".rstrip())
    elif code == ERROR_EXIT:
        err = details[0] if details else {}
        print(f"ERROR — sonde {err.get('path', '?')}: {err.get('error', 'inconnu')}",
              file=sys.stderr)
    else:
        note = ""
        if details and details[0].get("note"):
            note = f" ({details[0]['note']})"
        print(f"IDLE — aucun run en cours{note}")
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(ERROR_EXIT)
