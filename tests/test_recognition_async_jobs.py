from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from trms_backend.application.recognition_async_jobs import RecognitionAsyncJobProcessor
from trms_backend.application.recognition_llm import (
    RecognitionInputSource,
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

from test_tasks_api import (
    admin_auth_headers,
    create_invoice,
    create_task as create_admin_task,
    valid_task_payload,
)


class FakeRecognitionLlmClient(RecognitionLlmClient):
    def __init__(self, result: RecognitionLlmExtractionResult) -> None:
        self._result = result

    def recognize(self, *, material, document_input) -> RecognitionLlmExtractionResult:
        return self._result


class InlineInvoiceNumberRecognitionLlmClient(RecognitionLlmClient):
    def __init__(self) -> None:
        self.last_document_text: str | None = None

    def recognize(self, *, material, document_input) -> RecognitionLlmExtractionResult:
        assert document_input.source is RecognitionInputSource.PDF_TEXT
        self.last_document_text = document_input.text
        recognized_fields = {
            "material_type": RecognitionFieldResult(
                value="invoice",
                source="ai",
                confidence=0.99,
            ),
            "buyer_name": RecognitionFieldResult(
                value="Tongji University",
                source="ai",
                confidence=0.98,
            ),
            "tax_number": RecognitionFieldResult(
                value="12100000425006117D",
                source="ai",
                confidence=0.98,
            ),
            "amount_cents": RecognitionFieldResult(
                value=7286,
                source="ai",
                confidence=0.97,
            ),
            "expense_type": RecognitionFieldResult(
                value="registration",
                source="ai",
                confidence=0.96,
            ),
        }
        if (
            document_input.text is not None
            and "Invoice Number" in document_input.text
            and "25312000000355846530" in document_input.text
            and document_input.text.index("Invoice Number")
            < document_input.text.index("25312000000355846530")
        ):
            recognized_fields["invoice_number"] = RecognitionFieldResult(
                value="25312000000355846530",
                source="ai",
                confidence=0.99,
            )
        return RecognitionLlmExtractionResult(
            raw_response={"provider": "inline-invoice-number"},
            recognized_fields=recognized_fields,
        )


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


def build_positioned_text_pdf_bytes() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=200)
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
        b"BT\n/F1 12 Tf\n250 120 Td\n(25312000000355846530) Tj\nET\n"
        b"BT\n/F1 12 Tf\n180 120 Td\n(: ) Tj\nET\n"
        b"BT\n/F1 12 Tf\n120 120 Td\n(Invoice Number) Tj\nET\n"
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
    content_bytes: bytes | None = None,
    filename: str = "async-ticket.pdf",
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
        files={
            "files": (
                filename,
                build_text_pdf_bytes() if content_bytes is None else content_bytes,
                "application/pdf",
            )
        },
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


