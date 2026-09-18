#!/usr/bin/env python3
"""Exit 0 if the hook payload asks to open the local simulator."""
import json
import re
import sys


def walk(obj):
    if isinstance(obj, dict):
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)
    elif isinstance(obj, str):
        yield obj


def asks_open(data: dict) -> bool:
    chunks = [str(data.get(key) or "") for key in ("prompt", "text", "user_prompt", "content", "message")]
    chunks.extend(walk(data))
    text = " ".join(chunks)
    if not text.strip():
        return False
    norm = re.sub(r"\s+", " ", text.lower())
    patterns = (
        r"(ouvre|réouvre|reouvre|affiche|montre|voir|preview|open|ouverte).{0,80}"
        r"(appli|application|simulateur|naviguide|navigateur|preview|en local|localhost|5174)",
        r"(appli|application|simulateur|naviguide).{0,60}"
        r"(local|navigateur|preview|localhost|5174|ouverte)",
        r"affiche en local",
        r"montre[- ]moi",
        r"(ré)?ouvre l['’ ]*(appli|application|simulateur|navigateur|preview)",
        r"open (the )?(app|simulator|browser|preview)",
        r"localhost:5174",
        r"ne s['’ ]*ouvre",
        r"s['’ ]*ouvre.{0,30}pas",
        r"pas ouverte",
        r"(appli|application|simulateur|naviguide).{0,40}(toujours pas|pas ouverte)",
    )
    return any(re.search(pattern, norm) for pattern in patterns)


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 1
    return 0 if asks_open(data) else 1


if __name__ == "__main__":
    raise SystemExit(main())
