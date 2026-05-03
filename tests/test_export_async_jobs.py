import json
from io import BytesIO
from zipfile import ZipFile

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
from pypdf import PdfReader

from api_error_assertions import assert_api_error
from test_exports_api import (
    build_pdf_bytes,
    build_png_bytes,
    create_export_job,
    create_invoice_with_splits,
    create_invoice_with_splits_and_material,
    upload_supporting_material,
)
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
    assert export_job["status"] == "pending"
    assert export_job["artifact"] is None
    assert export_job["failure_reason"] is None
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


def test_export_artifact_download_exposes_filename_header_for_browser_cors(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="invoice-a.pdf",
        material_content=build_pdf_bytes(),
        split_items=[{"member_id": "2250001", "amount_cents": 12345}],
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")
    export_job = create_export_job(client, task_id, format="csv")
    processor = build_processor(tmp_path, runtime_config)
    processor.run_once()

    download_response = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=admin_auth_headers(client) | {
            "Origin": "http://127.0.0.1:5173",
        },
    )

    assert download_response.status_code == 200
    exposed_headers = download_response.headers["access-control-expose-headers"]
    assert "Content-Disposition" in exposed_headers


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


def test_export_async_processor_persists_real_merged_pdf_artifact(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="invoice-a.pdf",
        material_content=build_pdf_bytes(),
        split_items=[{"member_id": "2250001", "amount_cents": 12345}],
    )
    upload_supporting_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="order_screenshot",
        filename="ticket.png",
        content_type="image/png",
        content=build_png_bytes(),
    )
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
    status_body = status_response.json()
    assert status_body["status"] == "succeeded"
    assert status_body["failure_reason"] is None
    assert status_body["artifact"]["filename"] == f"{task_id}-merged-printing.pdf"
    assert status_body["artifact"]["content_type"] == "application/pdf"

    artifact_download = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=admin_auth_headers(client),
    )
    assert artifact_download.status_code == 200
    assert artifact_download.headers["content-type"].startswith("application/pdf")
    assert (
        artifact_download.headers["content-disposition"]
        == f'attachment; filename="{task_id}-merged-printing.pdf"'
    )
    assert len(PdfReader(BytesIO(artifact_download.content)).pages) == 2

    audit_logs = list_export_job_audit_logs(tmp_path, export_job_id=export_job["id"])

    assert len(audit_logs) == 3
    assert audit_logs[0].action == "create_task_export_job"
    assert audit_logs[0].detail["kind"] == "merged_pdf"
    assert audit_logs[0].detail["format"] == "pdf"
    assert audit_logs[1].actor_id == "system:export-worker"
    assert audit_logs[1].action == "complete_task_export_job"
    assert audit_logs[1].result is AuditLogResult.SUCCEEDED
    assert audit_logs[1].request_id is None
    assert audit_logs[1].detail["previous_status"] == "running"
    assert audit_logs[1].detail["status"] == "succeeded"
    assert audit_logs[1].detail["artifact"]["filename"] == f"{task_id}-merged-printing.pdf"
    assert audit_logs[2].actor_id == "admin-1"
    assert audit_logs[2].action == "download_task_export_artifact"
    assert audit_logs[2].result is AuditLogResult.SUCCEEDED


def test_export_async_processor_reports_specific_merged_pdf_failure_reason(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")
    material_id = upload_supporting_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="competition_notice",
        filename="broken.pdf",
        content=b"%PDF-1.4 broken",
    )
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
    status_body = status_response.json()
    assert status_body["status"] == "failed"
    assert status_body["artifact"] is None
    assert status_body["started_at"] is not None
    assert status_body["finished_at"] is not None
    assert status_body["failure_reason"].startswith("merged pdf source material ")
    assert material_id in status_body["failure_reason"]
    assert "is unreadable:" in status_body["failure_reason"]

    audit_logs = list_export_job_audit_logs(tmp_path, export_job_id=export_job["id"])

    assert len(audit_logs) == 2
    assert audit_logs[0].action == "create_task_export_job"
    assert audit_logs[0].result is AuditLogResult.SUCCEEDED
    assert audit_logs[1].actor_id == "system:export-worker"
    assert audit_logs[1].action == "fail_task_export_job"
    assert audit_logs[1].result is AuditLogResult.FAILED
    assert audit_logs[1].request_id is None
    assert audit_logs[1].detail["previous_status"] == "running"
    assert audit_logs[1].detail["status"] == "failed"
    assert audit_logs[1].detail["artifact"] is None
    assert audit_logs[1].detail["failure_reason"] == status_body["failure_reason"]


