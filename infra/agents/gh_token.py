#!/usr/bin/env python3
"""Un jeton GitHub qui MARCHE, quel que soit le shell.

Le Mac du porteur a deux magasins d'identifiants git (`osxkeychain` dans la config
système, `store` = ~/.git-credentials dans ~/.gitconfig) : selon le Terminal, `git
credential fill` renvoie l'un ou l'autre — et le fichier peut contenir un vieux jeton
(HTTP 401 le 21 sept.). Ici on rassemble les candidats (GITHUB_TOKEN, trousseau,
fichier, `git credential fill` par défaut), on **essaie** chacun sur l'API, on garde
le premier qui répond 200 et on dit lequel est périmé.

    from gh_token import token
    tok = token()            # str, ou sys.exit avec un message clair
    tok = token(required=False)   # None si aucun (lecture anonyme possible)

Usage en ligne de commande : python3 infra/agents/gh_token.py   (diagnostic, valeurs masquées)
"""
from __future__ import annotations

import os
import subprocess
import sys
import urllib.error
import urllib.request

REPO = os.environ.get("BIM_REPO", "Berry-Mappemonde/Blue-Intelligence")
_CACHE: dict[str, str | None] = {}


def _fill(*helper_args: str) -> str:
    try:
        p = subprocess.run(["git", *helper_args, "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                           text=True, capture_output=True, timeout=20, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except Exception:
        return ""
    for line in p.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    return ""


def candidates() -> list[tuple[str, str]]:
    """[(origine, jeton)] dédoublonnés, dans l'ordre d'essai."""
    out: list[tuple[str, str]] = []
    env = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if env:
        out.append(("GITHUB_TOKEN (variable d'environnement)", env.strip()))
    out.append(("trousseau macOS (osxkeychain)", _fill("-c", "credential.helper=", "-c", "credential.helper=osxkeychain")))
    out.append(("fichier ~/.git-credentials (store)", _fill("-c", "credential.helper=", "-c", "credential.helper=store")))
    out.append(("git credential fill (par défaut)", _fill()))
    seen: set[str] = set()
    uniq = []
    for src, tok in out:
        if tok and tok not in seen:
            seen.add(tok)
            uniq.append((src, tok))
    return uniq


def probe(tok: str) -> int:
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}",
                                 headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
                                          "User-Agent": "bim-gh-token", "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def token(*, required: bool = True, quiet: bool = False) -> str | None:
    if "tok" in _CACHE:
        return _CACHE["tok"]
    stale: list[str] = []
    for src, tok in candidates():
        code = probe(tok)
        if code == 200:
            if stale and not quiet:
                print("gh_token : jeton périmé ignoré — " + " ; ".join(stale) + " (à nettoyer : la ligne github.com de ~/.git-credentials, ou `unset GITHUB_TOKEN`).", file=sys.stderr)
            _CACHE["tok"] = tok
            return tok
        stale.append(f"{src} → HTTP {code}")
    _CACHE["tok"] = None
    if required:
        sys.exit("Aucun jeton GitHub valide. Essayés : " + ("; ".join(stale) or "aucun candidat") +
                 ". Poser un jeton : `gh auth login`, ou GITHUB_TOKEN=… , ou `git credential approve` dans le trousseau.")
    return None


def main() -> None:
    print(f"dépôt sondé : {REPO}")
    for src, tok in candidates():
        print(f"  {src:42} {tok[:4]}…{tok[-3:]} ({len(tok)} car.) → HTTP {probe(tok)}")
    ok = token(required=False, quiet=True)
    print("résultat :", "un jeton valide est disponible" if ok else "AUCUN jeton valide")


if __name__ == "__main__":
    main()
