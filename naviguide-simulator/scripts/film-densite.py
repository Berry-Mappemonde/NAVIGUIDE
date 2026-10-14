#!/usr/bin/env python3
"""Mesure de densité du récit du film (lot RC26).

Imprime, depuis GET /voyage/official/film et GET /voyage/official/moments :
  - par chapitre : jours de MER (départ → arrivée), caractères, items dits
    (hors escales), plancher jours/1,5 (min 4, plafond 16), part des
    caractères ancrés sur une même minute, plus grand trou sans phrase
    ancrée (en % de la mer) ;
  - pour le film : stations / projets / AMP / climato dits vs stock,
    doublons de site, adjectifs ZEE orphelins (« françaises » sans « eaux »).

Usage :
  python3 scripts/film-densite.py                     # API du poste (127.0.0.1:8010)
  python3 scripts/film-densite.py --api http://127.0.0.1:8011
  python3 scripts/film-densite.py --film f.json --moments m.json [-v]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from urllib.request import Request, urlopen

DAY_MS = 86_400_000
AIR_RE = re.compile(r"s'envole|s’envole|flies (?:from|to)|attend à|awaits", re.I)
# Adjectifs de nationalité des phrases ZEE : orphelins si le mot d'avant n'est
# ni « eaux », ni « les », ni un nom propre (« Samoa américaines »).
NATION_ADJ = (
    "espagnoles", "françaises", "italiennes", "portugaises", "britanniques",
    "américaines", "canadiennes", "brésiliennes", "australiennes",
    "néo-zélandaises", "marocaines", "algériennes", "vénézuéliennes",
    "cubaines", "fidjiennes", "indonésiennes", "indiennes", "mexicaines",
    "colombiennes", "néerlandaises", "irlandaises", "norvégiennes",
    "japonaises", "chinoises", "sud-africaines", "argentines", "chiliennes",
    "sénégalaises", "maltaises", "grecques", "tunisiennes", "mauritaniennes",
    "papouanes", "philippines", "surinamaises", "barbadiennes",
    "grenadiennes", "panaméennes", "costariciennes", "équatoriennes",
    "péruviennes", "tongiennes", "samoanes", "tuvaluanes", "comoriennes",
    "mauriciennes", "malgaches", "mozambicaines", "seychelloises",
    "tanzaniennes", "kényanes", "capverdiennes", "bahaméennes", "haïtiennes",
    "jamaïcaines", "honduriennes", "nicaraguayennes", "dominicaines",
)
ADJ_RE = re.compile(r"\b(" + "|".join(NATION_ADJ) + r")\b", re.I)
SITE_SPLIT_RE = re.compile(r"\s+[-—–]\s+|\s*\(")


def _ms(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
                   .astimezone(timezone.utc).timestamp() * 1000)
    except ValueError:
        return None


def _get(url: str) -> dict:
    with urlopen(Request(url), timeout=30) as resp:
        return json.loads(resp.read().decode())


def departures_from_clock(clock: dict | None) -> dict[str, int]:
    """{nom d'escale: instant d'appareillage} depuis l'horloge officielle."""
    out: dict[str, int] = {}
    for mark in (clock or {}).get("marks") or []:
        t = _ms(mark.get("iso"))
        if t is None:
            continue
        hold = float(mark.get("holdHours") or 0)
        out[str(mark.get("name") or "").strip()] = t + int(hold * 3_600_000)
    return out


def sea_bounds(ch: dict, departs: dict[str, int]) -> tuple[int | None, int | None]:
    """[départ réel, arrivée] : l'escale à quai du début n'est pas un trou."""
    t_a, t_b = _ms(ch.get("tA")), _ms(ch.get("tB"))
    depart = departs.get(str(ch.get("fromName") or "").strip())
    if depart is not None and t_a is not None and t_b is not None and t_a <= depart < t_b:
        return depart, t_b
    return t_a, t_b


def sea_days(ch: dict, departs: dict[str, int]) -> float:
    lo, hi = sea_bounds(ch, departs)
    if lo is None or hi is None or hi <= lo:
        return 0.0
    return (hi - lo) / DAY_MS


def chapter_items(ch: dict) -> list[dict]:
    return [
        e for e in (ch.get("events") or [])
        if str(e.get("kind") or "") != "stop" and not str(e.get("id") or "").startswith("stop:")
    ]


