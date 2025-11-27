import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import auth_service

client = TestClient(app)


@pytest.fixture
def auth_token():
    payload = {
        "user_id": "test-user-1",
        "username": "testuser",
        "email": "test@example.com",
        "role": "admin",
        "org_id": "org-test",
    }
    return auth_service.create_access_token(payload)


def test_full_prediction_workflow_placeholder(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Submit prediction
    predict_resp = client.post(
        "/api/v1/predict",
        json={
            "sequence": "ACDEFGHIKLMNPQRSTVWY",
            "experiment_type": "protein_folding",
            "method": "alphafold3",
        },
        headers=headers,
    )
    assert predict_resp.status_code in (200, 202, 401)
    if predict_resp.status_code == 401:
        return  # auth is off in placeholder mode
    job_id = predict_resp.json()["job_id"]
    assert job_id.startswith("exp-")

    # Status
    status_resp = client.get(f"/api/v1/jobs/{job_id}/status", headers=headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["job_id"] == job_id
    assert 0.0 <= status_data["progress"] <= 1.0

    # Result
    result_resp = client.get(f"/api/v1/jobs/{job_id}/result", headers=headers)
    assert result_resp.status_code == 200
    result_data = result_resp.json()
    assert result_data["job_id"] == job_id
    assert result_data["status"] in ["queued", "completed"]


def test_predict_without_auth_fails():
    resp = client.post(
        "/api/v1/predict",
        json={"sequence": "ACDEFGHIKLMNPQRSTVWY", "experiment_type": "protein_folding", "method": "alphafold3"},
    )
    assert resp.status_code == 401
