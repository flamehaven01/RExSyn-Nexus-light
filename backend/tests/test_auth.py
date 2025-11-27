from app.services import auth_service


def test_jwt_secret_loaded():
    assert auth_service.SECRET_KEY is not None
    assert len(auth_service.SECRET_KEY) > 0


def test_access_token_creation_and_decode():
    payload = {
        "user_id": "u1",
        "username": "demo",
        "email": "demo@example.com",
        "role": "admin",
        "org_id": "org1",
    }
    token = auth_service.create_access_token(payload)
    decoded = auth_service.decode_token(token)
    assert decoded is not None
    assert decoded.user_id == "u1"


def test_refresh_token_creation():
    payload = {
        "user_id": "u2",
        "username": "demo2",
        "email": "demo2@example.com",
        "role": "viewer",
        "org_id": "org1",
    }
    token = auth_service.create_refresh_token(payload)
    assert isinstance(token, str)
