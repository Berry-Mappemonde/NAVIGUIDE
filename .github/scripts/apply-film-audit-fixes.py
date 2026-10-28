#!/usr/bin/env python3
"""Apply targeted film-integrity fixes to the isolated PR integration tree."""
from pathlib import Path

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)

film_path = Path("naviguide-simulator/server/film_script.py")
film = film_path.read_text(encoding="utf-8")

anchor_line = '"anchors": chapter_anchors(text, anchored, w["tA"], w["tB"], lang),'
count = film.count(anchor_line)
if count != 3:
    raise SystemExit(f"anchor source capture: expected 3 chapter builders, found {count}")
film = film.replace(
    anchor_line,
    anchor_line + '\n                "_anchorInputs": list(anchored),',
)

helper_anchor = "def reanchor_written_chapter(chapter: dict, written_text: str, lang: str) -> list[dict]:"
helper = '''def _drop_stale_dated_sentences(chapters: list[dict], *, lang: str = "fr") -> None:
    """Drop a dated sentence when it contradicts its chapter's actual start date.

    A stale observation date should not invalidate the entire written film.
    Unreconcilable dated statements are omitted rather than silently rewritten.
    """
    for chapter in chapters or []:
        if not isinstance(chapter, dict):
            continue
        text = str(chapter.get("text") or "")
        sentences = _sentences(text)
        start_ms = _ms(chapter.get("tA"))
        if not text or not sentences or start_ms is None:
            continue
        kept = []
        kept_old_indices = []
        for i, sentence in enumerate(sentences):
            if _spoken_before_anchor(sentence, start_ms, lang):
                continue
            kept.append(sentence)
            kept_old_indices.append(i)
        if len(kept) == len(sentences):
            continue
        new_text = " ".join(kept).strip()
        chapter["text"] = new_text
        # Current builders retain semantic anchor inputs and rebuild them later.
        # For legacy snapshots, move surviving anchors with their sentences.
        if "_anchorInputs" not in chapter:
            old_starts = _sentence_starts(text, sentences)
            new_starts = _sentence_starts(new_text, kept)
            old_to_new = {old_i: new_i for new_i, old_i in enumerate(kept_old_indices)}
            moved = []
            for anchor in chapter.get("anchors") or []:
                if not isinstance(anchor, dict):
                    continue
                try:
                    idx = int(anchor.get("charIdx") or 0)
                except (TypeError, ValueError):
                    continue
                hit = next(
                    (i for i, start in enumerate(old_starts)
                     if start <= idx < start + max(1, len(sentences[i]))),
                    len(sentences) - 1,
                )
                if hit not in old_to_new:
                    continue
                new_i = old_to_new[hit]
                local = max(0, idx - old_starts[hit])
                moved.append({
                    **anchor,
                    "charIdx": new_starts[new_i] + min(local, max(0, len(kept[new_i]) - 1)),
                })
            chapter["anchors"] = moved


def _reconcile_film_indices(chapters: list[dict], *, lang: str = "fr") -> None:
    """Rebuild text-linked indices after cuts/injections; repair legacy snapshots too.

    Builders keep source anchor tuples privately until all character-budget and
    air-sentence edits are complete. Public payloads never include that field.
    Cached legacy plans without source tuples get bounded, monotone anchors.
    """
    for chapter in chapters or []:
        if not isinstance(chapter, dict):
            continue
        text = str(chapter.get("text") or "")
        size = len(text)
        source_anchors = chapter.pop("_anchorInputs", None)
        if source_anchors is not None:
            ta, tb = _ms(chapter.get("tA")), _ms(chapter.get("tB"))
            chapter["anchors"] = (
                chapter_anchors(text, source_anchors, ta, tb, lang)
                if text and ta is not None and tb is not None else []
            )
        else:
            old = [a for a in (chapter.get("anchors") or []) if isinstance(a, dict)]
            if not text:
                chapter["anchors"] = []
            elif old:
                parsed = []
                for a in old:
                    try:
                        idx = int(a.get("charIdx") or 0)
                    except (TypeError, ValueError):
                        continue
                    parsed.append((idx, a))
                if any(idx < 0 or idx >= size for idx, _ in parsed):
                    old_span = max(1, max((idx for idx, _ in parsed), default=size - 1))
                    parsed = [
                        (int(round(max(0, idx) * (size - 1) / old_span)), a)
                        for idx, a in parsed
                    ]
                parsed.sort(key=lambda pair: pair[0])
                bounded = []
                last_idx = -1
                last_t = None
                for idx, row in parsed:
                    idx = max(0, min(size - 1, idx))
                    if idx <= last_idx:
                        idx = last_idx + 1
                    if idx >= size:
                        continue
                    t_ms = _ms(row.get("t"))
                    if t_ms is not None and last_t is not None and t_ms < last_t:
                        t_ms = last_t
                    if t_ms is not None:
                        last_t = t_ms
                    bounded.append({
                        **row,
                        "charIdx": idx,
                        **({"t": _iso(t_ms)} if t_ms is not None else {}),
                    })
                    last_idx = idx
                chapter["anchors"] = bounded

        # Event bubbles use text positions too. Re-find their named fact in the
        # final text; fall back to the event timestamp interpolated over the leg.
        for event in chapter.get("events") or []:
            if not isinstance(event, dict):
                continue
            card = event.get("card") if isinstance(event.get("card"), dict) else {}
            fact = str(event.get("fact") or card.get("text") or "")
            idx = _event_char_idx(event, chapter, fact)
            event["charIdx"] = max(0, min(max(0, size - 1), int(idx or 0)))
        chapter["events"] = sorted(
            [e for e in (chapter.get("events") or []) if isinstance(e, dict)],
            key=lambda e: (int(e.get("charIdx") or 0), str(e.get("id") or "")),
        )


'''
film = replace_once(film, helper_anchor, helper + helper_anchor, "insert index reconciler")

