from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from trms_backend.application.recognition_async_jobs import RecognitionAsyncJobProcessor
from trms_backend.application.recognition_preparation import RecognitionPreparationService
from trms_backend.application.recognition_runtime import resolve_recognition_llm_capability
from trms_backend.domain.audit_logs import AuditLogResult
from trms_backend.infrastructure.database import build_session_factory, init_database
from trms_backend.infrastructure.repositories import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyInvoiceRepository,
    SqlAlchemyMaterialRepository,
    SqlAlchemyRecognitionTaskRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyValidationRepository,
)
from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from test_tasks_api import admin_auth_headers, create_task as create_admin_task


def build_text_pdf_bytes() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=144)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref}),
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT\n/F1 12 Tf\n72 100 Td\n(Invoice INV-ASYNC-001 Tongji University) Tj\nET\n"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


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
    task = create_admin_task(client)
    client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    return task["id"]


def upload_material(client: TestClient, task_id: str) -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("async-ticket.pdf", build_text_pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["items"][0]["id"]


def build_processor(tmp_path, runtime_config) -> RecognitionAsyncJobProcessor:
    session_factory = build_session_factory(runtime_config.database_url)
    init_database(session_factory)
    material_repository = SqlAlchemyMaterialRepository(session_factory)
    task_repository = SqlAlchemyTaskRepository(session_factory)
    invoice_repository = SqlAlchemyInvoiceRepository(session_factory)
    validation_repository = SqlAlchemyValidationRepository(session_factory)
    audit_log_repository = SqlAlchemyAuditLogRepository(session_factory)
    recognition_task_repository = SqlAlchemyRecognitionTaskRepository(session_factory)
    material_file_storage = LocalMaterialFileStorage(tmp_path / "material-storage")
    recognition_preparation_service = RecognitionPreparationService(
        material_repository,
        material_file_storage,
        recognition_task_repository,
        audit_log_repository,
        resolve_recognition_llm_capability(runtime_config),
    )
    return RecognitionAsyncJobProcessor(
        task_repository=task_repository,
        material_repository=material_repository,
        invoice_repository=invoice_repository,
        validation_repository=validation_repository,
        recognition_task_repository=recognition_task_repository,
        recognition_preparation_service=recognition_preparation_service,
    )


def test_recognition_async_processor_consumes_pending_task_and_preserves_idempotency(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    material_id = upload_material(client, task_id)
    processor = build_processor(tmp_path, runtime_config)

    first_run_processed = processor.run_once()
    first_listing = client.get(f"/api/materials/{material_id}/recognition-tasks")
    second_run_processed = processor.run_once()

    assert first_run_processed == 1
    assert second_run_processed == 0
    assert first_listing.status_code == 200
    assert first_listing.json()["retry_count"] == 0
    task = first_listing.json()["items"][0]
    assert task["status"] == "failed"
    assert task["failure"] == {
        "stage": "ai",
        "reason": "llm_provider_not_configured",
    }

    audit_repository = SqlAlchemyAuditLogRepository(
        build_session_factory(runtime_config.database_url)
    )
    audit_logs = audit_repository.list_by_object(
        object_type="recognition_task",
        object_id=task["id"],
    )

    assert len(audit_logs) == 1
    assert audit_logs[0].actor_id == "system:recognition-worker"
    assert audit_logs[0].action == "record_recognition_result"
    assert audit_logs[0].result is AuditLogResult.FAILED
    assert audit_logs[0].task_id == task_id
    assert audit_logs[0].request_id is None
    assert audit_logs[0].detail["material_id"] == material_id
    assert audit_logs[0].detail["recognition_status"] == "failed"
    assert audit_logs[0].detail["failure_stage"] == "ai"
    assert audit_logs[0].detail["failure_reason"] == "llm_provider_not_configured"
    assert "raw_response" not in audit_logs[0].detail