def test_recognition_async_processor_auto_creates_invoice_from_expense_type_candidate(tmp_path):
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
                    "expense_type_candidate": RecognitionFieldResult(
                        value="railway",
                        source="ai",
                        confidence=0.97,
                    ),
                    "invoice_number": RecognitionFieldResult(
                        value="ASYNC-CANDIDATE-001",
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
                        value=35400,
                        source="ai",
                        confidence=0.97,
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
    assert invoices[0]["invoice_number"] == "ASYNC-CANDIDATE-001"
    assert invoices[0]["expense_type"] == "railway"


def test_recognition_async_processor_keeps_inline_invoice_number_text_order_for_pdf(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        content_bytes=build_positioned_text_pdf_bytes(),
        filename="positioned-invoice.pdf",
    )
    recognition_client = InlineInvoiceNumberRecognitionLlmClient()
    processor = build_processor(
        tmp_path,
        runtime_config,
        recognition_llm_client=recognition_client,
    )

    assert processor.run_once() == 1
    assert recognition_client.last_document_text is not None
    assert "Invoice Number" in recognition_client.last_document_text
    assert "25312000000355846530" in recognition_client.last_document_text
    assert recognition_client.last_document_text.index("Invoice Number") < recognition_client.last_document_text.index(
        "25312000000355846530"
    )

    invoices_response = client.get(
        f"/api/tasks/{task_id}/invoices",
        headers=admin_auth_headers(client),
    )
    assert invoices_response.status_code == 200
    invoices = invoices_response.json()["items"]
    assert len(invoices) == 1
    assert invoices[0]["material_id"] == material_id
    assert invoices[0]["invoice_number"] == "25312000000355846530"
    assert invoices[0]["expense_type"] == "registration"


def test_recognition_async_processor_auto_links_default_upload_after_support_type_is_recognized(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task_id = create_task(client)
    invoice_material_id = upload_material(client, task_id)
    create_invoice(
        client,
        invoice_material_id,
        amount_cents=45678,
        expense_type="registration",
        invoice_number="ASYNC-LINK-BASE-001",
        seller_name="报名服务商",
    )
    build_processor(
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
                    "expense_type": RecognitionFieldResult(
                        value="registration",
                        source="ai",
                        confidence=0.96,
                    ),
                    "invoice_number": RecognitionFieldResult(
                        value="ASYNC-LINK-BASE-001",
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
                },
            )
        ),
    ).run_once()
    support_material_id = upload_material(client, task_id, material_type=None)
    support_processor = build_processor(
        tmp_path,
        runtime_config,
        recognition_llm_client=FakeRecognitionLlmClient(
            RecognitionLlmExtractionResult(
                raw_response={"provider": "fake-worker"},
                recognized_fields={
                    "material_type": RecognitionFieldResult(
                        value="payment_record",
                        source="ai",
                        confidence=0.99,
                    ),
                    "expense_type_candidate": RecognitionFieldResult(
                        value="registration",
                        source="ai",
                        confidence=0.96,
                    ),
                    "amount_cents": RecognitionFieldResult(
                        value=45678,
                        source="ai",
                        confidence=0.98,
                    ),
                },
            )
        ),
    )

    assert support_processor.run_once() == 1

    invoice_repository = SqlAlchemyInvoiceRepository(
        build_session_factory(runtime_config.database_url)
    )
    linked_invoices = invoice_repository.list_by_supporting_material(support_material_id)
    assert [invoice.material_id for invoice in linked_invoices] == [invoice_material_id]


