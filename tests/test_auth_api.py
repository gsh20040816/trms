from fastapi.testclient import TestClient

from trms_backend.infrastructure.database import build_session_factory, session_scope
from trms_backend.infrastructure.models import UserAccountRow
from trms_backend.main import create_app


def make_client(tmp_path):
    return TestClient(create_app(f"sqlite:///{tmp_path}/test.db"))


def register_payload(**overrides):
    return {
        "username": "member1",
        "password": "correct-password",
        "role": "member",
        "display_name": "王队员",
        "actor_id": "2250001",
        "member_code": "MEM-001",
    } | overrides


def test_register_creates_user_and_returns_bearer_session(tmp_path):
    client = make_client(tmp_path)

    response = client.post("/api/auth/register", json=register_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"] == {
        "id": body["user"]["id"],
        "username": "member1",
        "role": "member",
        "actor_id": "2250001",
        "display_name": "王队员",
        "member_code": "MEM-001",
        "created_at": body["user"]["created_at"],
        "updated_at": body["user"]["updated_at"],
    }

    session_factory = build_session_factory(f"sqlite:///{tmp_path}/test.db")
    with session_scope(session_factory) as session:
        row = session.query(UserAccountRow).filter_by(username="member1").one()
        assert row.password_hash != "correct-password"
        assert row.password_hash.startswith("pbkdf2_sha256$")


def test_register_rejects_duplicate_username(tmp_path):
    client = make_client(tmp_path)
    assert client.post("/api/auth/register", json=register_payload()).status_code == 201

    response = client.post("/api/auth/register", json=register_payload())

    assert response.status_code == 409
    assert response.json()["detail"] == "username already exists: member1"


def test_login_returns_new_session_and_me_resolves_token(tmp_path):
    client = make_client(tmp_path)
    assert client.post("/api/auth/register", json=register_payload()).status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={"username": "member1", "password": "correct-password"},
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "member1"
    assert me_response.json()["actor_id"] == "2250001"


def test_login_rejects_wrong_password_without_exposing_hash(tmp_path):
    client = make_client(tmp_path)
    assert client.post("/api/auth/register", json=register_payload()).status_code == 201

    response = client.post(
        "/api/auth/login",
        json={"username": "member1", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid username or password"
    assert "pbkdf2" not in response.text


def test_logout_revokes_current_token(tmp_path):
    client = make_client(tmp_path)
    register_response = client.post("/api/auth/register", json=register_payload())
    token = register_response.json()["access_token"]

    logout_response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert logout_response.status_code == 204
    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 401