moments_end = "    chapters[:] = _drop_degenerate_chapters(chapters)\n    chars = script_chars(chapters)"
film = replace_once(
    film, moments_end,
    "    chapters[:] = _drop_degenerate_chapters(chapters)\n"
    "    _drop_stale_dated_sentences(chapters, lang=lang)\n"
    "    _reconcile_film_indices(chapters, lang=lang)\n"
    "    chars = script_chars(chapters)",
    "reconcile moments builder",
)

regular_start = film.index("def build_raw_script(")
regular_end = film.index("def journal_fingerprint(", regular_start)
sub = film[regular_start:regular_end]
sub = replace_once(
    sub,
    "    chars = script_chars(chapters)\n    return _with_dc_subjects({",
    "    _drop_stale_dated_sentences(chapters, lang=lang)\n"
    "    _reconcile_film_indices(chapters, lang=lang)\n"
    "    chars = script_chars(chapters)\n"
    "    return _with_dc_subjects({",
    "reconcile regular builder",
)
film = film[:regular_start] + sub + film[regular_end:]

film = replace_once(
    film,
    "    t = ev.get(\"tMs\")\n"
    "    if t_a is not None and t_b is not None and t is not None and t_b > t_a:",
    "    t = ev.get(\"tMs\")\n"
    "    if t is None:\n"
    "        card = ev.get(\"card\") if isinstance(ev.get(\"card\"), dict) else {}\n"
    "        t = _ms(ev.get(\"t\") or card.get(\"at\"))\n"
    "    if t_a is not None and t_b is not None and t is not None and t_b > t_a:",
    "event timestamp fallback",
)

