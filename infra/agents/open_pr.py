#!/usr/bin/env python3
"""Ouvre une PR sur Berry-Mappemonde/Blue-Intelligence sans `gh`.

Usage :
    python3 infra/agents/open_pr.py <branche> <base> "<titre>" <fichier-corps.md>

Le jeton GitHub vient de GITHUB_TOKEN ou du trousseau git (`git credential fill`).
Sert aux agents locaux (mode --runtime local de run_lots.py) : le prompt leur
dit d'appeler ce script une fois la branche poussée. Ne merge jamais.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "Berry-Mappemonde/Blue-Intelligence"


def token() -> str:
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    p = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", text=True, capture_output=True, check=True)
    for line in p.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    sys.exit("Aucun jeton GitHub (GITHUB_TOKEN ou trousseau git).")


def main() -> None:
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    head, base, title, body_file = sys.argv[1:5]
    body = open(body_file, encoding="utf-8").read()
    headers = {"Authorization": f"Bearer {token()}", "Accept": "application/vnd.github+json", "User-Agent": "bim-open-pr",
               "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"}
    # PR déjà ouverte pour cette branche ? On la met à jour au lieu d'échouer.
    org = REPO.split("/")[0]
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/pulls?head={org}:{head}&state=open", headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        existing = json.loads(resp.read().decode())
    if existing:
        pr = existing[0]
        req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/pulls/{pr['number']}", data=json.dumps({"title": title, "body": body}).encode(), method="PATCH", headers=headers)
        with urllib.request.urlopen(req, timeout=45) as resp:
            d = json.loads(resp.read().decode())
        print("PR", d["number"], d["html_url"], "(mise à jour)")
        return
    data = {"title": title, "head": head, "base": base, "body": body}
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/pulls", data=json.dumps(data).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            d = json.loads(resp.read().decode())
            print("PR", d["number"], d["html_url"])
    except urllib.error.HTTPError as e:
        print("ERR", e.code, e.read().decode()[:500])
        sys.exit(1)


if __name__ == "__main__":
    main()
