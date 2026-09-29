#!/usr/bin/env python3
"""Part du code écrite ou modifiée depuis le début du hackathon (porteur, 29 sept.) — pour la case Devpost
« existing project : how significantly was it updated since <date> ».

Deux mesures, toutes deux depuis `git` (rien d'estimé) :
  1. **part vivante** : parmi les lignes de code du dépôt AUJOURD'HUI, celles dont le dernier commit (git blame)
     est postérieur à la date — « X % du code actuel a été écrit ou réécrit depuis le … » ;
  2. **brassage** : lignes ajoutées + supprimées depuis la date (git log --numstat), rapportées au code actuel.

Périmètre : fichiers de code suivis (.py .js .jsx .ts .tsx .mjs .css .html .yml .yaml .sh), hors Archives/,
node_modules, dist, seed, .geojson, lockfiles, minifiés. Sous-totaux : simulateur, backend BI, frontend BI, infra.

    python3 infra/agents/devpost_code_share.py                 # depuis le 2026-08-26 (date du formulaire Devpost)
    python3 infra/agents/devpost_code_share.py --since 2026-08-24 --json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE_RE = re.compile(r"\.(py|js|jsx|ts|tsx|mjs|css|html|yml|yaml|sh)$")
EXCLUDE_RE = re.compile(r"(^Archives/|(^|/)node_modules/|(^|/)dist/|(^|/)seed/|\.geojson$|package-lock|\.min\.|(^|/)\.venv/)")


def sh(args: list[str]) -> str:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False).stdout


def area(path: str) -> str:
    if path.startswith("naviguide-simulator/"):
        return "simulateur"
    if path.startswith("backend/"):
        return "backend BI"
    if path.startswith("frontend/"):
        return "frontend BI"
    if path.startswith("infra/") or path.startswith(".github/") or path.startswith("scripts/"):
        return "infra / CI / agents"
    return "autre"


def code_files() -> list[str]:
    return [f for f in sh(["git", "ls-files"]).splitlines() if CODE_RE.search(f) and not EXCLUDE_RE.search(f)]


def blame_share(files: list[str], since_ts: int) -> tuple[dict[str, list[int]], int, int]:
    """Par zone : [lignes totales, lignes datées après `since`]."""
    per = defaultdict(lambda: [0, 0])
    total = recent = 0
    for f in files:
        out = sh(["git", "blame", "--line-porcelain", "-w", "--", f])
        if not out:
            continue
        for m in re.finditer(r"^committer-time (\d+)$", out, re.M):
            n_recent = int(m.group(1)) >= since_ts
            per[area(f)][0] += 1
            per[area(f)][1] += int(n_recent)
            total += 1
            recent += int(n_recent)
    return per, total, recent


def churn(since: str) -> tuple[int, int, int, int]:
    """(ajoutées, supprimées, fichiers touchés, commits) depuis `since`, même périmètre."""
    out = sh(["git", "log", f"--since={since}", "--numstat", "--format=%h"])
    added = deleted = 0
    files: set[str] = set()
    commits = 0
    for line in out.splitlines():
        if re.fullmatch(r"[0-9a-f]{7,}", line.strip()):
            commits += 1
            continue
        m = re.match(r"^(\d+|-)\t(\d+|-)\t(.+)$", line)
        if not m:
            continue
        path = m.group(3)
        if "=>" in path:  # renommage : on garde le nom final
            path = re.sub(r"\{.* => (.*)\}", r"\1", path).replace("//", "/")
        if not CODE_RE.search(path) or EXCLUDE_RE.search(path):
            continue
        if m.group(1) != "-":
            added += int(m.group(1)); deleted += int(m.group(2))
        files.add(path)
    return added, deleted, len(files), commits


def snapshot(since: str) -> dict:
    """Le dépôt tel qu'il était au dernier commit AVANT la date : fichiers et lignes de code (même périmètre)."""
    rev = sh(["git", "rev-list", "-1", f"--before={since}", "main"]).strip() or sh(["git", "rev-list", "-1", f"--before={since}", "HEAD"]).strip()
    if not rev:
        return {"rev": None, "codeFiles": 0, "lines": 0, "hadSimulator": False}
    files = [f for f in sh(["git", "ls-tree", "-r", "--name-only", rev]).splitlines() if CODE_RE.search(f) and not EXCLUDE_RE.search(f)]
    lines = 0
    for f in files:
        lines += sh(["git", "show", f"{rev}:{f}"]).count("\n")
    return {"rev": rev[:7], "date": sh(["git", "log", "-1", "--format=%ad", "--date=short", rev]).strip(),
            "codeFiles": len(files), "lines": lines, "hadSimulator": any(f.startswith("naviguide-simulator/") for f in files)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default="2026-08-26", help="date de début du hackathon (formulaire Devpost : August 26, 2026)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    since_ts = int(datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    files = code_files()
    per, total, recent = blame_share(files, since_ts)
    added, deleted, touched, commits = churn(args.since)
    before = snapshot(args.since)
    share = 100.0 * recent / total if total else 0.0
    result = {
        "since": args.since,
        "head": sh(["git", "rev-parse", "--short", "HEAD"]).strip(),
        "before": before,
        "codeFiles": len(files),
        "linesNow": total,
        "linesWrittenOrChangedSince": recent,
        "shareLivePercent": round(share, 1),
        "churn": {"added": added, "deleted": deleted, "filesTouched": touched, "commits": commits,
                  "ratioPercent": round(100.0 * (added + deleted) / total, 1) if total else 0.0},
        "areas": {k: {"linesNow": v[0], "recent": v[1], "sharePercent": round(100.0 * v[1] / v[0], 1) if v[0] else 0.0}
                  for k, v in sorted(per.items())},
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return
    since_en = datetime.strptime(args.since, "%Y-%m-%d").strftime("%B %-d, %Y")
    sim_lines = result["areas"].get("simulateur", {}).get("linesNow", 0)
    result["sentenceEn"] = (
        f"In numbers (from git, code files only): on {since_en} the repository held {before['codeFiles']} code files and "
        f"{before['lines']:,} lines{'' if before['hadSimulator'] else ' — the NAVIGUIDE simulator did not exist'}. Today it holds "
        f"{len(files)} code files and {total:,} lines, and {share:.0f}% of those lines ({recent:,}) were written or rewritten since "
        f"{since_en} — {commits} commits, {touched} files touched."
        + (f" The simulator ({sim_lines:,} lines) is entirely post-{since_en}." if sim_lines and not before["hadSimulator"] else "")
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return
    fr = lambda n: f"{n:,}".replace(",", " ")  # noqa: E731
    print(f"Au {args.since} (commit {before['rev']}, {before.get('date')}) : {before['codeFiles']} fichiers de code, {fr(before['lines'])} lignes"
          f"{'' if before['hadSimulator'] else ' — pas de naviguide-simulator/'}.")
    print(f"Aujourd'hui (HEAD {result['head']}) : {len(files)} fichiers, {fr(total)} lignes.")
    print(f"Depuis le {args.since} : {fr(recent)} de ces lignes ont été écrites ou réécrites → **{share:.1f} %** du code actuel.")
    print(f"Brassage : +{fr(added)} / −{fr(deleted)} lignes, {touched} fichiers touchés, {commits} commits "
          f"({result['churn']['ratioPercent']} % du code actuel en ajouts + suppressions).")
    for k, v in result["areas"].items():
        print(f"  {k:20} {fr(v['linesNow']):>9} lignes, {v['sharePercent']:5.1f} % depuis le {args.since}")
    print("\nPhrase (EN, à coller) : " + result["sentenceEn"])


if __name__ == "__main__":
    sys.exit(main())
