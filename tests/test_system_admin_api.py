from fastapi.testclient import TestClient

from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from test_tasks_api import auth_headers, register_and_get_token


def make_client(tmp_path):
    runtime_config = load_runtime_config(
        env={
            "DATABASE_URL": f"sqlite:///{tmp_path}/test.db",
            "TRMS_PUBLIC_API_BASE_URL": "http://127.0.0.1:9876/api",
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
        "runtime": {
            "environment": "development",
            "public_api_base_url": "http://127.0.0.1:9876/api",
            "async_job_mode": "in_process",
            "file_storage_backend": "local",
            "llm_provider_configured": True,
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
