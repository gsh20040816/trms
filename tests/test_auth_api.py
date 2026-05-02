from alembic import command
from fastapi.testclient import TestClient

from trms_backend.infrastructure.database import (
    build_alembic_config,
    build_session_factory,
    session_scope,
)
from trms_backend.infrastructure.models import UserAccountRow
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from api_error_assertions import assert_api_error


def make_client(tmp_path, runtime_config=None):
    if runtime_config is not None and runtime_config.environment == "production":
        command.upgrade(build_alembic_config(runtime_config.database_url), "head")
    if runtime_config is not None:
        return TestClient(create_app(runtime_config=runtime_config))
    return TestClient(create_app(f"sqlite:///{tmp_path}/test.db"))


def make_production_runtime_config(tmp_path, **overrides):
    return load_runtime_config(
        env={
            "TRMS_ENV": "production",
            "DATABASE_URL": f"sqlite:///{tmp_path}/production.db",
            "TRMS_STORAGE_BACKEND": "s3",
            "TRMS_STORAGE_S3_ENDPOINT": "https://minio.example.com",
            "TRMS_STORAGE_S3_BUCKET": "trms-prod",
            "TRMS_STORAGE_S3_ACCESS_KEY_ID": "prod-access",
            "TRMS_STORAGE_S3_SECRET_ACCESS_KEY": "prod-secret",
            "TRMS_CORS_ALLOWED_ORIGINS": "https://trms.example.edu",
            "TRMS_PUBLIC_API_BASE_URL": "https://trms.example.edu/api",
            "TRMS_API_HOST": "0.0.0.0",
            "TRMS_API_PORT": "8000",
        }
        | overrides
    )


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
        "roles": ["member"],
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

    assert_api_error(
        response,
        status_code=409,
        code="conflict",
        detail="username already exists: member1",
    )


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


def test_member_can_update_own_profile(tmp_path):
    client = make_client(tmp_path)
    register_response = client.post("/api/auth/register", json=register_payload())
    token = register_response.json()["access_token"]

    response = client.put(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "display_name": "新名字",
            "member_code": "2250999",
        },
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "新名字"
    assert response.json()["member_code"] == "2250999"


def test_admin_profile_update_rejects_member_code_change(tmp_path):
    client = make_client(tmp_path)
    register_response = client.post(
        "/api/auth/register",
        json=register_payload(
            username="admin1",
            role="admin",
            display_name="张管理员",
            actor_id="admin-1",
            member_code=None,
        ),
    )
    token = register_response.json()["access_token"]

    response = client.put(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "display_name": "新管理员",
            "member_code": "ADMIN-001",
        },
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="member_code can only be updated by member accounts",
    )


def test_profile_update_rejects_blank_display_name(tmp_path):
    client = make_client(tmp_path)
    register_response = client.post("/api/auth/register", json=register_payload())
    token = register_response.json()["access_token"]

    response = client.put(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "display_name": "   ",
            "member_code": "2250001",
        },
    )

    assert response.status_code == 422


def test_member_can_change_password_and_login_with_new_password(tmp_path):
    client = make_client(tmp_path)
    register_response = client.post("/api/auth/register", json=register_payload())
    token = register_response.json()["access_token"]

    response = client.put(
        "/api/auth/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "correct-password",
            "new_password": "new-password-123",
        },
    )

    assert response.status_code == 204

    old_login_response = client.post(
        "/api/auth/login",
        json={"username": "member1", "password": "correct-password"},
    )
    assert_api_error(
        old_login_response,
        status_code=401,
        code="unauthorized",
        detail="invalid username or password",
    )

    new_login_response = client.post(
        "/api/auth/login",
        json={"username": "member1", "password": "new-password-123"},
    )
    assert new_login_response.status_code == 200


def test_password_change_rejects_incorrect_current_password(tmp_path):
    client = make_client(tmp_path)
    register_response = client.post("/api/auth/register", json=register_payload())
    token = register_response.json()["access_token"]

    response = client.put(
        "/api/auth/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "wrong-password",
            "new_password": "new-password-123",
        },
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="current password is incorrect",
    )