def test_recognition_async_processor_prioritizes_local_transport_invoice_for_itinerary(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task = create_admin_task(
        client,
        payload=valid_task_payload() | {"fee_categories": ["railway", "local_transport"]},
    )
    client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    task_id = task["id"]
    railway_material_id = upload_material(client, task_id, material_type="invoice")
    local_transport_material_id = upload_material(client, task_id, material_type="invoice")
    create_invoice(
        client,
        railway_material_id,
        expense_type="railway",
        amount_cents=12345,
        invoice_number="ASYNC-RAIL-001",
    )
    local_transport_invoice_id = create_invoice(
        client,
        local_transport_material_id,
        expense_type="local_transport",
        amount_cents=4250,
        invoice_number="ASYNC-RIDE-001",
        seller_name="滴滴出行",
    )
    itinerary_material_id = upload_material(client, task_id, material_type="itinerary")
    processor = build_processor(
        tmp_path,
        runtime_config,
        recognition_llm_client=FakeRecognitionLlmClient(
            RecognitionLlmExtractionResult(
                raw_response={"provider": "fake-worker"},
                recognized_fields={
                    "material_type": RecognitionFieldResult(
                        value="itinerary",
                        source="ai",
                        confidence=0.99,
                    ),
                    "expense_type": RecognitionFieldResult(
                        value="local_transport",
                        source="ai",
                        confidence=0.97,
                    ),
                    "amount_cents": RecognitionFieldResult(
                        value=4250,
                        source="ai",
                        confidence=0.96,
                    ),
                    "transaction_time": RecognitionFieldResult(
                        value="2026-11-01T08:00:00+00:00",
                        source="ai",
                        confidence=0.94,
                    ),
                },
            )
        ),
    )

    assert processor.run_once() == 1

    invoice_repository = SqlAlchemyInvoiceRepository(
        build_session_factory(runtime_config.database_url)
    )
    linked_invoices = invoice_repository.list_by_supporting_material(itinerary_material_id)
    assert [invoice.id for invoice in linked_invoices] == [local_transport_invoice_id]


def test_recognition_async_processor_does_not_auto_link_ambiguous_local_transport_itinerary(
    tmp_path,
):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task = create_admin_task(
        client,
        payload=valid_task_payload() | {"fee_categories": ["local_transport"]},
    )
    client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    task_id = task["id"]
    first_invoice_material_id = upload_material(client, task_id, material_type="invoice")
    second_invoice_material_id = upload_material(client, task_id, material_type="invoice")
    create_invoice(
        client,
        first_invoice_material_id,
        expense_type="local_transport",
        amount_cents=4250,
        invoice_number="ASYNC-RIDE-101",
        seller_name="滴滴出行",
    )
    create_invoice(
        client,
        second_invoice_material_id,
        expense_type="local_transport",
        amount_cents=4250,
        invoice_number="ASYNC-RIDE-102",
        seller_name="高德出行",
    )
    itinerary_material_id = upload_material(client, task_id, material_type="itinerary")
    processor = build_processor(
        tmp_path,
        runtime_config,
        recognition_llm_client=FakeRecognitionLlmClient(
            RecognitionLlmExtractionResult(
                raw_response={"provider": "fake-worker"},
                recognized_fields={
                    "material_type": RecognitionFieldResult(
                        value="itinerary",
                        source="ai",
                        confidence=0.99,
                    ),
                    "expense_type": RecognitionFieldResult(
                        value="local_transport",
                        source="ai",
                        confidence=0.97,
                    ),
                },
            )
        ),
    )

    assert processor.run_once() == 1

    invoice_repository = SqlAlchemyInvoiceRepository(
        build_session_factory(runtime_config.database_url)
    )
    linked_invoices = invoice_repository.list_by_supporting_material(itinerary_material_id)
    assert linked_invoices == []


def test_recognition_async_processor_does_not_auto_link_local_transport_itinerary_when_amount_mismatches(
    tmp_path,
):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task = create_admin_task(
        client,
        payload=valid_task_payload() | {"fee_categories": ["local_transport"]},
    )
    client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    task_id = task["id"]
    invoice_material_id = upload_material(client, task_id, material_type="invoice")
    local_transport_invoice_id = create_invoice(
        client,
        invoice_material_id,
        expense_type="local_transport",
        amount_cents=4250,
        invoice_number="ASYNC-RIDE-201",
        seller_name="高德出行",
    )
    itinerary_material_id = upload_material(client, task_id, material_type="itinerary")
    processor = build_processor(
        tmp_path,
        runtime_config,
        recognition_llm_client=FakeRecognitionLlmClient(
            RecognitionLlmExtractionResult(
                raw_response={"provider": "fake-worker"},
                recognized_fields={
                    "material_type": RecognitionFieldResult(
                        value="itinerary",
                        source="ai",
                        confidence=0.99,
                    ),
                    "expense_type": RecognitionFieldResult(
                        value="local_transport",
                        source="ai",
                        confidence=0.97,
                    ),
                    "amount_cents": RecognitionFieldResult(
                        value=7286,
                        source="ai",
                        confidence=0.96,
                    ),
                },
            )
        ),
    )

    assert processor.run_once() == 1

    invoice_repository = SqlAlchemyInvoiceRepository(
        build_session_factory(runtime_config.database_url)
    )
    linked_invoices = invoice_repository.list_by_supporting_material(itinerary_material_id)
    assert linked_invoices == []
    assert invoice_repository.get(local_transport_invoice_id) is not None


def test_recognition_async_processor_backfills_itinerary_link_when_invoice_is_recognized_later(
    tmp_path,
):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task = create_admin_task(
        client,
        payload=valid_task_payload() | {"fee_categories": ["local_transport"]},
    )
    client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    task_id = task["id"]
    itinerary_material_id = upload_material(client, task_id, material_type="itinerary")
    itinerary_processor = build_processor(
        tmp_path,
        runtime_config,
        recognition_llm_client=FakeRecognitionLlmClient(
            RecognitionLlmExtractionResult(
                raw_response={"provider": "fake-worker"},
                recognized_fields={
                    "material_type": RecognitionFieldResult(
                        value="itinerary",
                        source="ai",
                        confidence=0.99,
                    ),
                    "expense_type": RecognitionFieldResult(
                        value="local_transport",
                        source="ai",
                        confidence=0.97,
                    ),
                    "amount_cents": RecognitionFieldResult(
                        value=4250,
                        source="ai",
                        confidence=0.96,
                    ),
                },
            )
        ),
    )

    assert itinerary_processor.run_once() == 1

    invoice_repository = SqlAlchemyInvoiceRepository(
        build_session_factory(runtime_config.database_url)
    )
    assert invoice_repository.list_by_supporting_material(itinerary_material_id) == []

    invoice_material_id = upload_material(client, task_id, material_type="invoice")
    invoice_processor = build_processor(
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
                    "expense_type": RecognitionFieldResult(
                        value="local_transport",
                        source="ai",
                        confidence=0.97,
                    ),
                    "invoice_number": RecognitionFieldResult(
                        value="ASYNC-RIDE-LATE-001",
                        source="ai",
                        confidence=0.98,
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
                        value=4250,
                        source="ai",
                        confidence=0.96,
                    ),
                },
            )
        ),
    )

    assert invoice_processor.run_once() == 1

    linked_invoices = invoice_repository.list_by_supporting_material(itinerary_material_id)
    assert [invoice.material_id for invoice in linked_invoices] == [invoice_material_id]


