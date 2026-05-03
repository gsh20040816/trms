from fastapi.testclient import TestClient

from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config
from trms_backend.infrastructure.database import build_session_factory, session_scope
from trms_backend.infrastructure.models import AuditLogRow, UserAccountRow

from test_tasks_api import auth_headers, register_and_get_token


def make_client(tmp_path):
    runtime_config = load_runtime_config(
        env={
            "DATABASE_URL": f"sqlite:///{tmp_path}/test.db",
            "TRMS_PUBLIC_API_BASE_URL": "http://127.0.0.1:9876/api",
            "TZ": "Asia/Shanghai",
            "TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN": "bootstrap-secret",
            "TRMS_AUTH_TELEGRAM_INBOUND_TOKEN": "telegram-secret",
            "TRMS_AUTH_EMAIL_INBOUND_TOKEN": "email-secret",
            "TRMS_LLM_API_KEY": "sk-test-secret",
            "TRMS_LLM_MODEL": "gpt-4.1-mini",
        }
    )
    return TestClient(create_app(runtime_config=runtime_config))


def system_admin_auth_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(
        register_and_get_token(
            client,
            username="sysadmin1",
            role="system_admin",
            actor_id="sysadmin-1",
            member_code=None,
        )
    )


def list_user_audit_logs(tmp_path, user_id: str) -> list[AuditLogRow]:
    session_factory = build_session_factory(f"sqlite:///{tmp_path}/test.db")
    with session_scope(session_factory) as session:
        return (
            session.query(AuditLogRow)
            .filter_by(object_type="user_account", object_id=user_id)
            .order_by(AuditLogRow.created_at)
            .all()
        )


