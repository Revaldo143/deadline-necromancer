from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_health_shape():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["model"] == settings.MODEL
    assert "ollama_reachable" in body
    assert "default_scan_path" in body


def test_scan_default_path(make_repo, tmp_path, monkeypatch):
    make_repo("default-corpse")
    monkeypatch.setattr(settings, "DEFAULT_SCAN_PATH", str(tmp_path))
    resp = client.post("/api/scan", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert "projects" in body
    assert len(body["projects"]) == 1


def test_scan_finds_repos(make_repo, tmp_path):
    make_repo("corpse-one")
    resp = client.post("/api/scan", json={"path": str(tmp_path)})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["projects"]) == 1
    assert body["projects"][0]["name"] == "corpse-one"


def test_scan_missing_path_is_404(tmp_path):
    resp = client.post("/api/scan", json={"path": str(tmp_path / "nope")})
    assert resp.status_code == 404


def test_resurrect_returns_a_plan(make_repo, tmp_path, monkeypatch):
    from app.core import necromancer

    monkeypatch.setattr(necromancer, "ollama_status", lambda: (False, None))
    repo = make_repo("risen")
    resp = client.post("/api/resurrect", json={"path": str(repo)})
    assert resp.status_code == 200
    body = resp.json()
    assert body["project"]["name"] == "risen"
    # No Ollama in the test environment — the fallback must carry the demo.
    assert body["plan"]["mode"] == "fallback"
    assert len(body["plan"]["steps"]) >= 3
    assert body["hours_saved"] > 0


def test_resurrect_rejects_non_repo(tmp_path):
    resp = client.post("/api/resurrect", json={"path": str(tmp_path)})
    assert resp.status_code == 404


def test_frontend_is_served():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Necromancer" in resp.text