def test_recognition_async_processor_does_not_mislink_future_itinerary_to_existing_invoice(
    tmp_path,
):
    runtime_config = make_runtime_config(tmp_path)
    client = make_client(tmp_path, runtime_config=runtime_config)
    task = create_admin_task(
        client,
        payload=valid_task_payload() | {"fee_categories": ["local_transport"]},
    )
    client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    task_id = task["id"]
    invoice_a_material_id = upload_material(client, task_id, material_type="invoice")
    invoice_a_processor = build_processor(
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
                    "expense_type": RecognitionFieldResult(
                        value="local_transport",
                        source="ai",
                        confidence=0.97,
                    ),
                    "invoice_number": RecognitionFieldResult(
                        value="ASYNC-RIDE-A",
                        source="ai",
                        confidence=0.98,
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
                    "seller_name": RecognitionFieldResult(
                        value="滴滴出行",
                        source="ai",
                        confidence=0.97,
                    ),
                    "amount_cents": RecognitionFieldResult(
                        value=3000,
                        source="ai",
                        confidence=0.96,
                    ),
                },
            )
        ),
    )

    assert invoice_a_processor.run_once() == 1

    itinerary_b_material_id = upload_material(client, task_id, material_type="itinerary")
    itinerary_b_processor = build_processor(
        tmp_path,
        runtime_config,
        recognition_llm_client=FakeRecognitionLlmClient(
            RecognitionLlmExtractionResult(
                raw_response={"provider": "fake-worker"},
                recognized_fields={
                    "material_type": RecognitionFieldResult(
                        value="itinerary",
                        source="ai",
                        confidence=0.99,
                    ),
                    "expense_type": RecognitionFieldResult(
                        value="local_transport",
                        source="ai",
                        confidence=0.97,
                    ),
                    "amount_cents": RecognitionFieldResult(
                        value=5000,
                        source="ai",
                        confidence=0.96,
                    ),
                },
            )
        ),
    )

    assert itinerary_b_processor.run_once() == 1

    invoice_repository = SqlAlchemyInvoiceRepository(
        build_session_factory(runtime_config.database_url)
    )
    invoice_a_id = invoice_repository.get_by_material(invoice_a_material_id).id
    assert invoice_repository.list_by_supporting_material(itinerary_b_material_id) == []

    itinerary_a_material_id = upload_material(client, task_id, material_type="itinerary")
    itinerary_a_processor = build_processor(
        tmp_path,
        runtime_config,
        recognition_llm_client=FakeRecognitionLlmClient(
            RecognitionLlmExtractionResult(
                raw_response={"provider": "fake-worker"},
                recognized_fields={
                    "material_type": RecognitionFieldResult(
                        value="itinerary",
                        source="ai",
                        confidence=0.99,
                    ),
                    "expense_type": RecognitionFieldResult(
                        value="local_transport",
                        source="ai",
                        confidence=0.97,
                    ),
                    "amount_cents": RecognitionFieldResult(
                        value=3000,
                        source="ai",
                        confidence=0.96,
                    ),
                },
            )
        ),
    )

    assert itinerary_a_processor.run_once() == 1
    linked_to_invoice_a = invoice_repository.list_by_supporting_material(itinerary_a_material_id)
    assert [invoice.id for invoice in linked_to_invoice_a] == [invoice_a_id]

    invoice_b_material_id = upload_material(client, task_id, material_type="invoice")
    invoice_b_processor = build_processor(
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
                    "expense_type": RecognitionFieldResult(
                        value="local_transport",
                        source="ai",
                        confidence=0.97,
                    ),
                    "invoice_number": RecognitionFieldResult(
                        value="ASYNC-RIDE-B",
                        source="ai",
                        confidence=0.98,
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
                        value=5000,
                        source="ai",
                        confidence=0.96,
                    ),
                },
            )
        ),
    )

    assert invoice_b_processor.run_once() == 1

    linked_to_invoice_b = invoice_repository.list_by_supporting_material(itinerary_b_material_id)
    assert [invoice.material_id for invoice in linked_to_invoice_b] == [invoice_b_material_id]