def test_system_admin_dashboard_returns_real_config_and_runtime_summary(tmp_path):
    client = make_client(tmp_path)
    save_response = client.put(
        "/api/system/global-invoice-config",
        json={
            "invoice_title": "同济大学",
            "tax_number": "12100000425006117D",
        },
        headers=system_admin_auth_headers(client),
    )
    assert save_response.status_code == 200

    response = client.get(
        "/api/system/dashboard",
        headers=system_admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json() == {
        "service_health": "ok",
        "global_invoice_config": {
            "invoice_title": "同济大学",
            "tax_number": "12100000425006117D",
        },
        "registration_policy": {
            "allowed_email_hosts": [],
        },
        "system_ai_provider_config": {
            "text_llm": {
                "base_url": None,
                "model": None,
                "timeout_seconds": None,
                "max_retries": None,
                "api_key_configured": False,
            },
            "vlm": {
                "base_url": None,
                "model": None,
                "timeout_seconds": None,
                "max_retries": None,
                "api_key_configured": False,
            },
        },
        "runtime": {
            "environment": "development",
            "public_api_base_url": "http://127.0.0.1:9876/api",
            "system_timezone": "Asia/Shanghai",
            "async_job_mode": "in_process",
            "file_storage_backend": "local",
            "llm_provider_configured": True,
            "text_llm_provider_configured": True,
            "vlm_provider_configured": True,
            "allow_admin_self_register": True,
            "bootstrap_admin_configured": True,
            "telegram_inbound_configured": True,
            "email_inbound_configured": True,
        },
        "user_counts": {
            "member": 0,
            "admin": 0,
            "system_admin": 1,
        },
    }


def test_system_admin_can_update_registration_policy(tmp_path):
    client = make_client(tmp_path)

    response = client.put(
        "/api/system/registration-policy",
        json={
            "allowed_email_hosts": ["tongji.edu.cn", "@acm.tongji.edu.cn", "tongji.edu.cn"],
        },
        headers=system_admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json() == {
        "allowed_email_hosts": ["tongji.edu.cn", "acm.tongji.edu.cn"],
    }


def test_system_admin_can_update_global_invoice_config(tmp_path):
    client = make_client(tmp_path)

    response = client.put(
        "/api/system/global-invoice-config",
        json={
            "invoice_title": "同济大学 ACM 实验室",
            "tax_number": "91310000TEST00001",
        },
        headers=system_admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json() == {
        "invoice_title": "同济大学 ACM 实验室",
        "tax_number": "91310000TEST00001",
    }


def test_system_admin_can_update_recognition_provider_config(tmp_path):
    client = make_client(tmp_path)

    response = client.put(
        "/api/system/recognition-provider-config",
        json={
            "text_llm": {
                "base_url": "https://text.example.com/v1",
                "model": "gpt-4.1-mini",
                "timeout_seconds": 25,
                "max_retries": 1,
                "api_key": "sk-text-override",
            },
            "vlm": {
                "base_url": "https://vlm.example.com/v1",
                "model": "gpt-4.1",
                "timeout_seconds": 40,
                "max_retries": 2,
                "api_key": "sk-vlm-override",
            },
        },
        headers=system_admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json() == {
        "text_llm": {
            "base_url": "https://text.example.com/v1",
            "model": "gpt-4.1-mini",
            "timeout_seconds": 25.0,
            "max_retries": 1,
            "api_key_configured": True,
        },
        "vlm": {
            "base_url": "https://vlm.example.com/v1",
            "model": "gpt-4.1",
            "timeout_seconds": 40.0,
            "max_retries": 2,
            "api_key_configured": True,
        },
    }


def test_system_admin_can_grant_admin_role_to_existing_user_with_audit(tmp_path):
    client = make_client(tmp_path)
    member_response = client.post(
        "/api/auth/register",
        json={
            "username": "member1",
            "password": "correct-password",
            "role": "member",
            "display_name": "王队员",
            "actor_id": "2250001",
            "member_code": "2250001",
        },
    )
    assert member_response.status_code == 201
    member_user = member_response.json()["user"]

    response = client.put(
        f"/api/system/users/{member_user['id']}/roles/admin",
        headers=system_admin_auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "admin"
    assert body["already_assigned"] is False
    assert body["user"]["id"] == member_user["id"]
    assert body["user"]["username"] == "member1"
    assert body["user"]["role"] == "member"
    assert body["user"]["roles"] == ["member", "admin"]
    assert body["user"]["actor_id"] == "2250001"
    assert body["user"]["display_name"] == "王队员"
    assert body["user"]["member_code"] == "2250001"

    session_factory = build_session_factory(f"sqlite:///{tmp_path}/test.db")
    with session_scope(session_factory) as session:
        user_row = session.get(UserAccountRow, member_user["id"])
        assert user_row is not None
        assert user_row.role == "member"
        assert user_row.roles == ["member", "admin"]

    audit_logs = list_user_audit_logs(tmp_path, member_user["id"])
    assert len(audit_logs) == 1
    assert audit_logs[0].actor_id == "sysadmin-1"
    assert audit_logs[0].action == "grant_user_role"
    assert audit_logs[0].result == "succeeded"
    assert audit_logs[0].request_id.startswith("req_")
    assert audit_logs[0].detail == {
        "user_id": member_user["id"],
        "username": "member1",
        "granted_role": "admin",
        "already_assigned": False,
    }


def test_system_admin_can_search_existing_users(tmp_path):
    client = make_client(tmp_path)
    member_response = client.post(
        "/api/auth/register",
        json={
            "username": "member1",
            "password": "correct-password",
            "role": "member",
            "display_name": "王队员",
            "actor_id": "2250001",
            "member_code": "2250001",
        },
    )
    assert member_response.status_code == 201

    response = client.get(
        "/api/system/users/search?keyword=member1&limit=10",
        headers=system_admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": member_response.json()["user"]["id"],
                "actor_id": "2250001",
                "username": "member1",
                "display_name": "王队员",
                "student_id": "2250001",
                "roles": ["member"],
            }
        ]
    }


def test_system_admin_grant_admin_role_is_idempotent(tmp_path):
    client = make_client(tmp_path)
    member_response = client.post(
        "/api/auth/register",
        json={
            "username": "member1",
            "password": "correct-password",
            "role": "member",
            "display_name": "王队员",
            "actor_id": "2250001",
            "member_code": "2250001",
        },
    )
    assert member_response.status_code == 201
    member_user = member_response.json()["user"]

    first_response = client.put(
        f"/api/system/users/{member_user['id']}/roles/admin",
        headers=system_admin_auth_headers(client),
    )
    assert first_response.status_code == 200

    response = client.put(
        f"/api/system/users/{member_user['id']}/roles/admin",
        headers=system_admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["already_assigned"] is True
    assert response.json()["user"]["roles"] == ["member", "admin"]

    audit_logs = list_user_audit_logs(tmp_path, member_user["id"])
    assert len(audit_logs) == 2
    assert audit_logs[0].detail["already_assigned"] is False
    assert audit_logs[1].detail["already_assigned"] is True


def test_system_admin_dashboard_rejects_plain_admin(tmp_path):
    client = make_client(tmp_path)
    admin_headers = auth_headers(
        register_and_get_token(
            client,
            username="admin1",
            role="admin",
            actor_id="admin-1",
            member_code=None,
        )
    )

    response = client.get("/api/system/dashboard", headers=admin_headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to manage system settings"


def test_system_admin_role_grant_rejects_plain_admin(tmp_path):
    client = make_client(tmp_path)
    target_response = client.post(
        "/api/auth/register",
        json={
            "username": "member1",
            "password": "correct-password",
            "role": "member",
            "display_name": "王队员",
            "actor_id": "2250001",
            "member_code": "2250001",
        },
    )
    assert target_response.status_code == 201
    target_user_id = target_response.json()["user"]["id"]
    admin_headers = auth_headers(
        register_and_get_token(
            client,
            username="admin1",
            role="admin",
            actor_id="admin-1",
            member_code=None,
        )
    )

    response = client.put(
        f"/api/system/users/{target_user_id}/roles/admin",
        headers=admin_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to manage system settings"


def test_system_admin_update_rejects_member(tmp_path):
    client = make_client(tmp_path)
    member_headers = auth_headers(
        register_and_get_token(
            client,
            username="member1",
            role="member",
            actor_id="2250001",
            member_code="2250001",
        )
    )

    response = client.put(
        "/api/system/global-invoice-config",
        json={
            "invoice_title": "同济大学",
            "tax_number": "12100000425006117D",
        },
        headers=member_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to manage system settings"


def test_system_admin_recognition_provider_update_rejects_member(tmp_path):
    client = make_client(tmp_path)
    member_headers = auth_headers(
        register_and_get_token(
            client,
            username="member1",
            role="member",
            actor_id="2250001",
            member_code="2250001",
        )
    )

    response = client.put(
        "/api/system/recognition-provider-config",
        json={"text_llm": {}, "vlm": {}},
        headers=member_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to manage system settings"
