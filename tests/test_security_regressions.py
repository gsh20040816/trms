import pytest
from fastapi.testclient import TestClient

from trms_backend.domain.audit_logs import (
    AuditLogCreate,
    AuditLogResult,
    REDACTED_AUDIT_VALUE,
)
from trms_backend.logging_safety import (
    REDACTED_LOG_PATH,
    REDACTED_LOG_VALUE,
    sanitize_log_fields,
)
from trms_backend.main import create_app
from trms_backend.runtime_config import RuntimeConfigError, load_runtime_config

from api_error_assertions import assert_api_error
from test_auth_api import (
    make_client as make_auth_client,
    make_production_runtime_config,
    register_payload,
)
from test_export_async_jobs import (
    build_processor,
    create_task as create_export_task,
    make_client as make_export_client,
    make_runtime_config,
    outsider_admin_auth_headers,
)
from test_exports_api import create_export_job, create_invoice_with_splits
from test_permission_regressions import create_permission_fixture, member_auth_headers
from test_tasks_api import admin_auth_headers, update_task_row


def test_security_regression_blocks_member_overreach_on_sensitive_paths(tmp_path):
    client, task_id, material_id, _, _ = create_permission_fixture(tmp_path)

    material_response = client.get(
        f"/api/materials/{material_id}/content",
        headers=member_auth_headers(client, username="member2", actor_id="2250002"),
    )
    assert_api_error(
        material_response,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to view this material content",
    )

    review_response = client.get(
        f"/api/tasks/{task_id}/review-summary",
        params={"actor_id": "2250001"},
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )
    assert_api_error(
        review_response,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to view review summary for this task",
    )


def test_security_regression_limits_export_download_to_responsible_admin(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_export_client(tmp_path, runtime_config=runtime_config)
    task_id = create_export_task(client)

    update_task_row(tmp_path, task_id, status="open")
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="security-regression-invoice.pdf",
        split_items=[{"member_id": "2250001", "amount_cents": 12345}],
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")
    export_job = create_export_job(client, task_id, format="csv")

    processor = build_processor(tmp_path, runtime_config)
    assert processor.run_once() == 1

    owner_download = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=admin_auth_headers(client),
    )
    assert owner_download.status_code == 200

    member_download = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )
    assert_api_error(
        member_download,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to manage exports for this task",
    )

    outsider_download = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=outsider_admin_auth_headers(client),
    )
    assert_api_error(
        outsider_download,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to manage exports for this task",
    )


def test_security_regression_redacts_sensitive_log_and_audit_fields():
    sanitized = sanitize_log_fields(
        {
            "authorization": "Bearer secret-token",
            "storage_key": "private/task-1/export.csv",
            "artifact_url": "https://storage.example.com/private/task-1/export.csv?signature=secret",
            "root_dir": "/srv/trms/materials",
        }
    )

    assert sanitized["authorization"] == REDACTED_LOG_VALUE
    assert sanitized["storage_key"] == REDACTED_LOG_PATH
    assert sanitized["artifact_url"] == "https://storage.example.com/[redacted-path]"
    assert sanitized["root_dir"] == REDACTED_LOG_PATH

    entry = AuditLogCreate(
        actor_id="system:export-worker",
        object_type="export_job",
        object_id="job-1",
        action="complete_task_export_job",
        result=AuditLogResult.FAILED,
        summary="export failed token=secret-token",
        detail={
            "authorization": "Bearer secret-token",
            "raw_response": '{"secret":"payload"}',
            "failure_reason": "  worker timeout  ",
        },
    )

    assert entry.summary == "export failed token=[REDACTED]"
    assert entry.detail["authorization"] == REDACTED_AUDIT_VALUE
    assert entry.detail["raw_response"] == REDACTED_AUDIT_VALUE
    assert entry.detail["failure_reason"] == "worker timeout"


def test_security_regression_keeps_cors_explicit_and_applied(tmp_path):
    with pytest.raises(RuntimeConfigError) as exc_info:
        load_runtime_config(
            env={
                "TRMS_ENV": "production",
                "DATABASE_URL": f"sqlite:///{tmp_path}/production.db",
                "TRMS_STORAGE_BACKEND": "s3",
                "TRMS_STORAGE_S3_ENDPOINT": "https://minio.example.com",
                "TRMS_STORAGE_S3_BUCKET": "trms-prod",
                "TRMS_STORAGE_S3_ACCESS_KEY_ID": "prod-access",
                "TRMS_STORAGE_S3_SECRET_ACCESS_KEY": "prod-secret",
                "TRMS_PUBLIC_API_BASE_URL": "https://trms.example.edu/api",
                "TRMS_API_HOST": "0.0.0.0",
                "TRMS_API_PORT": "8000",
            }
        )

    assert "TRMS_CORS_ALLOWED_ORIGINS is required when TRMS_ENV=production" in str(
        exc_info.value
    )

    config = load_runtime_config(
        env={},
        database_url=f"sqlite:///{tmp_path}/test.db",
        material_storage_dir=tmp_path / "materials",
        cors_allowed_origins="http://example.com",
        public_api_base_url="http://example.com/api",
    )
    client = TestClient(create_app(runtime_config=config))

    response = client.options(
        "/api/tasks",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://example.com"


def test_security_regression_enforces_production_registration_policy(tmp_path):
    client = make_auth_client(tmp_path, runtime_config=make_production_runtime_config(tmp_path))

    privileged_register = client.post(
        "/api/auth/register",
        json=register_payload(
            username="admin1",
            role="admin",
            actor_id="admin-1",
            member_code=None,
        ),
    )
    assert_api_error(
        privileged_register,
        status_code=403,
        code="forbidden",
        detail="self-service registration for role 'admin' is disabled",
    )

    member_register = client.post(
        "/api/auth/register",
        json=register_payload(
            username="member2",
            actor_id="2250002",
            member_code="MEM-002",
        ),
    )

    assert member_register.status_code == 201
    assert member_register.json()["user"]["role"] == "member"
