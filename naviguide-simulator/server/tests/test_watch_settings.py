"""R42 : interrupteur « Veille Tavily » — réglage persistant, effet réel sur watch_enabled()."""
from fastapi.testclient import TestClient

import escale_watch


def _client():
    import main  # noqa: PLC0415
    return TestClient(main.app)


def test_default_follows_env(monkeypatch):
    monkeypatch.delenv("NAVIGUIDE_TAVILY_WATCH", raising=False)
    assert escale_watch.watch_settings() == {"enabled": True, "default": True, "source": "env"}
    monkeypatch.setenv("NAVIGUIDE_TAVILY_WATCH", "0")
    assert escale_watch.watch_enabled() is False


def test_toggle_persists_and_drives_watch_enabled(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_TAVILY_WATCH", "1")
    c = _client()
    assert c.get("/escale/watch/settings").json()["enabled"] is True
    r = c.post("/escale/watch/settings", json={"enabled": False})
    assert r.status_code == 200 and r.json() == {"enabled": False, "default": True, "source": "setting"}
    assert escale_watch.watch_enabled() is False
    # Persistant : relu depuis pearl_store, pas d'un état en mémoire de la requête.
    assert escale_watch.watch_override() is False
    assert c.get("/escale/watch/settings").json()["enabled"] is False
    r = c.post("/escale/watch/settings", json={"enabled": True})
    assert r.json()["enabled"] is True and escale_watch.watch_enabled() is True


def test_off_means_zero_search(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_TAVILY_WATCH", "1")
    escale_watch.set_watch_override(False)
    import escale_api  # noqa: PLC0415
    called = []
    monkeypatch.setattr(escale_watch, "official_stop_in_window", lambda *a, **k: called.append(1))
    escale_api._schedule_escale_watch("Nouméa", -22.27, 166.44)
    assert called == []


def test_post_rejects_non_bool_and_requires_admin(monkeypatch):
    c = _client()
    assert c.post("/escale/watch/settings", json={"enabled": "yes"}).status_code == 400
    monkeypatch.setenv("NAVIGUIDE_ADMIN_SECRET", "s3")
    assert c.post("/escale/watch/settings", json={"enabled": False}).status_code == 401
    ok = c.post("/escale/watch/settings", json={"enabled": False}, headers={"X-Naviguide-Admin": "s3"})
    assert ok.status_code == 200
