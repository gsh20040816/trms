from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from trms_backend.application.recognition_async_jobs import RecognitionAsyncJobProcessor
from trms_backend.application.recognition_llm import (
    RecognitionLlmClient,
    RecognitionLlmExtractionResult,
)
from trms_backend.application.recognition_preparation import RecognitionPreparationService
from trms_backend.application.recognition_runtime import resolve_recognition_llm_capability
from trms_backend.domain.recognitions import RecognitionFieldResult
from trms_backend.domain.audit_logs import AuditLogResult
from trms_backend.infrastructure.database import build_session_factory, init_database
from trms_backend.infrastructure.repositories import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyConfirmationRepository,
    SqlAlchemyExpenseSplitRepository,
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


class FakeRecognitionLlmClient(RecognitionLlmClient):
    def __init__(self, result: RecognitionLlmExtractionResult) -> None:
        self._result = result

    def recognize(self, *, material, document_input) -> RecognitionLlmExtractionResult:
        return self._result


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


def upload_material(
    client: TestClient,
    task_id: str,
    *,
    material_type: str | None = "invoice",
) -> str:
    form_data = {
        "submitter_id": "2250001",
        "channel": "web",
    }
    if material_type is not None:
        form_data["material_type"] = material_type
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data=form_data,
        files={"files": ("async-ticket.pdf", build_text_pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["items"][0]["id"]


def build_processor(
    tmp_path,
    runtime_config,
    *,
    recognition_llm_client: RecognitionLlmClient | None = None,
) -> RecognitionAsyncJobProcessor:
    session_factory = build_session_factory(runtime_config.database_url)
    init_database(session_factory)
    material_repository = SqlAlchemyMaterialRepository(session_factory)
    task_repository = SqlAlchemyTaskRepository(session_factory)
    invoice_repository = SqlAlchemyInvoiceRepository(session_factory)
    validation_repository = SqlAlchemyValidationRepository(session_factory)
    audit_log_repository = SqlAlchemyAuditLogRepository(session_factory)
    recognition_task_repository = SqlAlchemyRecognitionTaskRepository(session_factory)
    split_repository = SqlAlchemyExpenseSplitRepository(session_factory)
    confirmation_repository = SqlAlchemyConfirmationRepository(session_factory)
    material_file_storage = LocalMaterialFileStorage(tmp_path / "material-storage")
    recognition_preparation_service = RecognitionPreparationService(
        material_repository,
        material_file_storage,
        recognition_task_repository,
        audit_log_repository,
        resolve_recognition_llm_capability(runtime_config),
        recognition_llm_client,
    )
    return RecognitionAsyncJobProcessor(
        task_repository=task_repository,
        material_repository=material_repository,
        invoice_repository=invoice_repository,
        validation_repository=validation_repository,
        recognition_task_repository=recognition_task_repository,
        split_repository=split_repository,
        confirmation_repository=confirmation_repository,
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


def test_recognition_async_processor_auto_creates_invoice_after_successful_recognition(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    material_id = upload_material(client, task_id)
    processor = build_processor(
        tmp_path,
        runtime_config,
        recognition_llm_client=FakeRecognitionLlmClient(
            RecognitionLlmExtractionResult(
                raw_response={"provider": "fake-worker"},
                recognized_fields={
                    "material_type": RecognitionFieldResult(
                        value="invoice",
                        source="ai",
                        confidence=0.99,
                    ),
                    "invoice_number": RecognitionFieldResult(
                        value="ASYNC-AUTO-001",
                        source="ai",
                        confidence=0.99,
                    ),
                    "buyer_name": RecognitionFieldResult(
                        value="同济大学",
                        source="ai",
                        confidence=0.98,
                    ),
                    "tax_number": RecognitionFieldResult(
                        value="12100000425006117D",
                        source="ai",
                        confidence=0.98,
                    ),
                    "amount_cents": RecognitionFieldResult(
                        value=45678,
                        source="ai",
                        confidence=0.97,
                    ),
                    "expense_type": RecognitionFieldResult(
                        value="registration",
                        source="ai",
                        confidence=0.96,
                    ),
                },
            )
        ),
    )

    assert processor.run_once() == 1

    invoices_response = client.get(
        f"/api/tasks/{task_id}/invoices",
        headers=admin_auth_headers(client),
    )
    assert invoices_response.status_code == 200
    invoices = invoices_response.json()["items"]
    assert len(invoices) == 1
    assert invoices[0]["material_id"] == material_id
    assert invoices[0]["invoice_number"] == "ASYNC-AUTO-001"
    assert invoices[0]["amount_cents"] == 45678

    validations_response = client.get(
        f"/api/invoices/{invoices[0]['id']}/validations",
        headers=admin_auth_headers(client),
    )
    assert validations_response.status_code == 200
    assert validations_response.json()["items"]


def test_recognition_async_processor_auto_creates_invoice_after_default_material_type_is_recognized(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    material_id = upload_material(client, task_id, material_type=None)
    processor = build_processor(
        tmp_path,
        runtime_config,
        recognition_llm_client=FakeRecognitionLlmClient(
            RecognitionLlmExtractionResult(
                raw_response={"provider": "fake-worker"},
                recognized_fields={
                    "material_type": RecognitionFieldResult(
                        value="invoice",
                        source="ai",
                        confidence=0.99,
                    ),
                    "invoice_number": RecognitionFieldResult(
                        value="ASYNC-DEFAULT-AUTO-001",
                        source="ai",
                        confidence=0.99,
                    ),
                    "buyer_name": RecognitionFieldResult(
                        value="同济大学",
                        source="ai",
                        confidence=0.98,
                    ),
                    "tax_number": RecognitionFieldResult(
                        value="12100000425006117D",
                        source="ai",
                        confidence=0.98,
                    ),
                    "amount_cents": RecognitionFieldResult(
                        value=45678,
                        source="ai",
                        confidence=0.97,
                    ),
                    "expense_type": RecognitionFieldResult(
                        value="registration",
                        source="ai",
                        confidence=0.96,
                    ),
                },
            )
        ),
    )

    assert processor.run_once() == 1

    invoices_response = client.get(
        f"/api/tasks/{task_id}/invoices",
        headers=admin_auth_headers(client),
    )
    assert invoices_response.status_code == 200
    invoices = invoices_response.json()["items"]
    assert len(invoices) == 1
    assert invoices[0]["material_id"] == material_id
    assert invoices[0]["invoice_number"] == "ASYNC-DEFAULT-AUTO-001"

    materials_response = client.get(
        f"/api/tasks/{task_id}/materials",
        headers=admin_auth_headers(client),
    )
    assert materials_response.status_code == 200
    assert materials_response.json()["items"][0]["material_type"] == "invoice"