def test_export_async_processor_persists_reimbursement_package_zip_with_manifest(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="invoice-a.pdf",
        material_content=build_pdf_bytes(),
        split_items=[{"member_id": "2250001", "amount_cents": 12345}],
    )
    upload_supporting_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="payment_record",
        filename="payment.png",
        content_type="image/png",
        content=build_png_bytes(),
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")
    export_job = create_export_job(
        client,
        task_id,
        kind="reimbursement_package",
        format="zip",
    )
    processor = build_processor(tmp_path, runtime_config)

    processed_count = processor.run_once()

    assert processed_count == 1

    status_response = client.get(
        f"/api/tasks/exports/{export_job['id']}",
        headers=admin_auth_headers(client),
    )
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] == "succeeded"
    assert status_body["failure_reason"] is None
    assert status_body["artifact"]["filename"] == f"{task_id}-reimbursement-package.zip"
    assert status_body["artifact"]["content_type"] == "application/zip"

    artifact_download = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=admin_auth_headers(client),
    )
    assert artifact_download.status_code == 200
    assert artifact_download.headers["content-type"].startswith("application/zip")
    assert (
        artifact_download.headers["content-disposition"]
        == f'attachment; filename="{task_id}-reimbursement-package.zip"'
    )

    with ZipFile(BytesIO(artifact_download.content)) as archive:
        names = set(archive.namelist())
        assert names == {
            "reimbursement-summary.csv",
            "member-details.csv",
            "invoice-details.csv",
            "missing-materials.csv",
            "finance-draft.json",
            "merged-printing.pdf",
            "manifest.json",
        }
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        assert manifest["task_id"] == task_id
        assert manifest["task_data_version"] == status_body["task_data_version"]
        assert manifest["exported_by"] == "admin-1"
        assert manifest["warnings"] == []
        artifact_names = {item["filename"] for item in manifest["artifacts"]}
        assert artifact_names == names - {"manifest.json"}
        assert len(manifest["materials"]) == 2
        assert len(PdfReader(BytesIO(archive.read("merged-printing.pdf"))).pages) == 2


def test_reimbursement_package_export_skips_paper_invoice_placeholder_in_merged_pdf(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")

    create_response = client.post(
        f"/api/tasks/{task_id}/paper-invoices",
        json={
            "invoice_number": "PAPER-EXPORT-001",
            "issue_date": "2026-11-04",
            "transaction_time": "2026-11-01T08:00:00+00:00",
            "buyer_name": "同济大学",
            "tax_number": "12100000425006117D",
            "seller_name": "线下收票",
            "corporate_transfer_reference": None,
            "amount_cents": 8800,
            "expense_type": "registration",
        },
        headers=member_auth_headers(client),
    )
    assert create_response.status_code == 201
    paper_invoice = create_response.json()["invoice"]

    confirm_response = client.put(
        f"/api/invoices/{paper_invoice['id']}/paper-receipt",
        json={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )
    assert confirm_response.status_code == 200

    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="invoice-a.pdf",
        material_content=build_pdf_bytes(),
        split_items=[{"member_id": "2250001", "amount_cents": 12345}],
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")
    export_job = create_export_job(
        client,
        task_id,
        kind="reimbursement_package",
        format="zip",
    )
    processor = build_processor(tmp_path, runtime_config)

    processed_count = processor.run_once()

    assert processed_count == 1

    artifact_download = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=admin_auth_headers(client),
    )
    assert artifact_download.status_code == 200

    with ZipFile(BytesIO(artifact_download.content)) as archive:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        assert manifest["warnings"] == [
            f"纸质发票 {paper_invoice['invoice_number']} 仅记录线下收票，不会出现在 merged-printing.pdf 中。"
        ]
        assert len(manifest["materials"]) == 2
        assert len(PdfReader(BytesIO(archive.read("merged-printing.pdf"))).pages) == 1


def test_reimbursement_package_export_groups_shared_attachment_related_invoices(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")

    invoice_a_id, _ = create_invoice_with_splits_and_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="invoice-a.pdf",
        material_content=build_pdf_bytes(width=101, height=101),
        invoice_overrides={"invoice_number": "INV-A"},
    )
    _, _ = create_invoice_with_splits_and_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="invoice-b.pdf",
        material_content=build_pdf_bytes(width=202, height=202),
        invoice_overrides={"invoice_number": "INV-B"},
    )
    invoice_c_id, _ = create_invoice_with_splits_and_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="invoice-c.pdf",
        material_content=build_pdf_bytes(width=303, height=303),
        invoice_overrides={"invoice_number": "INV-C"},
    )
    exclusive_attachment_material_id = upload_supporting_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="payment_record",
        filename="attachment-a.pdf",
        content=build_pdf_bytes(width=111, height=111),
    )
    shared_attachment_material_id = upload_supporting_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="competition_notice",
        filename="attachment-shared.pdf",
        content=build_pdf_bytes(width=222, height=222),
    )
    for invoice_id, material_id in (
        (invoice_a_id, exclusive_attachment_material_id),
        (invoice_a_id, shared_attachment_material_id),
        (invoice_c_id, shared_attachment_material_id),
    ):
        attach_response = client.put(
            f"/api/invoices/{invoice_id}/supporting-materials/{material_id}",
            headers=admin_auth_headers(client),
        )
        assert attach_response.status_code == 200

    update_task_row(tmp_path, task_id, status="ready_to_export")
    export_job = create_export_job(
        client,
        task_id,
        kind="reimbursement_package",
        format="zip",
    )
    processor = build_processor(tmp_path, runtime_config)

    processed_count = processor.run_once()

    assert processed_count == 1

    artifact_download = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=admin_auth_headers(client),
    )
    assert artifact_download.status_code == 200

    with ZipFile(BytesIO(artifact_download.content)) as archive:
        merged_pdf = PdfReader(BytesIO(archive.read("merged-printing.pdf")))
        page_widths = [int(float(page.mediabox.width)) for page in merged_pdf.pages]
        assert page_widths == [101, 111, 303, 222, 202]


