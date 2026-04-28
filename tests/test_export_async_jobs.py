from fastapi.testclient import TestClient

from trms_backend.application.export_async_jobs import ExportAsyncJobProcessor
from trms_backend.domain.audit_logs import AuditLogResult
from trms_backend.infrastructure.database import build_session_factory, init_database
from trms_backend.infrastructure.repositories import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyConfirmationRepository,
    SqlAlchemyExportJobRepository,
    SqlAlchemyExpenseSplitRepository,
    SqlAlchemyInvoiceRepository,
    SqlAlchemyMaterialRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyValidationRepository,
)
from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from api_error_assertions import assert_api_error
from test_exports_api import create_export_job, create_invoice_with_splits
from test_tasks_api import (
    admin_auth_headers,
    auth_headers,
    create_task as create_admin_task,
    register_and_get_token,
    update_task_row,
)


def make_runtime_config(tmp_path):
    return load_runtime_config(
        environment="test",
        database_url=f"sqlite:///{tmp_path}/test.db",
        material_storage_dir=tmp_path / "material-storage",
        cors_allowed_origins="http://127.0.0.1:5173",
        public_api_base_url="http://127.0.0.1:8000/api",
        api_host="127.0.0.1",
        api_port=8000,
        async_job_mode="worker",
    )


def make_client(tmp_path, *, runtime_config):
    return TestClient(
        create_app(
            runtime_config=runtime_config,
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def create_task(client: TestClient) -> str:
    return create_admin_task(client)["id"]


def member_auth_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(
        register_and_get_token(
            client,
            username="member1",
            role="member",
            actor_id="2250001",
            member_code="2250001",
        )
    )


def outsider_admin_auth_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(
        register_and_get_token(
            client,
            username="admin2",
            role="admin",
            actor_id="admin-2",
            member_code=None,
        )
    )


def build_processor(tmp_path, runtime_config) -> ExportAsyncJobProcessor:
    session_factory = build_session_factory(runtime_config.database_url)
    init_database(session_factory)
    return ExportAsyncJobProcessor(
        task_repository=SqlAlchemyTaskRepository(session_factory),
        export_job_repository=SqlAlchemyExportJobRepository(session_factory),
        invoice_repository=SqlAlchemyInvoiceRepository(session_factory),
        material_repository=SqlAlchemyMaterialRepository(session_factory),
        material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        validation_repository=SqlAlchemyValidationRepository(session_factory),
        split_repository=SqlAlchemyExpenseSplitRepository(session_factory),
        confirmation_repository=SqlAlchemyConfirmationRepository(session_factory),
        audit_log_repository=SqlAlchemyAuditLogRepository(session_factory),
    )


def list_export_job_audit_logs(tmp_path, *, export_job_id: str):
    repository = SqlAlchemyAuditLogRepository(
        build_session_factory(f"sqlite:///{tmp_path}/test.db")
    )
    return repository.list_by_object(
        object_type="export_job",
        object_id=export_job_id,
    )


def test_export_async_processor_persists_artifact_and_exposes_download(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="railway-a.pdf",
        split_items=[{"member_id": "2250001", "amount_cents": 12345}],
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")
    export_job = create_export_job(
        client,
        task_id,
        format="csv",
    )
    processor = build_processor(tmp_path, runtime_config)

    processed_count = processor.run_once()
    second_run_processed = processor.run_once()

    assert processed_count == 1
    assert second_run_processed == 0

    status_response = client.get(
        f"/api/tasks/exports/{export_job['id']}",
        headers=admin_auth_headers(client),
    )
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] == "succeeded"
    assert status_body["retry_count"] == 0
    assert status_body["artifact"] == {
        "filename": f"{task_id}-reimbursement-summary.csv",
        "content_type": "text/csv",
        "size_bytes": status_body["artifact"]["size_bytes"],
        "sha256": status_body["artifact"]["sha256"],
    }
    assert "artifact_storage_key" not in status_response.text
    assert status_body["started_at"] is not None
    assert status_body["finished_at"] is not None

    download_response = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=admin_auth_headers(client),
    )
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("text/csv")
    assert (
        download_response.headers["content-disposition"]
        == f'attachment; filename="{task_id}-reimbursement-summary.csv"'
    )
    assert "expense_type,total_amount_cents" in download_response.text
    assert "grand_total" in download_response.text

    audit_logs = list_export_job_audit_logs(tmp_path, export_job_id=export_job["id"])

    assert len(audit_logs) == 3
    assert audit_logs[0].actor_id == "admin-1"
    assert audit_logs[0].action == "create_task_export_job"
    assert audit_logs[0].result is AuditLogResult.SUCCEEDED
    assert audit_logs[0].task_id == task_id
    assert audit_logs[0].request_id.startswith("req_")
    assert audit_logs[0].detail["kind"] == "reimbursement_summary"
    assert audit_logs[0].detail["format"] == "csv"
    assert audit_logs[1].actor_id == "system:export-worker"
    assert audit_logs[1].action == "complete_task_export_job"
    assert audit_logs[1].result is AuditLogResult.SUCCEEDED
    assert audit_logs[1].request_id is None
    assert audit_logs[1].detail["previous_status"] == "running"
    assert audit_logs[1].detail["status"] == "succeeded"
    assert audit_logs[1].detail["artifact"]["filename"] == f"{task_id}-reimbursement-summary.csv"
    assert "storage_key" not in str(audit_logs[1].detail)
    assert audit_logs[2].actor_id == "admin-1"
    assert audit_logs[2].action == "download_task_export_artifact"
    assert audit_logs[2].result is AuditLogResult.SUCCEEDED
    assert audit_logs[2].request_id.startswith("req_")
    assert audit_logs[2].detail["artifact"]["filename"] == f"{task_id}-reimbursement-summary.csv"
    assert "storage_key" not in str(audit_logs[2].detail)


def test_export_artifact_download_reports_not_ready_and_rejects_non_admin(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")
    export_job = create_export_job(
        client,
        task_id,
        format="csv",
    )

    pending_download = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=admin_auth_headers(client),
    )
    assert_api_error(
        pending_download,
        status_code=409,
        code="conflict",
        detail="export artifact is not ready; current status is pending",
    )

    anonymous_status = client.get(f"/api/tasks/exports/{export_job['id']}")
    assert_api_error(
        anonymous_status,
        status_code=401,
        code="unauthorized",
        detail="invalid or missing bearer token",
    )

    forbidden_status = client.get(
        f"/api/tasks/exports/{export_job['id']}",
        headers=member_auth_headers(client),
    )
    assert_api_error(
        forbidden_status,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to manage exports for this task",
    )

    forbidden_download = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=member_auth_headers(client),
    )
    assert_api_error(
        forbidden_download,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to manage exports for this task",
    )