def test_request_context_returns_anonymous_identity_without_bearer_token(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/auth/request-context")

    assert response.status_code == 200
    assert response.json() == {
        "is_authenticated": False,
        "source": "anonymous",
        "role": None,
        "available_roles": [],
        "actor_id": None,
        "member_id": None,
        "user": None,
    }


def test_request_context_returns_authenticated_identity_with_member_mapping(tmp_path):
    client = make_client(tmp_path)
    register_response = client.post("/api/auth/register", json=register_payload())
    token = register_response.json()["access_token"]

    response = client.get(
        "/api/auth/request-context",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "is_authenticated": True,
        "source": "bearer",
        "role": "member",
        "available_roles": ["member"],
        "actor_id": "2250001",
        "member_id": "MEM-001",
        "user": {
            "id": register_response.json()["user"]["id"],
            "username": "member1",
            "role": "member",
            "roles": ["member"],
            "actor_id": "2250001",
            "display_name": "王队员",
            "member_code": "MEM-001",
            "created_at": register_response.json()["user"]["created_at"],
            "updated_at": register_response.json()["user"]["updated_at"],
        },
    }


def test_login_rejects_wrong_password_without_exposing_hash(tmp_path):
    client = make_client(tmp_path)
    assert client.post("/api/auth/register", json=register_payload()).status_code == 201

    response = client.post(
        "/api/auth/login",
        json={"username": "member1", "password": "wrong-password"},
    )

    assert_api_error(
        response,
        status_code=401,
        code="unauthorized",
        detail="invalid username or password",
    )
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


def test_production_register_rejects_admin_self_registration(tmp_path):
    client = make_client(tmp_path, runtime_config=make_production_runtime_config(tmp_path))

    response = client.post(
        "/api/auth/register",
        json=register_payload(role="admin", actor_id="admin-1", member_code=None),
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="self-service registration for role 'admin' is disabled",
    )


def test_production_register_still_allows_member_self_registration(tmp_path):
    client = make_client(tmp_path, runtime_config=make_production_runtime_config(tmp_path))

    response = client.post("/api/auth/register", json=register_payload())

    assert response.status_code == 201
    assert response.json()["user"]["role"] == "member"
    assert response.json()["user"]["roles"] == ["member"]


def test_bootstrap_admin_creates_privileged_account_and_records_audit_source(tmp_path):
    runtime_config = make_production_runtime_config(
        tmp_path,
        TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN=" bootstrap-secret ",
    )
    client = make_client(tmp_path, runtime_config=runtime_config)

    response = client.post(
        "/api/auth/bootstrap-admin",
        headers={"X-TRMS-Bootstrap-Token": "bootstrap-secret"},
        json=register_payload(
            username="sysadmin1",
            role="system_admin",
            display_name="赵系统管理员",
            actor_id="sysadmin-1",
            member_code=None,
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "system_admin"
    assert body["user"]["roles"] == ["system_admin"]

    session_factory = build_session_factory(f"sqlite:///{tmp_path}/production.db")
    with session_scope(session_factory) as session:
        row = session.query(UserAccountRow).filter_by(username="sysadmin1").one()
        assert row.registration_source == "bootstrap_token"
        assert row.created_by_user_id is None


def test_bootstrap_admin_rejects_second_privileged_bootstrap(tmp_path):
    runtime_config = make_production_runtime_config(
        tmp_path,
        TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN="bootstrap-secret",
    )
    client = make_client(tmp_path, runtime_config=runtime_config)
    payload = register_payload(
        username="sysadmin1",
        role="system_admin",
        display_name="赵系统管理员",
        actor_id="sysadmin-1",
        member_code=None,
    )

    assert client.post(
        "/api/auth/bootstrap-admin",
        headers={"X-TRMS-Bootstrap-Token": "bootstrap-secret"},
        json=payload,
    ).status_code == 201

    response = client.post(
        "/api/auth/bootstrap-admin",
        headers={"X-TRMS-Bootstrap-Token": "bootstrap-secret"},
        json=register_payload(
            username="sysadmin1",
            role="system_admin",
            display_name="赵系统管理员",
            actor_id="sysadmin-1",
            member_code=None,
        ),
    )

    payload = assert_api_error(
        response,
        status_code=409,
        code="conflict",
    )
    assert "bootstrap is already completed" in payload["detail"]


def test_bootstrap_admin_rejects_plain_admin_role(tmp_path):
    runtime_config = make_production_runtime_config(
        tmp_path,
        TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN="bootstrap-secret",
    )
    client = make_client(tmp_path, runtime_config=runtime_config)

    response = client.post(
        "/api/auth/bootstrap-admin",
        headers={"X-TRMS-Bootstrap-Token": "bootstrap-secret"},
        json=register_payload(
            username="admin1",
            role="admin",
            display_name="张管理员",
            actor_id="admin-1",
            member_code=None,
        ),
    )

    assert_api_error(
        response,
        status_code=400,
        code="bad_request",
        detail="bootstrap endpoint only supports 'system_admin', got 'admin'",
    )


def test_login_returns_available_roles_for_multi_role_account(tmp_path):
    client = make_client(tmp_path)

    register_response = client.post(
        "/api/auth/register",
        json=register_payload(
            role="member",
            actor_id="hybrid-1",
            member_code="MEM-001",
        ),
    )

    assert register_response.status_code == 201
    user = register_response.json()["user"]
    sysadmin_response = client.post(
        "/api/auth/register",
        json=register_payload(
            username="sysadmin1",
            role="system_admin",
            display_name="赵系统管理员",
            actor_id="sysadmin-1",
            member_code=None,
        ),
    )
    assert sysadmin_response.status_code == 201
    sysadmin_token = sysadmin_response.json()["access_token"]
    grant_response = client.put(
        f"/api/system/users/{user['id']}/roles/admin",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert grant_response.status_code == 200
    assert grant_response.json()["user"]["roles"] == ["member", "admin"]

    login_response = client.post(
        "/api/auth/login",
        json={"username": "member1", "password": "correct-password"},
    )

    assert login_response.status_code == 200
    assert login_response.json()["user"]["role"] == "member"
    assert login_response.json()["user"]["roles"] == ["member", "admin"]


def test_switch_role_updates_active_role_for_current_session(tmp_path):
    client = make_client(tmp_path)
    register_response = client.post(
        "/api/auth/register",
        json=register_payload(
            role="member",
            actor_id="hybrid-1",
            member_code="MEM-001",
        ),
    )
    assert register_response.status_code == 201
    user = register_response.json()["user"]
    sysadmin_response = client.post(
        "/api/auth/register",
        json=register_payload(
            username="sysadmin1",
            role="system_admin",
            display_name="赵系统管理员",
            actor_id="sysadmin-1",
            member_code=None,
        ),
    )
    assert sysadmin_response.status_code == 201
    grant_response = client.put(
        f"/api/system/users/{user['id']}/roles/admin",
        headers={"Authorization": f"Bearer {sysadmin_response.json()['access_token']}"},
    )
    assert grant_response.status_code == 200
    token = register_response.json()["access_token"]

    response = client.post(
        "/api/auth/switch-role",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "admin"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == token
    assert response.json()["user"]["role"] == "admin"
    assert response.json()["user"]["roles"] == ["member", "admin"]

    request_context_response = client.get(
        "/api/auth/request-context",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert request_context_response.status_code == 200
    assert request_context_response.json()["role"] == "admin"
    assert request_context_response.json()["available_roles"] == ["member", "admin"]


def test_switch_role_rejects_unassigned_role(tmp_path):
    client = make_client(tmp_path)
    register_response = client.post("/api/auth/register", json=register_payload())
    token = register_response.json()["access_token"]

    response = client.post(
        "/api/auth/switch-role",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "admin"},
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="role 'admin' is not assigned to this account",
    )


def test_production_register_rejects_privileged_role_in_role_set(tmp_path):
    client = make_client(tmp_path, runtime_config=make_production_runtime_config(tmp_path))

    response = client.post(
        "/api/auth/register",
        json=register_payload(
            role="member",
            roles=["member", "admin"],
        ),
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="self-service registration for role 'admin' is disabled",
    )


def test_register_rejects_multi_role_self_service_payload_in_development(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/auth/register",
        json=register_payload(
            roles=["member", "admin"],
        ),
    )

    assert_api_error(
        response,
        status_code=400,
        code="bad_request",
        detail="self-service registration only supports a single role",
    )