film = replace_once(
    film,
    "    if super_plan is None or int((super_stats or {}).get(\"rewritten\") or 0) <= 0:\n"
    "        return None, None, stats",
    "    if super_plan is None or int((super_stats or {}).get(\"rewritten\") or 0) <= 0:\n"
    "        stats[\"reason\"] = \"no-rewritten-sentences\"\n"
    "        stats[\"writeStats\"] = {\n"
    "            \"rewritten\": int((super_stats or {}).get(\"rewritten\") or 0),\n"
    "            \"fallen\": int((super_stats or {}).get(\"fallen\") or 0),\n"
    "            \"source\": str((super_stats or {}).get(\"source\") or \"rules\"),\n"
    "        }\n"
    "        stats[\"source\"] = str((super_stats or {}).get(\"source\") or \"rules\")\n"
    "        return None, None, stats",
    "record no-rewrite reason",
)
film = replace_once(
    film,
    "    if not ok_fr:\n"
    "        stats[\"faults\"] = review_fr.get(\"faults\") or []\n"
    "        return None, None, stats",
    "    if not ok_fr:\n"
    "        stats[\"reason\"] = \"local-reread-rejected\"\n"
    "        stats[\"faults\"] = review_fr.get(\"faults\") or []\n"
    "        return None, None, stats",
    "record reread reason",
)
film = replace_once(
    film,
    "    return 1 <= delta <= 60",
    "    return 1 <= delta <= 365",
    "widen stale-date window",
)
film = replace_once(
    film,
    "            if _known_stop(place, route_rows) and _spoken_before_anchor(sentence, t_ms, lang):\n                return",
    "            if _spoken_before_anchor(sentence, t_ms, lang):\n                return",
    "reject stale dates on non-port events too",
)
film = replace_once(
    film,
    "            sentence = event_sentence(rich, lang, display_t0=display_t0).strip()\n"
    "            if not sentence:\n"
    "                return\n"
    "            char_idx = len(\" \".join(bits)) + (1 if bits else 0)",
    "            sentence = event_sentence(rich, lang, display_t0=display_t0).strip()\n"
    "            if not sentence or _spoken_before_anchor(sentence, ev.get(\"tMs\"), lang):\n"
    "                return\n"
    "            char_idx = len(\" \".join(bits)) + (1 if bits else 0)",
    "reject stale event dates in the regular composer",
)
film = replace_once(
    film,
    "    raw = dict(plan)\n"
    "    raw[\"targetSeconds\"] = _film_seconds(seconds if seconds is not None else plan.get(\"targetSeconds\"))",
    "    raw = {\n"
    "        **plan,\n"
    "        \"chapters\": [dict(ch) for ch in (plan.get(\"chapters\") or []) if isinstance(ch, dict)],\n"
    "    }\n"
    "    _drop_stale_dated_sentences(raw[\"chapters\"], lang=\"fr\")\n"
    "    raw[\"targetSeconds\"] = _film_seconds(seconds if seconds is not None else plan.get(\"targetSeconds\"))",
    "sanitize stale cached chapter dates before Super",
)
film_path.write_text(film, encoding="utf-8")

test_path = Path("naviguide-simulator/server/tests/test_film_script.py")
test = test_path.read_text(encoding="utf-8")
test = replace_once(
    test, "    _nm_label,\n)", "    _nm_label,\n    _drop_stale_dated_sentences,\n    _reconcile_film_indices,\n    _dates_regress,\n)",
    "import reconciler",
)
test += '''

def test_stale_date_inside_later_chapter_is_removed_before_writing():
    """Une date vieille de 82 jours ne doit pas faire rejeter tout le récit."""
    chapter = {
        "tA": "2026-08-13T22:50:23Z",
        "tB": "2026-08-17T08:48:38Z",
        "text": (
            "Le 23 mai, une bouée. 489 milles, trois jours de mer. "
            "Arrivée à Saint-Pierre le 17 août."
        ),
        "anchors": [
            {"charIdx": 0, "t": "2026-08-14T23:50:23Z"},
            {"charIdx": 117, "t": "2026-08-14T23:50:23Z"},
            {"charIdx": 205, "t": "2026-08-17T08:48:38Z"},
        ],
        "events": [],
    }

    _drop_stale_dated_sentences([chapter], lang="fr")

    assert "23 mai" not in chapter["text"]
    assert "489 milles" in chapter["text"]
    assert "17 août" in chapter["text"]
    assert not _dates_regress(chapter["text"], "fr")


def test_reconcile_film_indices_after_text_cut():
    """Les index utilisent le texte final, pas celui d'avant la coupe budgétaire."""
    text = "Départ vers Ajaccio. La traversée continue."
    chapter = {
        "id": "leg-test",
        "tA": "2026-05-15T12:00:00Z",
        "tB": "2026-06-06T03:36:48Z",
        "text": text,
        "anchors": [
            {"charIdx": 0, "t": "2026-05-15T12:00:00Z"},
            {"charIdx": 220, "t": "2026-06-06T03:36:48Z"},
        ],
        "_anchorInputs": [
            ("Départ vers Ajaccio.", _ms("2026-05-15T12:00:00Z"), {"role": "depart"}),
            ("Arrivée à Ajaccio le 6 juin.", _ms("2026-06-06T03:36:48Z"),
             {"role": "arrive", "place": "Ajaccio", "kind": "escale"}),
        ],
        "events": [{
            "id": "stop:Ajaccio",
            "kind": "stop",
            "name": "Ajaccio",
            "title": "Ajaccio",
            "fact": "Arrivée à Ajaccio le 6 juin.",
            "charIdx": 280,
            "card": {"at": "2026-06-06T03:36:48Z"},
        }],
    }

    _reconcile_film_indices([chapter], lang="fr")

    assert "_anchorInputs" not in chapter
    assert chapter["anchors"]
    assert all(0 <= a["charIdx"] < len(text) for a in chapter["anchors"])
    indices = [a["charIdx"] for a in chapter["anchors"]]
    assert indices == sorted(set(indices))
    event = chapter["events"][0]
    assert 0 <= event["charIdx"] < len(text)
    assert event["charIdx"] == text.index("Ajaccio")


def test_reconcile_film_indices_repairs_legacy_overflow_monotonically():
    """Un vieux snapshot sans métadonnées d'ancres ne publie plus d'index hors texte."""
    chapter = {
        "tA": "2026-05-15T12:00:00Z",
        "tB": "2026-06-06T03:36:48Z",
        "text": "Départ. Arrivée.",
        "anchors": [
            {"charIdx": 0, "t": "2026-05-15T12:00:00Z"},
            {"charIdx": 120, "t": "2026-05-24T12:00:00Z"},
            {"charIdx": 280, "t": "2026-06-06T03:36:48Z"},
        ],
        "events": [],
    }

    _reconcile_film_indices([chapter], lang="fr")

    indices = [a["charIdx"] for a in chapter["anchors"]]
    assert indices
    assert all(0 <= idx < len(chapter["text"]) for idx in indices)
    assert indices == sorted(set(indices))
'''
test_path.write_text(test, encoding="utf-8")

