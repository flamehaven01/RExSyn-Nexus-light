from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_returns_status():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "services" in body


def test_openapi_available():
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json().get("info", {}).get("title") == "RExSyn Nexus API"
