from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "naviguide-simulator"


def test_polar_chat_is_404():
    r = client.post("/api/v1/polar/chat")
    assert r.status_code == 404


def test_agents_are_404():
    r = client.post("/agents/meteo")
    assert r.status_code == 404