store_path = Path("naviguide-simulator/server/official_store.py")
store = store_path.read_text(encoding="utf-8")
store = replace_once(
    store,
    "    if not isinstance(fr_plan, dict) or not (fr_plan.get(\"chapters\") or []):\n"
    "        _log_fill_written(f\"written clic {lg} {secs}s : pas de rédigé ({stats.get('source')})\")\n"
    "        return serve_film(lang=lg, seconds=secs, style=\"written\")",
    "    if not isinstance(fr_plan, dict) or not (fr_plan.get(\"chapters\") or []):\n"
    "        faults = \",\".join(str(x) for x in (stats.get(\"faults\") or [])) or \"none\"\n"
    "        write_stats = stats.get(\"writeStats\") if isinstance(stats.get(\"writeStats\"), dict) else {}\n"
    "        _log_fill_written(\n"
    "            f\"written clic {lg} {secs}s : pas de rédigé \"\n"
    "            f\"reason={stats.get('reason') or 'unknown'} source={stats.get('source') or 'rules'} \"\n"
    "            f\"reread={stats.get('reread') or 'not-run'} faults={faults} \"\n"
    "            f\"rewritten={write_stats.get('rewritten', 'n/a')} fallen={write_stats.get('fallen', 'n/a')}\"\n"
    "        )\n"
    "        return serve_film(lang=lg, seconds=secs, style=\"written\")",
    "log detailed fallback",
)
store = replace_once(
    store,
    "    _log_fill_written(\n"
    "        f\"written clic {lg} {secs}s : source={stats.get('source')} \"\n"
    "        f\"ultra={stats.get('ultra_edit')}/{stats.get('ultra_judge')} lightning={stats.get('lightning')}\"\n"
    "    )",
    "    _log_fill_written(\n"
    "        f\"written clic {lg} {secs}s : source={stats.get('source')} \"\n"
    "        f\"ultra={stats.get('ultra_edit')}/{stats.get('ultra_judge')} lightning={stats.get('lightning')} \"\n"
    "        f\"reread={stats.get('reread') or 'n/a'}\"\n"
    "    )",
    "log successful reread",
)
store_path.write_text(store, encoding="utf-8")

print("Applied film index, timestamp fallback, and writing-failure diagnostic patches.")
