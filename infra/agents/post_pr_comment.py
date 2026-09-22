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
    """Jeton éprouvé sur l'API (gh_token.py) : trousseau, fichier ou variable, le premier qui répond 200."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gh_token import token as _token  # noqa: PLC0415
    return _token()


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
