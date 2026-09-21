#!/usr/bin/env python3
"""Ouvre une PR sur Berry-Mappemonde/Blue-Intelligence sans `gh`.

Usage :
    python3 infra/agents/open_pr.py <branche> <base> "<titre>" <fichier-corps.md>
    python3 infra/agents/open_pr.py --retrofit 250 251      # ajoute les cases à cocher aux PR existantes

Le jeton GitHub vient de GITHUB_TOKEN ou du trousseau git (`git credential fill`).
Sert aux agents locaux (mode --runtime local de run_lots.py) : le prompt leur
dit d'appeler ce script une fois la branche poussée. Ne merge jamais.

Lot W1 : la rubrique « Recette » du corps devient une liste de cases à cocher
GitHub (`- [ ] …`) — le porteur coche ce qu'il a vu et qui est bon, laisse vide
ce qui ne l'est pas et écrit un commentaire « KO : écran, ce que je vois, ce que
je voulais ». `review_collect.py` lit ces cases et ces commentaires.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

REPO = os.environ.get("BIM_REPO", "Berry-Mappemonde/Blue-Intelligence")

HEADING_RE = re.compile(r"^\s{0,3}(#{2,4})\s+(.+?)\s*$")
BULLET_RE = re.compile(r"^(\s*)(?:[-*•]|\d+[.)])\s+(.+?)\s*$")
CHECK_RE = re.compile(r"^\s*[-*]\s*\[( |x|X)\]\s")
RECETTE_TITLES = ("recette", "recipe", "acceptance", "what to check")
NOT_A_STEP_RE = re.compile(r"(?i)^\**\s*(captures?|écran|screen|langue|language)\s*\**\s*:")


def token() -> str:
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    p = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", text=True, capture_output=True, check=True)
    for line in p.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    sys.exit("Aucun jeton GitHub (GITHUB_TOKEN ou trousseau git).")


def checkboxify(body: str) -> str:
    """Dans les rubriques « Recette », chaque étape (puce ou numéro) devient `- [ ] étape`.
    Les lignes de captures / d'écran et les cases déjà présentes sont laissées telles quelles."""
    out: list[str] = []
    in_recette = False
    in_fence = False
    for line in (body or "").splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        m = HEADING_RE.match(line)
        if m and not in_fence:
            in_recette = any(m.group(2).strip().lower().startswith(t) for t in RECETTE_TITLES)
            out.append(line)
            continue
        if in_recette and not in_fence and not CHECK_RE.match(line):
            b = BULLET_RE.match(line)
            if b and "docs/recette/" not in line and not NOT_A_STEP_RE.match(b.group(2)):
                out.append(f"{b.group(1)}- [ ] {b.group(2)}")
                continue
        out.append(line)
    return "\n".join(out) + ("\n" if body.endswith("\n") else "")


def _headers() -> dict:
    return {"Authorization": f"Bearer {token()}", "Accept": "application/vnd.github+json", "User-Agent": "bim-open-pr",
            "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"}


def _call(path: str, method: str = "GET", data: dict | None = None):
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}{path}",
                                 data=json.dumps(data).encode() if data is not None else None, method=method, headers=_headers())
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def warn_if_not_bilingual(body: str) -> None:
    """PR bilingues FR / EN (règle du 21 sept.) : on avertit, on ne bloque pas."""
    low = (body or "").lower()
    if not re.search(r"\b(objective|what changes|acceptance|recipe|out of scope|english)\b", low):
        print("AVERTISSEMENT : le corps de la PR ne semble pas contenir de version anglaise (règle : chaque rubrique FR puis EN).", file=sys.stderr)


def retrofit(numbers: list[int]) -> None:
    for n in numbers:
        pr = _call(f"/pulls/{n}")
        body = pr.get("body") or ""
        new = checkboxify(body)
        if new == body:
            print(f"PR {n} : déjà à jour")
            continue
        _call(f"/pulls/{n}", "PATCH", {"body": new})
        boxes = len(re.findall(r"^\s*- \[ \]", new, re.M))
        print(f"PR {n} : {boxes} cases à cocher ajoutées — {pr.get('html_url')}")


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "--retrofit":
        retrofit([int(x) for x in sys.argv[2:]])
        return
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    head, base, title, body_file = sys.argv[1:5]
    body = checkboxify(open(body_file, encoding="utf-8").read())
    warn_if_not_bilingual(body)
    # PR déjà ouverte pour cette branche ? On la met à jour au lieu d'échouer.
    org = REPO.split("/")[0]
    existing = _call(f"/pulls?head={org}:{head}&state=open")
    if existing:
        pr = existing[0]
        d = _call(f"/pulls/{pr['number']}", "PATCH", {"title": title, "body": body})
        print("PR", d["number"], d["html_url"], "(mise à jour)")
        return
    try:
        d = _call("/pulls", "POST", {"title": title, "head": head, "base": base, "body": body})
        print("PR", d["number"], d["html_url"])
    except urllib.error.HTTPError as e:
        print("ERR", e.code, e.read().decode()[:500])
        sys.exit(1)


if __name__ == "__main__":
    main()
