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
    """Drop a dated sentence that predates its chapter, keeping source dates intact."""
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
            if _spoken_before_anchor(sentence, start_ms, lang, max_days=365):
                continue
            kept.append(sentence)
            kept_old_indices.append(i)
        if len(kept) == len(sentences):
            continue
        new_text = " ".join(kept).strip()
        chapter["text"] = new_text
        # For legacy snapshots, drop invalid or removed-sentence anchors before
        # remapping; never attach an arbitrary overflow anchor to the last sentence.
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
                if idx < 0 or idx >= len(text):
                    continue
                hit = next(
                    (i for i, start in enumerate(old_starts)
                     if start <= idx < start + max(1, len(sentences[i]))),
                    None,
                )
                if hit is None or hit not in old_to_new:
                    continue
                new_i = old_to_new[hit]
                local = max(0, idx - old_starts[hit])
                moved.append({
                    **anchor,
                    "charIdx": new_starts[new_i] + min(local, max(0, len(kept[new_i]) - 1)),
                })
            chapter["anchors"] = moved


def _reconcile_film_indices(chapters: list[dict], *, lang: str = "fr") -> None:
    """Rebuild character indices from final chapter text and semantic dates.

    Newly generated chapters retain source anchor tuples. Legacy snapshots do not:
    rebuild their date-bearing phrases semantically instead of linearly scaling an
    obsolete index into unrelated text after a budget cut.
    """
    for chapter in chapters or []:
        if not isinstance(chapter, dict):
            continue
        text = str(chapter.get("text") or "")
        size = len(text)
        source_anchors = chapter.pop("_anchorInputs", None)
        ta, tb = _ms(chapter.get("tA")), _ms(chapter.get("tB"))
        if source_anchors is not None:
            rebuilt = chapter_anchors(text, source_anchors, ta, tb, lang) if text and ta is not None and tb is not None else []
            chapter["anchors"] = _strict_increasing_anchors(rebuilt)
        elif not text:
            chapter["anchors"] = []
        else:
            sentences = _sentences(text)
            starts = _sentence_starts(text, sentences)
            old_by_sentence = {}
            for anchor in chapter.get("anchors") or []:
                if not isinstance(anchor, dict):
                    continue
                try:
                    idx = int(anchor.get("charIdx") or 0)
                except (TypeError, ValueError):
                    continue
                if idx < 0 or idx >= size:
                    continue
                sentence_i = next(
                    (i for i, start in enumerate(starts)
                     if start <= idx < start + max(1, len(sentences[i]))),
                    None,
                )
                if sentence_i is None:
                    continue
                sent = sentences[sentence_i]
                t_raw = anchor.get("t")
                t_ms = t_raw if isinstance(t_raw, int) else _ms(t_raw)
                # Any sentence with an explicit date gets a fresh semantic time below.
                if _parse_spoken_date(sent, lang) is not None or _is_arrival_sentence(sent):
                    continue
                if t_ms is None or _spoken_before_anchor(sent, t_ms, lang, max_days=365):
                    continue
                old_by_sentence.setdefault(sentence_i, (t_ms, anchor))

            anchored = []
            span = max(1, size - 1)
            for i, sentence in enumerate(sentences):
                start = starts[i] if i < len(starts) else 0
                spoken_date = _parse_spoken_date(sentence, lang)
                extra = {}
                if _is_arrival_sentence(sentence):
                    t_ms = tb
                    extra["role"] = "arrive"
                elif spoken_date is not None:
                    t_ms = int(spoken_date.timestamp() * 1000)
                    if _is_depart_sentence(sentence):
                        extra["role"] = "depart"
                    if ta is not None:
                        t_ms = max(ta, t_ms)
                    if tb is not None:
                        t_ms = min(tb, t_ms)
                elif _is_depart_sentence(sentence) and ta is not None:
                    t_ms = ta
                    extra["role"] = "depart"
                elif i in old_by_sentence:
                    t_ms, old = old_by_sentence[i]
                    for key in ("place", "kind", "role"):
                        if old.get(key):
                            extra[key] = old[key]
                elif ta is not None and tb is not None:
                    t_ms = ta + int(round((tb - ta) * start / span))
                else:
                    t_ms = None
                if t_ms is None:
                    continue
                anchored.append((sentence, t_ms, extra))

            rebuilt = chapter_anchors(text, anchored, ta, tb, lang) if ta is not None and tb is not None else []
            chapter["anchors"] = _strict_increasing_anchors(rebuilt)

        # Event bubbles also carry text indices. Search the final phrase first;
        # use timestamp interpolation only when a matching phrase is absent.
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
    "def _spoken_before_anchor(sentence: str, t_ms: Any, lang: str) -> bool:",
    "def _spoken_before_anchor(sentence: str, t_ms: Any, lang: str, *, max_days: int = 60) -> bool:",
    "make stale-date window explicit",
)
film = replace_once(
    film,
    "    return 1 <= delta <= 60",
    "    return 1 <= delta <= max(0, int(max_days))",
    "parameterize stale-date window",
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
film = replace_once(
    film,
    "            row: dict[str, Any] = {\"name\": name}\n"
    "            for key in (\"nm\", \"filmNm\"):\n",
    "            row: dict[str, Any] = {\"name\": name}\n"
    "            if raw.get(\"iso\"):\n"
    "                row[\"iso\"] = str(raw[\"iso\"])\n"
    "            for key in (\"nm\", \"filmNm\"):\n",
    "preserve stop timestamps for repeated visits",
)
film = replace_once(
    film,
    "            rows.append(row)\n        elif str(raw or \"\").strip():",
    "            rows.append(row)\n        elif str(raw or \"\").strip():",
    "retain existing stop row shape",
)
film = replace_once(
    film,
    "        row: dict[str, Any] = {\"name\": name}\n        nm = mark.get(\"filmNm\")",
    "        row: dict[str, Any] = {\"name\": name}\n        if mark.get(\"iso\"):\n            row[\"iso\"] = str(mark[\"iso\"])\n        nm = mark.get(\"filmNm\")",
    "preserve missing air stop timestamps",
)
film = replace_once(
    film,
    "def _pair_indexes(rows: list[dict], frm: str, to: str) -> tuple[Optional[int], Optional[int]]:\n"
    "    ia = _index_row(rows, frm)\n"
    "    if ia is None:\n"
    "        return None, None\n"
    "    return ia, _index_row(rows, to, after=ia)\n\n\n"
    "def _sea_between(rows: list[dict], frm: str, to: str) -> list[str]:\n"
    "    ia, ib = _pair_indexes(rows, frm, to)\n"
    "    if ia is None or ib is None or ib <= ia + 1:\n"
    "        return []\n"
    "    missed: list[str] = []\n"
    "    for row in rows[ia + 1:ib]:\n"
    "        label = _stop_spoken(row.get(\"name\") or \"\")\n"
    "        if not label or _is_air_only_stop(label):\n"
    "            continue\n"
    "        missed.append(label)\n"
    "    return missed\n\n\n"
    "def _span_nm(rows: list[dict], frm: str, to: str) -> Optional[float]:\n"
    "    ia, ib = _pair_indexes(rows, frm, to)\n"
    "    if ia is None or ib is None or ib <= ia:\n"
    "        return None\n"
    "    a, b = _row_nm(rows[ia]), _row_nm(rows[ib])\n"
    "    if a is None or b is None:\n"
    "        return None\n"
    "    gap = b - a\n"
    "    return gap if gap > 1 else None",
    "def _pair_indexes(\n"
    "    rows: list[dict], frm: str, to: str, *,\n"
    "    start_ms: Optional[int] = None, end_ms: Optional[int] = None,\n"
    ") -> tuple[Optional[int], Optional[int]]:\n"
    "    # Repeated ports (Cayenne on the return flight) must be matched to this\n"
    "    # chapter's dates, not the first same-name port in the entire itinerary.\n"
    "    ia = None\n"
    "    if start_ms is not None:\n"
    "        candidates = []\n"
    "        for i, row in enumerate(rows):\n"
    "            if not _known_stop(frm, [row]):\n"
    "                continue\n"
    "            at = _ms(row.get(\"iso\"))\n"
    "            if at is not None and at <= start_ms + 12 * 3600 * 1000:\n"
    "                candidates.append((abs(start_ms - at), i, at))\n"
    "        if candidates:\n"
    "            close = [x for x in candidates if x[0] <= 3 * 86400000]\n"
    "            ia = min(close or candidates)[1]\n"
    "    if ia is None:\n"
    "        ia = _index_row(rows, frm)\n"
    "    if ia is None:\n"
    "        return None, None\n"
    "    if end_ms is not None:\n"
    "        candidates = []\n"
    "        for i in range(ia + 1, len(rows)):\n"
    "            row = rows[i]\n"
    "            if not _known_stop(to, [row]):\n"
    "                continue\n"
    "            at = _ms(row.get(\"iso\"))\n"
    "            if at is not None and at >= start_ms - 12 * 3600 * 1000:\n"
    "                candidates.append((abs(end_ms - at), i, at))\n"
    "        if candidates:\n"
    "            close = [x for x in candidates if x[0] <= 3 * 86400000]\n"
    "            return ia, min(close or candidates)[1]\n"
    "    return ia, _index_row(rows, to, after=ia)\n\n\n"
    "def _sea_between(\n"
    "    rows: list[dict], frm: str, to: str, *,\n"
    "    start_ms: Optional[int] = None, end_ms: Optional[int] = None,\n"
    ") -> list[str]:\n"
    "    ia, ib = _pair_indexes(rows, frm, to, start_ms=start_ms, end_ms=end_ms)\n"
    "    if ia is None or ib is None or ib <= ia + 1:\n"
    "        return []\n"
    "    missed: list[str] = []\n"
    "    for row in rows[ia + 1:ib]:\n"
    "        label = _stop_spoken(row.get(\"name\") or \"\")\n"
    "        if not label or _is_air_only_stop(label):\n"
    "            continue\n"
    "        if same_stop(label, frm) or same_stop(label, to):\n"
    "            continue\n"
    "        missed.append(label)\n"
    "    return missed\n\n\n"
    "def _span_nm(\n"
    "    rows: list[dict], frm: str, to: str, *,\n"
    "    start_ms: Optional[int] = None, end_ms: Optional[int] = None,\n"
    ") -> Optional[float]:\n"
    "    ia, ib = _pair_indexes(rows, frm, to, start_ms=start_ms, end_ms=end_ms)\n"
    "    if ia is None or ib is None or ib <= ia:\n"
    "        return None\n"
    "    a, b = _row_nm(rows[ia]), _row_nm(rows[ib])\n"
    "    if a is None or b is None:\n"
    "        return None\n"
    "    gap = b - a\n"
    "    return gap if gap > 1 else None",
    "match repeated route visits using chapter timestamps",
)
film = replace_once(
    film,
    "def _cap_leg_faults(text: str, rows: list[dict], frm: str) -> list[str]:\n"
    "    \"\"\"« cap sur Dzaoudzi » depuis Papeete : la destination n'est pas l'escale suivante.\"\"\"",
    "def _cap_leg_faults(\n"
    "    text: str, rows: list[dict], frm: str, *,\n"
    "    start_ms: Optional[int] = None, end_ms: Optional[int] = None,\n"
    ") -> list[str]:\n"
    "    \"\"\"« cap sur Dzaoudzi » depuis Papeete : la destination n'est pas l'escale suivante.\"\"\"",
    "make chapter dates available to cap checker",
)
film = replace_once(
    film,
    "        skipped = _sea_between(rows, frm, to)\n"
    "        if skipped and \"skip\" not in faults:",
    "        skipped = _sea_between(rows, frm, to, start_ms=start_ms, end_ms=end_ms)\n"
    "        if skipped and \"skip\" not in faults:",
    "time-aware skip checker",
)
film = replace_once(
    film,
    "        span = _span_nm(rows, frm, to)\n"
    "        if span is None:\n"
    "            continue\n"
    "        close = abs(float(nums[0]) - span)",
    "        span = _span_nm(rows, frm, to, start_ms=start_ms, end_ms=end_ms)\n"
    "        if span is None:\n"
    "            continue\n"
    "        close = abs(float(nums[0]) - span)",
    "time-aware distance checker",
)
film = replace_once(
    film,
    "        for fault in _cap_leg_faults(chapter.get(\"text\") or \"\", rows, str(chapter.get(\"fromName\") or \"\")):",
    "        for fault in _cap_leg_faults(\n"
    "            chapter.get(\"text\") or \"\", rows, str(chapter.get(\"fromName\") or \"\"),\n"
    "            start_ms=_ms(chapter.get(\"tA\")), end_ms=_ms(chapter.get(\"tB\")),\n"
    "        ):",
    "pass chapter time to route gate",
)
film = replace_once(
    film,
    "def _route_stops_for_reread(plan: dict | None) -> list[dict]:",
    "def _insert_chapter_air_revisits(rows: list[dict], plan: dict | None) -> list[dict]:\n"
    "    \"\"\"Insert a dated second arrival at the destination of an air-transfer chapter.\"\"\"\n"
    "    out = [dict(row) for row in (rows or [])]\n"
    "    chapters = [ch for ch in (plan or {}).get(\"chapters\") or [] if isinstance(ch, dict)]\n"
    "    for i, chapter in enumerate(chapters[:-1]):\n"
    "        frm = str(chapter.get(\"fromName\") or \"\")\n"
    "        to = str(chapter.get(\"toName\") or \"\")\n"
    "        if not _is_air_leg(frm, to):\n"
    "            continue\n"
    "        nxt = chapters[i + 1]\n"
    "        if not same_stop(str(nxt.get(\"fromName\") or \"\"), to):\n"
    "            continue\n"
    "        iso = str(nxt.get(\"tA\") or chapter.get(\"tB\") or \"\")\n"
    "        at = _ms(iso)\n"
    "        if at is None:\n"
    "            continue\n"
    "        present = any(\n"
    "            same_stop(str(row.get(\"name\") or \"\"), to)\n"
    "            and _ms(row.get(\"iso\")) is not None\n"
    "            and abs(_ms(row.get(\"iso\")) - at) <= 12 * 3600 * 1000\n"
    "            for row in out\n"
    "        )\n"
    "        if present:\n"
    "            continue\n"
    "        item = {\"name\": to, \"iso\": iso}\n"
    "        at_or_before = [\n"
    "            j for j, row in enumerate(out)\n"
    "            if _ms(row.get(\"iso\")) is not None and _ms(row.get(\"iso\")) <= at\n"
    "        ]\n"
    "        insert_at = (max(at_or_before) + 1) if at_or_before else len(out)\n"
    "        out.insert(insert_at, item)\n"
    "    return out\n\n\n"
    "def _route_stops_for_reread(plan: dict | None) -> list[dict]:",
    "insert timestamped air-transfer revisits",
)
film = replace_once(
    film,
    "    if isinstance(explicit, list) and explicit:\n"
    "        return _as_stop_rows(explicit)",
    "    if isinstance(explicit, list) and explicit:\n"
    "        return _insert_chapter_air_revisits(_as_stop_rows(explicit), plan)",
    "augment explicit route stops with repeated air arrivals",
)
film = replace_once(
    film,
    "        rows = _insert_missing_air(_as_stop_rows(marks), clock.get(\"marks\"))\n"
    "        if len(rows) >= 8:",
    "        rows = _insert_missing_air(_as_stop_rows(marks), clock.get(\"marks\"))\n"
    "        rows = _insert_chapter_air_revisits(rows, plan)\n"
    "        if len(rows) >= 8:",
    "augment official stops with repeated air arrivals",
)
film = replace_once(
    film,
    "    if _skip_pairs(blob, rows):",
    "    if _skip_pairs(blob, rows, chapters=chapters):",
    "validate route skip against the matching chapter interval",
)
film = replace_once(
    film,
    "def _skip_pairs(text: str, rows: list[dict]) -> bool:",
    "def _skip_pairs(text: str, rows: list[dict], *, chapters: list | None = None) -> bool:",
    "allow time-aware skip checks",
)
film = replace_once(
    film,
    "        if _sea_between(rows, frm, to):\n"
    "            return True\n"
    "    return False\n\n\ndef _upcoming_omits",
    "        chapter = next((\n"
    "            ch for ch in (chapters or []) if isinstance(ch, dict)\n"
    "            and same_stop(str(ch.get(\"fromName\") or \"\"), frm)\n"
    "            and same_stop(str(ch.get(\"toName\") or \"\"), to)\n"
    "            and bool(_LEAVE_FOR_RE.search(ch.get(\"text\") or \"\"))\n"
    "        ), None)\n"
    "        start_ms = _ms(chapter.get(\"tA\")) if chapter else None\n"
    "        end_ms = _ms(chapter.get(\"tB\")) if chapter else None\n"
    "        if _sea_between(rows, frm, to, start_ms=start_ms, end_ms=end_ms):\n"
    "            return True\n"
    "    return False\n\n\ndef _upcoming_omits",
    "time-aware departure skip check",
)
hook_path = Path("naviguide-simulator/src/hooks/useReplay.js")
hook = hook_path.read_text(encoding="utf-8")
hook = replace_once(
    hook,
    "      const done = filmShouldFinish({\n"
    "        voiceClock,\n"
    "        speaking,\n"
    "        voiceAllDone,\n"
    "        linearFinish: linear.finish,",
    "      const holdForSelectedBudget = shouldHoldFilmForBudget({\n"
    "        userBudget: budgetRef.current,\n"
    "        wallElapsed,\n"
    "        lastChapter: linear.lastReached,\n"
    "      });\n"
    "      const done = filmShouldFinish({\n"
    "        voiceClock,\n"
    "        speaking,\n"
    "        voiceAllDone,\n"
    "        linearFinish: linear.finish && !holdForSelectedBudget,",
    "hold the last frame until the selected film budget",
)
hook_path.write_text(hook, encoding="utf-8")

film_path.write_text(film, encoding="utf-8")

test_path = Path("naviguide-simulator/server/tests/test_film_script.py")
test = test_path.read_text(encoding="utf-8")
test = replace_once(
    test, "    _nm_label,\n)", "    _nm_label,\n    _drop_stale_dated_sentences,\n    _reconcile_film_indices,\n    _dates_regress,\n    _anchor_dates_regress,\n    _sea_between,\n    _insert_chapter_air_revisits,\n)",
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
test += '''

def test_legacy_arrival_anchor_is_rebuilt_from_the_spoken_date():
    """A stale September anchor must not point into the August departure sentence."""
    text = (
        "Le 30 août, le catamaran reprend la mer, départ vers Papeete "
        "(Polynésie française). Arrivée à Papeete (Polynésie française) le 13 octobre."
    )
    chapter = {
        "tA": "2026-08-30T03:57:30Z",
        "tB": "2026-10-13T19:07:28Z",
        "text": text,
        "anchors": [
            {"charIdx": 0, "t": "2026-08-30T03:57:30Z"},
            {"charIdx": 42, "t": "2026-08-30T03:57:30Z"},
            {"charIdx": 104, "t": "2026-09-02T06:42:36Z"},
            {"charIdx": 119, "t": "2026-10-04T21:56:56Z"},
            {"charIdx": 137, "t": "2026-10-13T19:07:28Z"},
        ],
        "events": [],
    }

    _reconcile_film_indices([chapter], lang="fr")

    assert not _anchor_dates_regress([chapter], "fr")
    anchors = chapter["anchors"]
    assert anchors
    assert all(0 <= a["charIdx"] < len(text) for a in anchors)
    assert all(_ms(anchors[i]["t"]) <= _ms(anchors[i + 1]["t"]) for i in range(len(anchors) - 1))
    assert any(
        a["charIdx"] >= text.index("Arrivée")
        and _ms(a["t"]) == _ms(chapter["tB"])
        for a in anchors
    )


def test_sea_between_ignores_a_duplicate_of_the_current_port():
    rows = [
        {"name": "Saint-Pierre", "iso": "2026-08-17T08:48:38Z"},
        {"name": "Saint-Pierre", "iso": "2026-08-20T22:16:06Z"},
        {"name": "Halifax", "iso": "2026-08-28T19:57:30Z"},
    ]
    assert _sea_between(
        rows, "Saint-Pierre", "Halifax",
        start_ms=_ms("2026-08-20T22:16:06Z"),
        end_ms=_ms("2026-08-28T19:57:30Z"),
    ) == []


def test_air_return_inserts_a_second_cayenne_visit_by_time():
    rows = [
        {"name": "Cayenne", "iso": "2026-08-10T14:50:23Z"},
        {"name": "Halifax", "iso": "2026-08-29T19:57:30Z"},
        {"name": "Papeete", "iso": "2026-10-13T19:07:28Z"},
    ]
    plan = {"chapters": [
        {
            "fromName": "Halifax", "toName": "Cayenne",
            "tA": "2026-08-29T19:57:30Z", "tB": "2026-08-30T03:57:30Z",
        },
        {
            "fromName": "Cayenne", "toName": "Papeete",
            "tA": "2026-08-30T03:57:30Z", "tB": "2026-10-13T19:07:28Z",
        },
    ]}

    out = _insert_chapter_air_revisits(rows, plan)
    visits = [r for r in out if r["name"] == "Cayenne"]
    assert len(visits) == 2
    assert visits[1]["iso"] == "2026-08-30T03:57:30Z"
'''
test_path.write_text(test, encoding="utf-8")

store_path = Path("naviguide-simulator/server/official_store.py")
store = store_path.read_text(encoding="utf-8")
served_helper = '''def _sanitize_served_film_plan(plan: dict, lang: str = "fr") -> dict:
    """Repair a stored legacy snapshot on read, without mutating its cache entry."""
    chapters = []
    for source in (plan.get("chapters") or []):
        if not isinstance(source, dict):
            continue
        chapter = dict(source)
        chapter["anchors"] = [
            dict(anchor) for anchor in (source.get("anchors") or [])
            if isinstance(anchor, dict)
        ]
        chapter["events"] = []
        for source_event in (source.get("events") or []):
            if not isinstance(source_event, dict):
                continue
            event = dict(source_event)
            if isinstance(event.get("card"), dict):
                event["card"] = dict(event["card"])
            chapter["events"].append(event)
        chapters.append(chapter)
    safe = {**plan, "chapters": chapters}
    from film_script import (  # noqa: PLC0415
        _drop_stale_dated_sentences,
        _reconcile_film_indices,
        film_estimated_seconds,
        script_chars,
    )

    _drop_stale_dated_sentences(safe["chapters"], lang=lang)
    _reconcile_film_indices(safe["chapters"], lang=lang)
    safe["chars"] = script_chars(safe["chapters"])
    safe["estimatedSeconds"] = film_estimated_seconds(safe["chars"])
    return safe


'''

store = replace_once(
    store,
    "def serve_film(lang: str = \"fr\", seconds: int = 0, style: str = \"raw\") -> dict:\n",
    served_helper + "def serve_film(lang: str = \"fr\", seconds: int = 0, style: str = \"raw\") -> dict:\n",
    "insert read-time legacy snapshot sanitizer",
)
store = replace_once(
    store,
    "            wplan = _repair_served_hop(wplan, lg, voy)\n"
    "            out = _with_film_estimate(wplan)",
    "            wplan = _repair_served_hop(wplan, lg, voy)\n"
    "            wplan = _sanitize_served_film_plan(wplan, lg)\n"
    "            out = _with_film_estimate(wplan)",
    "sanitize written snapshot before serving",
)
store = replace_once(
    store,
    "    out = _with_film_estimate(_repair_served_hop(plan, lg, voy))",
    "    out = _with_film_estimate(_sanitize_served_film_plan(_repair_served_hop(plan, lg, voy), lg))",
    "sanitize raw snapshot before serving",
)
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
test_store_path = Path("naviguide-simulator/server/tests/test_official_store.py")
test_store = test_store_path.read_text(encoding="utf-8")
test_store += '''

def test_served_film_plan_repairs_stale_date_and_text_indices():
    """Legacy snapshot repair happens on read and does not mutate the stored plan."""
    start = "2026-08-13T22:50:23Z"
    end = "2026-08-17T08:48:38Z"
    original = {
        "source": "rules",
        "chars": 400,
        "targetSeconds": 150,
        "chapters": [{
            "id": "leg-st-pierre",
            "tA": start,
            "tB": end,
            "text": (
                "Le 23 mai, une bouée. 489 milles, trois jours de mer. "
                "Arrivée à Saint-Pierre le 17 août."
            ),
            "anchors": [
                {"charIdx": 0, "t": start},
                {"charIdx": 117, "t": "2026-08-14T23:50:23Z"},
                {"charIdx": 205, "t": end},
            ],
            "events": [{
                "id": "distance",
                "kind": "distance",
                "title": "Distance du chapitre",
                "fact": "489 milles, trois jours de mer.",
                "charIdx": 190,
                "card": {"text": "489 milles, trois jours de mer.", "at": end},
            }],
        }],
    }

    repaired = official_store._sanitize_served_film_plan(original, "fr")
    chapter = repaired["chapters"][0]

    assert "23 mai" not in chapter["text"]
    assert "489 milles" in chapter["text"]
    assert len(chapter["text"]) == repaired["chars"]
    assert all(0 <= a["charIdx"] < len(chapter["text"]) for a in chapter["anchors"])
    assert all(0 <= e["charIdx"] < len(chapter["text"]) for e in chapter["events"])
    event = chapter["events"][0]
    assert event["charIdx"] == chapter["text"].index("489 milles")
    assert "23 mai" in original["chapters"][0]["text"]
    assert original["chapters"][0]["events"][0]["charIdx"] == 190
'''
test_store_path.write_text(test_store, encoding="utf-8")

hook_test_path = Path("naviguide-simulator/src/hooks/useReplay.test.js")
hook_test = hook_test_path.read_text(encoding="utf-8")
hook_test = replace_once(
    hook_test,
    "    assert.match(hook, /shouldHoldFilmForBudget/);",
    "    assert.match(hook, /shouldHoldFilmForBudget/);\n    assert.match(hook, /linearFinish: linear.finish && !holdForSelectedBudget/);",
    "assert linear playback waits for selected duration",
)
hook_test_path.write_text(hook_test, encoding="utf-8")

store_path.write_text(store, encoding="utf-8")

print("Applied film snapshot, index, and writing-failure diagnostic patches.")
