"""Réancrage stock officiel : dry-run, sauvegarde, pas de perte de lignes moments."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import official_store
import pearl_store
import reanchor_official
from moment_journal import apply_moment_reanchor, merge_preserve_moment_rows, plan_moment_reanchor
from voyage_clock import OFFICIAL_VOYAGE_ID


@pytest.fixture
def isolated_reanchor_env(tmp_path, monkeypatch):
    store = tmp_path / "store"
    voyage = tmp_path / "voyage"
    store.mkdir()
    voyage.mkdir()
    monkeypatch.setenv("NAVIGUIDE_OFFICIAL_STORE_DIR", str(store))
    monkeypatch.setenv("NAVIGUIDE_VOYAGE_DIR", str(voyage))
    monkeypatch.setenv("NAVIGUIDE_OFFICIAL_WORKER", "0")
    official_store.reset_store()
    pearl_store.reset()
    yield store, voyage
    pearl_store.reset()
    official_store.reset_store()


def _seed_climo(_store: Path, marks: list[dict]) -> None:
    payload = {"clock": {"t0": "2026-05-15T08:00:00Z", "marks": marks, "vertices": []}}
    official_store.put("climo", payload, key="route:test:2026-05-15T08:00:00Z:2026-10-18")


def _seed_moments_sqlite(rows: list[dict]) -> None:
    pearl_store.replace_moments(OFFICIAL_VOYAGE_ID, rows)


def test_dry_run_writes_nothing(isolated_reanchor_env):
    store, _voyage = isolated_reanchor_env
    _seed_climo(store, [
        {"name": "Fort-de-France (Martinique)", "iso": "2026-09-01T00:00:00Z",
         "lat": -7.0, "lon": -118.0, "filmNm": 1000},
    ])
    _seed_moments_sqlite([
        {"seq": 1, "t": "2026-05-15T08:00:00Z", "signature": "a", "changes": [], "moment": {}, "pos": {}},
        {"seq": 2, "t": "2026-05-16T08:00:00Z", "signature": "b", "changes": [], "moment": {}, "pos": {}},
    ])
    climo_files = list(store.glob("*/climo.json"))
    assert climo_files
    climo = climo_files[0]
    before_mtime = climo.stat().st_mtime
    before_db = pearl_store.db_path().stat().st_mtime if pearl_store.db_path().is_file() else 0

    assert reanchor_official.run_reanchor(dry_run=True, backup=False) == 0

    assert climo.stat().st_mtime == before_mtime
    if before_db:
        assert pearl_store.db_path().stat().st_mtime == before_db
    assert pearl_store.count_moments(OFFICIAL_VOYAGE_ID) == 2
    plan = reanchor_official.plan_reanchor()
    assert plan.counts_before.moment_rows == 2
    assert any("plan :" in line for line in plan.summary_lines())


def test_backup_creates_timestamped_copy(isolated_reanchor_env):
    store, _voyage = isolated_reanchor_env
    _seed_climo(store, [{"name": "La Rochelle", "iso": "2026-05-15T08:00:00Z", "lat": 46.15, "lon": -1.16}])
    _seed_moments_sqlite([
        {"seq": 0, "t": "2026-05-15T08:00:00Z", "signature": "s", "changes": [], "moment": {}, "pos": {}},
    ])
    dest = reanchor_official.backup_store(backup_parent=store.parent)
    assert dest.is_dir()
    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    assert manifest.get("copied")
    assert (dest / "official-store").exists() or (dest / "naviguide.sqlite").exists()


def test_merge_preserves_rows_not_in_rebuild():
    existing = [
        {"seq": 1, "t": "2026-05-15T08:00:00Z", "signature": "a", "changes": [{"kind": "coast", "id": "c1", "tMs": 1}], "moment": {}},
        {"seq": 2, "t": "2026-05-16T08:00:00Z", "signature": "b", "changes": [], "moment": {}},
        {"seq": 3, "t": "2026-05-17T08:00:00Z", "signature": "c", "changes": [], "moment": {}},
    ]
    rebuilt = [
        {"seq": 1, "t": "2026-05-15T09:00:00Z", "signature": "a", "changes": [{"kind": "coast", "id": "c1", "tMs": 99}], "moment": {}},
    ]
    merged, kept = merge_preserve_moment_rows(existing, rebuilt)
    assert len(merged) == 3
    assert len(kept) == 2
    assert merged[0]["changes"][0]["tMs"] == 99
    assert {r["seq"] for r in merged} == {1, 2, 3}


def test_apply_moment_reanchor_never_drops_sqlite_rows(isolated_reanchor_env, monkeypatch):
    store, _voyage = isolated_reanchor_env
    _seed_climo(store, [{"name": "La Rochelle", "lat": 46.15, "lon": -1.16, "iso": "2026-05-15T08:00:00Z"}])
    rows = [
        {"seq": i, "t": f"2026-05-{10 + i}T08:00:00Z", "signature": f"s{i}",
         "changes": [{"kind": "note", "id": f"n{i}", "title": "t"}], "moment": {}, "pos": {}}
        for i in range(5)
    ]
    _seed_moments_sqlite(rows)

    def _thin_build(_vid, _voy):
        return [rows[0]]

    clock = {"t0": "2026-05-15T08:00:00Z", "marks": [], "vertices": []}
    monkeypatch.setattr("voyage_store.load_voyage", lambda _vid: {"clock": clock})
    monkeypatch.setattr("moment_journal._build_rows", _thin_build)
    out = apply_moment_reanchor(dry_run=False)
    assert out["before"] == 5
    assert out["after"] == 5
    assert out["kept"] >= 4
    assert pearl_store.count_moments(OFFICIAL_VOYAGE_ID) == 5


def test_plan_moment_reanchor_reports_preserved_rows(isolated_reanchor_env, monkeypatch):
    store, _voyage = isolated_reanchor_env
    _seed_climo(store, [{"name": "La Rochelle", "lat": 46.15, "lon": -1.16, "iso": "2026-05-15T08:00:00Z"}])
    _seed_moments_sqlite([
        {"seq": 0, "t": "2026-05-15T08:00:00Z", "signature": "s", "changes": [], "moment": {}, "pos": {}},
        {"seq": 1, "t": "2026-05-16T08:00:00Z", "signature": "t", "changes": [], "moment": {}, "pos": {}},
    ])
    clock = {"t0": "2026-05-15T08:00:00Z", "marks": [], "vertices": []}
    monkeypatch.setattr("voyage_store.load_voyage", lambda _vid: {"clock": clock})
    monkeypatch.setattr("moment_journal._build_rows", lambda _v, _y: [])
    plan = plan_moment_reanchor()
    assert plan["merged_count"] == 2
    assert plan["kept_count"] == 2
