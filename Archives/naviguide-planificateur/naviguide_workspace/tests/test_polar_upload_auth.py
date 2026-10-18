"""L'upload de polaire du service historique (9004) exige le droit admin.

Les tests écrivent dans un dossier temporaire : jamais dans polar_data/.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
ROOT = WORKSPACE.parent
CSV = ROOT / "naviguide-app" / "public" / "Leopard46_Standard_Sails.csv"
SECRET = "test-admin-secret"


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.syspath_prepend(str(WORKSPACE))
    sys.modules.pop("polar_api.main", None)
    main = importlib.import_module("polar_api.main")
    data_dir = tmp_path / "polar_data"
    data_dir.mkdir()
    monkeypatch.setattr(main, "POLAR_DATA_DIR", data_dir)
    from fastapi.testclient import TestClient

    return main, TestClient(main.app), data_dir


def _form():
    return {
        "files": {"file": ("Leopard46_Standard_Sails.csv", CSV.read_bytes(), "text/csv")},
        "data": {"expedition_id": "berry-mappemonde-2026", "boat_name": "Leopard 46"},
    }


PROXY = {"X-Real-IP": "203.0.113.7", "X-Forwarded-For": "203.0.113.7"}


def test_upload_without_key_is_refused(api, monkeypatch):
    main, client, data_dir = api
    monkeypatch.setenv("NAVIGUIDE_ADMIN_SECRET", SECRET)
    r = client.post("/api/v1/polar/upload", headers=PROXY, **_form())
    assert r.status_code == 401
    assert list(data_dir.iterdir()) == []


def test_upload_with_wrong_key_is_refused(api, monkeypatch):
    main, client, data_dir = api
    monkeypatch.setenv("NAVIGUIDE_ADMIN_SECRET", SECRET)
    r = client.post(
        "/api/v1/polar/upload",
        headers={**PROXY, "X-Naviguide-Admin": "wrong"},
        **_form(),
    )
    assert r.status_code == 401
    assert list(data_dir.iterdir()) == []


def test_upload_behind_proxy_without_configured_secret_is_closed(api, monkeypatch):
    main, client, data_dir = api
    monkeypatch.delenv("NAVIGUIDE_ADMIN_SECRET", raising=False)
    r = client.post("/api/v1/polar/upload", headers=PROXY, **_form())
    assert r.status_code == 503
    assert list(data_dir.iterdir()) == []


def test_refused_upload_keeps_existing_polar(api, monkeypatch):
    main, client, data_dir = api
    monkeypatch.setenv("NAVIGUIDE_ADMIN_SECRET", SECRET)
    stored = data_dir / "polar_berry-mappemonde-2026.json"
    original = json.dumps({"expedition_id": "berry-mappemonde-2026", "marker": "keep"})
    stored.write_text(original, encoding="utf-8")
    r = client.post("/api/v1/polar/upload", headers=PROXY, **_form())
    assert r.status_code == 401
    assert stored.read_text(encoding="utf-8") == original


def test_admin_upload_is_accepted(api, monkeypatch):
    main, client, data_dir = api
    monkeypatch.setenv("NAVIGUIDE_ADMIN_SECRET", SECRET)
    r = client.post(
        "/api/v1/polar/upload",
        headers={**PROXY, "X-Naviguide-Admin": SECRET},
        **_form(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["expedition_id"] == "berry-mappemonde-2026"
    assert body["grid_shape"] == [181, 61]
    assert (data_dir / "polar_berry-mappemonde-2026.json").exists()


def test_read_routes_stay_public(api, monkeypatch):
    main, client, data_dir = api
    monkeypatch.setenv("NAVIGUIDE_ADMIN_SECRET", SECRET)
    r = client.post(
        "/api/v1/polar/upload",
        headers={**PROXY, "X-Naviguide-Admin": SECRET},
        **_form(),
    )
    assert r.status_code == 200, r.text
    full = client.get("/api/v1/polar/berry-mappemonde-2026", headers=PROXY)
    assert full.status_code == 200
    summary = client.get("/api/v1/polar/berry-mappemonde-2026/summary", headers=PROXY)
    assert summary.status_code == 200
    assert set(summary.json()) >= {"expedition_id", "boat_name", "grid_shape", "vmg_summary", "created_at"}