def frozen_minute_blocks(ch: dict) -> list[tuple[int, int, str]]:
    """Caractères FIGÉS : entre deux ancres consécutives sur la même minute, le
    bateau ne bouge pas (entre deux ancres d'instants différents, le film
    interpole et le bateau avance). [(caractères, minute, extrait)] décroissant."""
    text = ch.get("text") or ""
    anchors = sorted(
        [a for a in (ch.get("anchors") or []) if isinstance(a.get("charIdx"), int)],
        key=lambda a: a["charIdx"],
    )
    if not text or len(anchors) < 2:
        return []
    per_minute: dict[int, list[int]] = {}
    for a, b in zip(anchors, anchors[1:]):
        if a["charIdx"] == 0:
            continue  # l'ouverture (deux phrases réglementaires au départ) n'est pas un blocage
        t1, t2 = _ms(a.get("t")), _ms(b.get("t"))
        if t1 is None or t2 is None or (t1 // 60_000) != (t2 // 60_000):
            continue
        row = per_minute.setdefault(t1 // 60_000, [0, a["charIdx"]])
        row[0] += max(0, b["charIdx"] - a["charIdx"])
    out = [
        (chars, minute, text[start:start + 70].strip())
        for minute, (chars, start) in per_minute.items()
    ]
    out.sort(reverse=True)
    return out


def same_minute_share(ch: dict) -> float:
    blocks = frozen_minute_blocks(ch)
    if not blocks:
        return 0.0
    return blocks[0][0] / max(1, len(ch.get("text") or ""))


def max_same_minute_run(ch: dict) -> int:
    """Plus long enchaînement d'ancres consécutives sur la même minute — le
    grief du 29 sept. : « plus de cinq phrases d'affilée sans que le bateau
    bouge »."""
    anchors = sorted(
        [a for a in (ch.get("anchors") or []) if isinstance(a.get("charIdx"), int)],
        key=lambda a: a["charIdx"],
    )
    best = run = 0
    prev_minute = None
    for a in anchors:
        t = _ms(a.get("t"))
        minute = (t // 60_000) if t is not None else None
        if minute is not None and minute == prev_minute:
            run += 1
        else:
            run = 1 if minute is not None else 0
        prev_minute = minute
        best = max(best, run)
    return best


def max_gap(ch: dict, departs: dict[str, int]) -> tuple[float, int | None, int | None]:
    """(part de la mer, début, fin) du plus grand trou entre phrases ancrées."""
    lo, hi = sea_bounds(ch, departs)
    if lo is None or hi is None or hi <= lo:
        return 0.0, None, None
    times = sorted(
        t for t in (_ms(a.get("t")) for a in ch.get("anchors") or [])
        if t is not None and t >= lo
    )
    marks = [lo, *times, hi]
    worst, w_a, w_b = 0, None, None
    for a, b in zip(marks, marks[1:]):
        if b - a > worst:
            worst, w_a, w_b = b - a, a, b
    return worst / (hi - lo), w_a, w_b


def orphan_zee_adjectives(text: str) -> list[str]:
    out = []
    for m in ADJ_RE.finditer(text):
        before = text[:m.start()].rstrip()
        prev = re.findall(r"[A-Za-zÀ-ÿ’'-]+", before[-30:])
        prev_word = prev[-1] if prev else ""
        if prev_word in {"eaux", "les"} or (prev_word[:1].isupper() and prev_word != ""):
            continue
        out.append(m.group(1))
    return out


def site_key(kind: str, name: str) -> str:
    s = re.sub(r"\s+", " ", str(name or "")).strip().casefold()
    if kind == "zee":
        return f"zee:{s}"
    return SITE_SPLIT_RE.split(s, maxsplit=1)[0].strip()


def duplicate_sites(chapters: list[dict]) -> list[str]:
    dups = []
    for ch in chapters:
        seen: Counter = Counter()
        for e in chapter_items(ch):
            key = site_key(str(e.get("kind") or ""), e.get("title") or "")
            if key:
                seen[key] += 1
        dups.extend(k for k, n in seen.items() if n > 1)
    return dups


def _fmt_t(t: int | None) -> str:
    if t is None:
        return "?"
    return datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime("%d/%m %H:%M")


TELLABLE_KINDS = {"station", "project", "amp", "climo", "coast", "zee-enter", "alert-on"}


def collect_stock(moments: dict) -> tuple[Counter, list[tuple[int, str]]]:
    """(compteur par kind, [(instant, titre)] des changements racontables)."""
    stock: Counter = Counter()
    told: list[tuple[int, str]] = []
    for row in moments.get("moments") or []:
        t_row = _ms(row.get("t"))
        for c in row.get("changes") or []:
            kind = str(c.get("kind") or "?")
            stock[kind] += 1
            if kind == "alert-on" and "aire marine" not in str(c.get("title") or "").casefold():
                continue  # les formalités d'entrée n'ont pas de phrase : pas racontables
            if kind in TELLABLE_KINDS and t_row is not None:
                told.append((t_row, str(c.get("title") or "")))
    told.sort()
    return stock, told


def gap_has_untold_stock(
    g_a: int | None, g_b: int | None, stock_told: list[tuple[int, str]], text: str,
) -> bool:
    """Vrai si le stock a, dans le trou, un item racontable PAS déjà dans le
    texte (un groupe « puis les eaux fidjiennes » couvre l'entrée fidjienne)."""
    if g_a is None or g_b is None:
        return False
    margin = 6 * 3_600_000
    text_cf = (text or "").casefold()
    stop_words = {"économique", "exclusive", "overlapping", "protégée", "aucun"}
    for t, title in stock_told:
        if not (g_a + margin < t < g_b - margin):
            continue
        words = [
            w for w in re.findall(r"[a-zà-ÿ-]{5,}", title.casefold())
            if w not in stop_words
        ]
        if not any(w in text_cf for w in words):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:8010")
    ap.add_argument("--film", help="fichier JSON GET /film (sinon API)")
    ap.add_argument("--moments", help="fichier JSON GET /moments (sinon API)")
    ap.add_argument("--clock", help="fichier JSON GET /voyage/official (sinon API)")
    ap.add_argument("--lang", default="fr")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.film:
        film = json.load(open(args.film))
    else:
        film = _get(f"{args.api}/voyage/official/film?lang={args.lang}&seconds=0&style=raw")
    if args.moments:
        moments = json.load(open(args.moments))
    else:
        moments = _get(f"{args.api}/voyage/official/moments")
    clock = None
    try:
        clock = json.load(open(args.clock)) if args.clock else _get(f"{args.api}/voyage/official")
    except Exception as exc:  # l'horloge affine la mesure, elle n'est pas bloquante
        print(f"(horloge indisponible : {exc} — jours comptés depuis l'arrivée)")
    departs = departures_from_clock(clock)

    stock, stock_told = collect_stock(moments)

    chapters = film.get("chapters") or []
    said: Counter = Counter()
    orphans: list[str] = []
    print(f"film : {len(chapters)} chapitres, {film.get('chars')} caractères")
    print(f"stock : {sum(stock.values())} changements {dict(stock)}")
    print()
    print("chapitre                                    mer(j)  car.  items  plancher  même-min  trou-max")
    fails = 0
    for i, ch in enumerate(chapters):
        air = bool(AIR_RE.search(ch.get("text") or ""))
        days = 0.0 if air else sea_days(ch, departs)
        items = chapter_items(ch)
        for e in items:
            said[str(e.get("kind") or "?")] += 1
        floor = min(16, max(4, int(days / 1.5))) if days > 3 else 0
        minute = same_minute_share(ch)
        gap, g_a, g_b = max_gap(ch, departs)
        label = f"ch{i} {ch.get('fromName', '')[:18]} -> {ch.get('toName', '')[:14]}"
        flags = ["AVION"] if air else []
        if days > 3 and len(items) < floor:
            flags.append("ITEMS<PLANCHER")
        if days > 3 and minute > 0.20:
            flags.append("MEME-MINUTE>20%")
        if days > 3 and gap > 0.30:
            # Un trou n'est un défaut que si le stock avait quelque chose à y
            # dire qui n'est PAS déjà dans le texte (un groupe « puis les eaux
            # fidjiennes » couvre l'entrée fidjienne, même ancrée plus tôt).
            missing = gap_has_untold_stock(g_a, g_b, stock_told, ch.get("text") or "")
            flags.append("TROU>30%" if missing else "(trou, stock déjà dit ou vide)")
        fails += len([f for f in flags if f not in {"AVION", "(trou, stock déjà dit ou vide)"}])
        print(f"{label:44.44}  {days:5.1f}  {len(ch.get('text') or ''):4d}   {len(items):4d}  "
              f"{floor:8d}  {minute:7.0%}  {gap if days > 3 else 0:7.0%}  {' '.join(flags)}")
        if args.verbose and days > 3:
            blocks = frozen_minute_blocks(ch)
            if blocks:
                print(f"      pire minute : {blocks[0][0]} car. « {blocks[0][2]}… »")
            if g_a is not None:
                print(f"      pire trou   : {_fmt_t(g_a)} → {_fmt_t(g_b)}")
        orphans.extend(orphan_zee_adjectives(ch.get("text") or ""))
    dups = duplicate_sites(chapters)
    print()
    print(f"dits  : {dict(said)}")
    print(f"stations dites {said.get('sci', 0)} / stock {stock.get('station', 0)} ; "
          f"projets dits {said.get('project', 0)} / stock {stock.get('project', 0)} ; "
          f"AMP dites {said.get('amp', 0) + said.get('wx', 0)} / stock "
          f"{stock.get('amp', 0)}+{stock.get('alert-on', 0)} alertes ; "
          f"climo dites {said.get('climo', 0)} / stock {stock.get('climo', 0)}")
    print(f"doublons de site : {dups or 'aucun'}")
    print(f"adjectifs ZEE orphelins : {orphans or 'aucun'}")
    if dups or orphans:
        fails += 1
    print(f"\n{'KO' if fails else 'OK'} ({fails} défaut(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