def test_export_artifact_download_is_limited_to_responsible_administrator(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="railway-b.pdf",
        split_items=[{"member_id": "2250001", "amount_cents": 12345}],
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")
    export_job = create_export_job(
        client,
        task_id,
        format="csv",
    )
    processor = build_processor(tmp_path, runtime_config)

    processed_count = processor.run_once()

    assert processed_count == 1

    owner_download = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=admin_auth_headers(client),
    )
    assert owner_download.status_code == 200
    assert owner_download.headers["content-type"].startswith("text/csv")

    outsider_download = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=outsider_admin_auth_headers(client),
    )
    assert outsider_download.status_code == 403
    assert outsider_download.json()["detail"] == (
        "actor is not allowed to manage exports for this task"
    )

    anonymous_download = client.get(f"/api/tasks/exports/{export_job['id']}/artifact")
    assert anonymous_download.status_code == 401
    assert anonymous_download.json()["detail"] == "invalid or missing bearer token"


def test_export_async_processor_marks_unimplemented_job_failed(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")
    export_job = create_export_job(
        client,
        task_id,
        kind="merged_pdf",
        format="pdf",
    )
    processor = build_processor(tmp_path, runtime_config)

    processed_count = processor.run_once()

    assert processed_count == 1

    status_response = client.get(
        f"/api/tasks/exports/{export_job['id']}",
        headers=admin_auth_headers(client),
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "failed"
    assert status_response.json()["failure_reason"] == (
        "export format pdf is not implemented yet for merged_pdf"
    )

    failed_download = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=admin_auth_headers(client),
    )
    assert failed_download.status_code == 409
    assert failed_download.json()["detail"] == (
        "export artifact is unavailable because the job failed: "
        "export format pdf is not implemented yet for merged_pdf"
    )

    audit_logs = list_export_job_audit_logs(tmp_path, export_job_id=export_job["id"])

    assert len(audit_logs) == 2
    assert audit_logs[0].action == "create_task_export_job"
    assert audit_logs[0].detail["kind"] == "merged_pdf"
    assert audit_logs[0].detail["format"] == "pdf"
    assert audit_logs[1].actor_id == "system:export-worker"
    assert audit_logs[1].action == "fail_task_export_job"
    assert audit_logs[1].result is AuditLogResult.FAILED
    assert audit_logs[1].request_id is None
    assert audit_logs[1].detail["previous_status"] == "running"
    assert audit_logs[1].detail["status"] == "failed"
    assert audit_logs[1].detail["failure_reason"] == (
        "export format pdf is not implemented yet for merged_pdf"
    )
    assert audit_logs[1].detail["artifact"] is None
