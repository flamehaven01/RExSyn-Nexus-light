from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.core.settings import settings


client = TestClient(app)


@pytest.fixture
def token():
    payload = {
        "sub": "user-1",
        "org": "org-1",
        "roles": ["admin"],
        "perms": ["predict:create", "predict:read"],
        "aud": settings.JWT_AUD,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm="HS256",
        headers={"kid": "local"},
    )


def test_predict_success(token, monkeypatch):
    class _DummyTask:
        def delay(self, **kwargs):
            return None

    monkeypatch.setattr("app.api.v1.predict.run_structure_prediction", _DummyTask())

    resp = client.post(
        "/api/v1/predict",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "sequence": "ACDEFGHIKLMNPQRSTVWY",
            "experiment_type": "protein_folding",
            "method": "alphafold3",
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert data["job_id"].startswith("exp-")


def test_predict_invalid_sequence(token):
    resp = client.post(
        "/api/v1/predict",
        headers={"Authorization": f"Bearer {token}"},
        json={"sequence": "12345", "experiment_type": "protein_folding", "method": "alphafold3"},
    )
    assert resp.status_code == 422


def test_predict_unauthorized():
    resp = client.post(
        "/api/v1/predict",
        json={"sequence": "ACDEFGHIKLMNPQRSTVWY", "experiment_type": "protein_folding", "method": "alphafold3"},
    )
    assert resp.status_code == 401


def test_status_not_found(token):
    resp = client.get(
        "/api/v1/jobs/exp-missing/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_result_not_found(token):
    resp = client.get(
        "/api/v1/jobs/exp-missing/result",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_auth_invalid_token():
    resp = client.post(
        "/api/v1/predict",
        headers={"Authorization": "Bearer invalid"},
        json={"sequence": "ACDEFGHIKLMNPQRSTVWY", "experiment_type": "protein_folding", "method": "alphafold3"},
    )
    assert resp.status_code == 401
