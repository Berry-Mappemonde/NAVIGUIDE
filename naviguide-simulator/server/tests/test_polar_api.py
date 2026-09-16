import json

import polar_api


def test_client_polar_payload_reuses_stored_raw_without_grid(tmp_path, monkeypatch):
    monkeypatch.setattr(polar_api, "POLAR_DATA_DIR", tmp_path)
    path = polar_api._polar_path("berry-mappemonde-2026")
    path.write_text(json.dumps({
        "expedition_id": "berry-mappemonde-2026",
        "boat_name": "Leopard 46",
        "created_at": "2026-09-16T00:00:00Z",
        "grid_shape": [181, 61],
        "raw": {"twa_rows": [0, 180], "tws_cols": [6], "matrix": [[0], [8]]},
        "grid": [[0] * 61] * 181,
        "vmg_summary": {"6": {"upwind": {}, "downwind": {}, "gybe_angle": 120}},
    }), encoding="utf-8")

    payload = polar_api.get_polar_client("berry-mappemonde-2026")

    assert payload["raw"]["twa_rows"] == [0, 180]
    assert payload["vmg_summary"]["6"]["gybe_angle"] == 120
    assert "grid" not in payload
