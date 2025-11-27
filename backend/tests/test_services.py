import os

from app.services.peer_review_service import PeerReviewService
from app.main import app
from app.core import settings


def test_peer_review_service_stub_instantiation():
    # LIGHT mode should allow stub engine without external deps
    os.environ["RSN_LIGHT_MODE"] = "1"
    svc = PeerReviewService(redis_url="redis://localhost:6379/0")
    assert svc is not None


def test_settings_defaults_sqlite():
    assert settings.settings.DB_URL.startswith("sqlite:///")


def test_rate_limiter_present():
    assert hasattr(app.state, "limiter")


def test_placeholder_pipeline_flag():
    assert os.getenv("ALLOW_PLACEHOLDER_PIPELINE", "1") == "1"


def test_metrics_router_mounted():
    routes = [r.path for r in app.routes]
    assert "/metrics" in routes


def test_health_services_keys_present():
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get("/health")
    body = resp.json()
    assert "services" in body
    assert set(body["services"].keys()) >= {"database", "redis", "minio"}
