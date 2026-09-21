#!/usr/bin/env python3
"""Décide quels sites déployer (sortie GitHub Actions : clé=valeur)."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ZERO_SHA = "0" * 40

_FALSE = {"bi": "false", "naviguide": "false", "simulator": "false", "catch_up": "false"}


def _flag(ok: bool) -> str:
    return "true" if ok else "false"


def site_for_path(path: str) -> str | None:
    """blue-intelligence | naviguide | simulator | None."""
    path = path.lstrip("./")
    if path.startswith("frontend/") or path.startswith("backend/"):
        return "blue-intelligence"
    if path in (
        "infra/vps/deploy-app.sh",
        "infra/vps/blue-intelligence.service",
        "infra/vps/blue-intelligence-backup.cron",
        "infra/vps/nginx-blue-intelligence.conf",
    ):
        return "blue-intelligence"
    if path.startswith("naviguide-simulator/"):
        return "simulator"
    if path in (
        "infra/vps/nginx-bi-climatology-cache.conf",
        "infra/vps/nginx-snippet-bi-climatology.conf",
    ):
        # Installés par deploy-simulator.sh (cache nginx climatologie BI).
        return "simulator"
    if path.startswith("naviguide/"):
        return "naviguide"
    if path.startswith("infra/vps/naviguide/"):
        name = Path(path).name
        if "simulator" in name:
            return "simulator"
        return "naviguide"
    return None


def classify(files: list[str]) -> dict[str, str]:
    out = dict(_FALSE)
    for path in files:
        site = site_for_path(path)
        if site == "blue-intelligence":
            out["bi"] = "true"
        elif site == "naviguide":
            out["naviguide"] = "true"
        elif site == "simulator":
            out["simulator"] = "true"
    return out


def decide(event_name: str, *, input_site: str | None = None,
           files: list[str] | None = None) -> dict[str, str]:
    event = (event_name or "").strip()
    if event == "schedule":
        out = dict(_FALSE)
        out["catch_up"] = "true"
        return out
    if event == "workflow_dispatch":
        wanted = (input_site or "all").strip() or "all"
        out = dict(_FALSE)
        if wanted == "all":
            out["bi"] = out["naviguide"] = out["simulator"] = "true"
        elif wanted == "blue-intelligence":
            out["bi"] = "true"
        elif wanted == "naviguide":
            out["naviguide"] = "true"
        elif wanted == "simulator":
            out["simulator"] = "true"
        return out
    result = classify(files or [])
    # Un push qui ne touche que la sonde / apply-*.sh : envoyer les scripts
    # sur le VPS sans redémarrer les sites.
    if (result["bi"] == "false" and result["naviguide"] == "false"
            and result["simulator"] == "false"
            and any((p or "").startswith("infra/vps/ci/") for p in (files or []))):
        result["catch_up"] = "true"
    return result


def _changed_files(before: str, sha: str) -> list[str]:
    if not before or before == ZERO_SHA:
        cmd = ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha]
    else:
        cmd = ["git", "diff", "--name-only", before, sha]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr.strip() or "git diff failed", file=sys.stderr)
        # En cas de doute (force-push), on déploie les trois.
        return [
            "frontend/",
            "naviguide/",
            "naviguide-simulator/",
        ]
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default=os.environ.get("EVENT_NAME") or "")
    parser.add_argument("--site", default=os.environ.get("INPUT_SITE") or "")
    parser.add_argument("--before", default=os.environ.get("EVENT_BEFORE") or "")
    parser.add_argument("--sha", default=os.environ.get("GITHUB_SHA") or "")
    args = parser.parse_args(argv)

    files = None
    event = args.event or os.environ.get("GITHUB_EVENT_NAME") or ""
    if event == "push":
        files = _changed_files(args.before, args.sha)
    result = decide(event, input_site=args.site or None, files=files)
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