def test_original_materials_archive_export_preserves_original_filenames_and_deduplicates_collisions(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="invoice.pdf",
        material_content=build_pdf_bytes(width=101, height=101),
        split_items=[{"member_id": "2250001", "amount_cents": 12345}],
    )
    upload_supporting_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="payment_record",
        filename="invoice.pdf",
        content_type="image/png",
        content=build_png_bytes(),
    )
    upload_supporting_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="competition_notice",
        filename="notice.pdf",
        content=build_pdf_bytes(width=202, height=202),
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")
    export_job = create_export_job(
        client,
        task_id,
        kind="original_materials_archive",
        format="zip",
    )
    processor = build_processor(tmp_path, runtime_config)

    processed_count = processor.run_once()

    assert processed_count == 1

    status_response = client.get(
        f"/api/tasks/exports/{export_job['id']}",
        headers=admin_auth_headers(client),
    )
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] == "succeeded"
    assert status_body["artifact"]["filename"] == f"{task_id}-original-materials.zip"
    assert status_body["artifact"]["content_type"] == "application/zip"

    artifact_download = client.get(
        f"/api/tasks/exports/{export_job['id']}/artifact",
        headers=admin_auth_headers(client),
    )
    assert artifact_download.status_code == 200

    with ZipFile(BytesIO(artifact_download.content)) as archive:
        names = archive.namelist()
        assert names == ["invoice.pdf", "invoice (2).pdf", "notice.pdf"]
        assert archive.read("invoice.pdf").startswith(b"%PDF-")
        assert archive.read("invoice (2).pdf").startswith(b"\x89PNG\r\n\x1a\n")
        assert archive.read("notice.pdf").startswith(b"%PDF-")


def test_export_async_processor_rejects_stale_reimbursement_package_job(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="invoice-a.pdf",
        material_content=build_pdf_bytes(),
        split_items=[{"member_id": "2250001", "amount_cents": 12345}],
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")
    export_job = create_export_job(
        client,
        task_id,
        kind="reimbursement_package",
        format="zip",
    )
    update_task_row(
        tmp_path,
        task_id,
        project_info="Main flow integration scaffold (revised)",
    )
    processor = build_processor(tmp_path, runtime_config)

    processed_count = processor.run_once()

    assert processed_count == 1

    status_response = client.get(
        f"/api/tasks/exports/{export_job['id']}",
        headers=admin_auth_headers(client),
    )
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] == "failed"
    assert status_body["artifact"] is None
    assert status_body["failure_reason"] == (
        "task data changed since export job was requested; create a new export job"
    )
