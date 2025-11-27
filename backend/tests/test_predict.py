from fastapi.testclient import TestClient

from app.main import app
from app.core import settings


client = TestClient(app)


def test_placeholder_pipeline_default():
    assert settings.settings.SCIENCE_MODE == "placeholder"


def test_db_url_uses_sqlite_by_default():
    assert settings.settings.DB_URL.startswith("sqlite:///")


def test_health_returns_status_and_services():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "services" in body
    assert set(body["services"].keys()) >= {"database", "redis", "minio"}


def test_ui_redirect_present():
    resp = client.get("/ui", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "/frontend/landing/home/code.html" in resp.headers.get("location", "")


def test_predict_rejects_too_long_sequence():
    long_seq = "A" * 10001  # over max_length
    resp = client.post(
        "/api/v1/predict",
        json={
            "sequence": long_seq,
            "experiment_type": "protein_folding",
            "method": "alphafold3"
        },
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code in (401, 422)


def test_root_contains_links():
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("health") == "/health"
    assert body.get("metrics") == "/metrics"


def test_rate_limit_enabled_on_app_state():
    assert hasattr(app.state, "limiter")


def test_docs_available():
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_redoc_available():
    resp = client.get("/redoc")
    assert resp.status_code == 200


def test_openapi_available():
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json().get("info", {}).get("title") == "RExSyn Nexus API"
