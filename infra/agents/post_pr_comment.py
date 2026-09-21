#!/usr/bin/env python3
"""Poste un commentaire sur une PR (sans `gh`). Sert au réviseur de nuit (review_agent.py).

Usage :
    python3 infra/agents/post_pr_comment.py <numéro> <fichier.md>
    echo "KO : …" | python3 infra/agents/post_pr_comment.py <numéro> -

Jeton : GITHUB_TOKEN ou trousseau git. Ne ferme, ne merge, ne modifie rien d'autre.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request

REPO = os.environ.get("BIM_REPO", "Berry-Mappemonde/Blue-Intelligence")


def token() -> str:
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    p = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", text=True, capture_output=True, check=True)
    for line in p.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    sys.exit("Aucun jeton GitHub (GITHUB_TOKEN ou trousseau git).")


def post(number: int, body: str) -> str:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/issues/{number}/comments",
        data=json.dumps({"body": body}).encode(), method="POST",
        headers={"Authorization": f"Bearer {token()}", "Accept": "application/vnd.github+json", "User-Agent": "bim-post-comment",
                 "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode()).get("html_url", "")


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    number = int(sys.argv[1])
    body = sys.stdin.read() if sys.argv[2] == "-" else open(sys.argv[2], encoding="utf-8").read()
    if not body.strip():
        sys.exit("commentaire vide")
    print(post(number, body))


if __name__ == "__main__":
    main()
