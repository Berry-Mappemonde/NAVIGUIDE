#!/usr/bin/env python3
"""Vérifie les liens Markdown relatifs du dépôt. Aucun lien mort = code 0.

Usage (depuis la racine du dépôt) :

    python3 docs/check_md_links.py
    python3 docs/check_md_links.py --http   # sonde aussi les URL http(s)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".dev",
    "Archives",
}

# [text](url) et ![alt](url) — ignore les images de référence seules
LINK_RE = re.compile(r"!?\[([^\]]*)\]\(([^)]+)\)")
# [label]: url
REF_RE = re.compile(r"^\[([^\]]+)\]:\s+(\S+)", re.MULTILINE)

SKIP_URL_PREFIXES = (
    "mailto:",
    "javascript:",
    "#",
)


def should_skip_dir(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def iter_markdown(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        p = Path(dirpath)
        if should_skip_dir(p.relative_to(root) if p != root else Path(".")):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".md"):
                yield p / name


def split_url(raw: str) -> tuple[str, str]:
    url = raw.strip()
    if url.startswith("<") and url.endswith(">"):
        url = url[1:-1].strip()
    # title after space: url "title" or url 'title'
    if " " in url and (url.endswith('"') or url.endswith("'")):
        url = url.split(" ", 1)[0]
    if url.startswith("<") and ">" in url:
        url = url[1 : url.index(">")]
    frag = ""
    if "#" in url and not url.startswith("#"):
        url, frag = url.split("#", 1)
        frag = "#" + frag
    return url, frag


def is_external(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def resolve_relative(md_file: Path, url: str) -> Path:
    if url.startswith("/"):
        return (ROOT / url.lstrip("/")).resolve()
    return (md_file.parent / url).resolve()


def check_http(url: str, timeout: float) -> str | None:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "docs-link-check"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if 200 <= resp.status < 400:
                return None
            return f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        if exc.code in (405, 403):
            get_req = urllib.request.Request(url, headers={"User-Agent": "docs-link-check"})
            try:
                with urllib.request.urlopen(get_req, timeout=timeout) as resp:
                    if 200 <= resp.status < 400:
                        return None
                    return f"HTTP {resp.status}"
            except Exception as exc2:  # noqa: BLE001
                return str(exc2)
        return f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--http", action="store_true", help="sonder les URL http(s)")
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()

    broken: list[str] = []
    checked = 0
    files = 0

    for md in sorted(iter_markdown(ROOT)):
        files += 1
        text = md.read_text(encoding="utf-8")
        found = [(m.group(2), m.start()) for m in LINK_RE.finditer(text)]
        found += [(m.group(2), m.start()) for m in REF_RE.finditer(text)]
        for raw, _ in found:
            url, _frag = split_url(raw)
            if not url or url.startswith(SKIP_URL_PREFIXES):
                continue
            # Artefacts éditeur (Cursor media), hors dépôt.
            if url.startswith("/cursor/"):
                continue
            rel = md.relative_to(ROOT)
            checked += 1
            if is_external(url):
                if not args.http:
                    continue
                err = check_http(url, args.timeout)
                if err:
                    broken.append(f"{rel}: {url}  ({err})")
                continue
            if "://" in url:
                continue
            target = resolve_relative(md, url)
            try:
                target.relative_to(ROOT)
            except ValueError:
                broken.append(f"{rel}: {url}  (sort du dépôt)")
                continue
            if not target.exists():
                broken.append(f"{rel}: {url}  (absent → {target.relative_to(ROOT)})")

    print(f"Fichiers Markdown : {files}")
    print(f"Liens examinés    : {checked}")
    print(f"Liens morts       : {len(broken)}")
    for line in broken:
        print(f"  MORT  {line}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
