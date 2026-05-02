from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from trms_backend.application.export_async_jobs import ExportAsyncJobProcessor
from trms_backend.application.recognition_async_jobs import RecognitionAsyncJobProcessor
from trms_backend.application.recognition_llm import (
    RecognitionLlmClient,
    RecognitionLlmExtractionResult,
)
from trms_backend.application.recognition_preparation import RecognitionPreparationService
from trms_backend.application.recognition_runtime import resolve_recognition_llm_capability
from trms_backend.domain.recognitions import RecognitionFieldResult
from trms_backend.infrastructure.database import build_session_factory, init_database
from trms_backend.infrastructure.repositories import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyConfirmationRepository,
    SqlAlchemyExportJobRepository,
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
    auth_headers,
    create_task as create_admin_task,
    register_and_get_token,
    valid_invoice_payload,
    valid_task_payload,
)


class FakeRecognitionLlmClient(RecognitionLlmClient):
    def __init__(self, *, result: RecognitionLlmExtractionResult) -> None:
        self._result = result
        self.calls: list[dict[str, object]] = []

    def recognize(self, *, material, document_input) -> RecognitionLlmExtractionResult:
        self.calls.append(
            {
                "material_id": material.id,
                "material_type": material.material_type.value,
                "document_input": document_input.model_dump(mode="json"),
            }
        )
        return self._result


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
        llm_api_key="sk-test",
        llm_model="gpt-4.1-mini",
    )


def make_client(tmp_path, *, runtime_config=None, recognition_llm_client=None):
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
            runtime_config=runtime_config,
            recognition_llm_client=recognition_llm_client,
        )
    )


def member_auth_headers(
    client: TestClient,
    *,
    username: str = "member1",
    actor_id: str = "2250001",
) -> dict[str, str]:
    return auth_headers(
        register_and_get_token(
            client,
            username=username,
            role="member",
            actor_id=actor_id,
            member_code=actor_id,
        )
    )


def main_flow_task_payload():
    return valid_task_payload() | {
        "competition_name": "Main flow E2E scaffold",
        "member_ids": ["2250001"],
        "fee_categories": ["railway"],
        "project_info": "Main flow integration scaffold",
        "reimburser_info": "Nightly admin",
    }


def build_fake_recognition_result():
    return RecognitionLlmExtractionResult(
        raw_response={
            "provider": "fake-llm",
            "document_type": "invoice",
        },
        recognized_fields={
            "invoice_number": RecognitionFieldResult(
                value="INV-MAIN-E2E-001",
                source="ai",
                confidence=0.99,
            ),
            "buyer_name": RecognitionFieldResult(
                value="同济大学",
                source="ai",
                confidence=0.99,
            ),
            "tax_number": RecognitionFieldResult(
                value="12100000425006117D",
                source="ai",
                confidence=0.98,
            ),
            "amount_cents": RecognitionFieldResult(
                value=12345,
                source="ai",
                confidence=0.97,
            ),
            "transaction_time": RecognitionFieldResult(
                value="2026-11-01T08:00:00+00:00",
                source="ai",
                confidence=0.96,
            ),
            "expense_type": RecognitionFieldResult(
                value="railway",
                source="ai",
                confidence=0.95,
            ),
            "material_type": RecognitionFieldResult(
                value="invoice",
                source="ai",
                confidence=0.99,
            ),
        },
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
        b"BT\n/F1 12 Tf\n72 100 Td\n(Invoice INV-MAIN-E2E-001 Tongji University) Tj\n0 -16 Td\n"
        b"(Amount 123.45) Tj\nET\n"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def build_recognition_processor(
    tmp_path,
    *,
    runtime_config,
    recognition_llm_client,
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
    recognition_preparation_service = RecognitionPreparationService(
        material_repository,
        LocalMaterialFileStorage(tmp_path / "material-storage"),
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


def build_export_processor(tmp_path, *, runtime_config) -> ExportAsyncJobProcessor:
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


def move_task_status(
    client: TestClient,
    task_id: str,
    target_status: str,
    *,
    headers: dict[str, str],
):
    response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": target_status},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def list_recognition_tasks(
    client: TestClient,
    material_id: str,
    *,
    headers: dict[str, str],
):
    response = client.get(
        f"/api/materials/{material_id}/recognition-tasks",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_main_flow_e2e_scaffold_covers_submission_to_export_gate(tmp_path):
    runtime_config = make_runtime_config(tmp_path)
    fake_llm = FakeRecognitionLlmClient(result=build_fake_recognition_result())
    client = make_client(
        tmp_path,
        runtime_config=runtime_config,
        recognition_llm_client=fake_llm,
    )
    admin_headers = admin_auth_headers(client)
    member_headers = member_auth_headers(client)

    created = create_admin_task(
        client,
        payload=main_flow_task_payload(),
        headers=admin_headers,
    )
    task_id = created["id"]
    assert created["status"] == "draft"

    opened = move_task_status(client, task_id, "open", headers=admin_headers)
    assert opened["status"] == "open"

    upload_response = client.post(
        f"/api/tasks/{task_id}/materials",
        headers=member_headers,
        data={
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", build_text_pdf_bytes(), "application/pdf")},
    )
    assert upload_response.status_code == 201
    material_id = upload_response.json()["items"][0]["id"]

    initial_recognition_listing = list_recognition_tasks(
        client,
        material_id,
        headers=member_headers,
    )
    assert initial_recognition_listing["latest_effective"] is None
    assert len(initial_recognition_listing["items"]) == 1
    assert initial_recognition_listing["items"][0]["status"] == "pending"
    recognition_task_id = initial_recognition_listing["items"][0]["id"]

    recognition_processor = build_recognition_processor(
        tmp_path,
        runtime_config=runtime_config,
        recognition_llm_client=fake_llm,
    )
    assert recognition_processor.run_once() == 1
    assert recognition_processor.run_once() == 0

    recognition_listing = list_recognition_tasks(
        client,
        material_id,
        headers=admin_headers,
    )
    assert recognition_listing["latest_effective"]["id"] == recognition_task_id
    assert recognition_listing["latest_effective"]["status"] == "succeeded"
    assert recognition_listing["latest_effective"]["recognized_fields"]["buyer_name"]["value"] == (
        "同济大学"
    )
    assert recognition_listing["latest_effective"]["raw_response"]["llm"] == {
        "provider": "fake-llm",
        "document_type": "invoice",
    }
    assert fake_llm.calls[0]["material_id"] == material_id
    assert fake_llm.calls[0]["document_input"]["source"] == "pdf_text"

    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        headers=admin_headers,
        json=valid_invoice_payload()
        | {
            "actor_id": "admin-1",
            "invoice_number": "INV-MAIN-E2E-001",
        },
    )
    assert invoice_response.status_code == 201
    invoice_body = invoice_response.json()
    invoice_id = invoice_body["invoice"]["id"]
    validations_by_code = {
        item["rule_code"]: item for item in invoice_body["validations"]
    }
    assert validations_by_code["invoice_title_match"]["status"] == "passed"
    assert validations_by_code["invoice_tax_number_match"]["status"] == "passed"
    assert validations_by_code["invoice_number_unique"]["status"] == "passed"

    split_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        headers=member_headers,
        json={
            "items": [
                {
                    "member_id": "2250001",
                    "amount_cents": 12345,
                    "note": "self paid",
                }
            ]
        },
    )
    assert split_response.status_code == 200
    split_id = split_response.json()["items"][0]["id"]

    expense_details_after_split = client.get(
        f"/api/tasks/{task_id}/expense-details",
        headers=member_headers,
    )
    assert expense_details_after_split.status_code == 200
    detail_body = expense_details_after_split.json()
    assert detail_body["actor_id"] == "2250001"
    assert detail_body["total_amount_cents"] == 12345
    assert len(detail_body["items"]) == 1
    assert detail_body["items"][0]["split_id"] == split_id
    assert detail_body["items"][0]["confirmation"]["status"] == "confirmed"

    review_summary_after_split = client.get(
        f"/api/tasks/{task_id}/review-summary",
        headers=admin_headers,
    )
    assert review_summary_after_split.status_code == 200
    review_body_after_split = review_summary_after_split.json()
    assert review_body_after_split["counts"]["material_count"] == 1
    assert review_body_after_split["counts"]["invoice_count"] == 1
    assert review_body_after_split["counts"]["validation_count"] >= 2
    assert review_body_after_split["counts"]["missing_confirmation_count"] == 0
    assert review_body_after_split["counts"]["pending_confirmation_count"] == 0

    blocked_export_response = client.get(
        f"/api/tasks/{task_id}/exports/capabilities",
        headers=admin_headers,
    )
    assert blocked_export_response.status_code == 200
    blocked_export_body = blocked_export_response.json()
    assert blocked_export_body["current_task_status"] == "open"
    assert blocked_export_body["export_allowed"] is False
    assert blocked_export_body["blocking_reasons"] == [
        "当前任务还未进入“可导出”或“已完成”阶段，暂时不能生成正式导出材料。"
    ]

    reviewing = move_task_status(client, task_id, "reviewing", headers=admin_headers)
    assert reviewing["status"] == "reviewing"

    ready_to_export = move_task_status(
        client,
        task_id,
        "ready_to_export",
        headers=admin_headers,
    )
    assert ready_to_export["status"] == "ready_to_export"

    review_summary_after_confirmation = client.get(
        f"/api/tasks/{task_id}/review-summary",
        headers=admin_headers,
    )
    assert review_summary_after_confirmation.status_code == 200
    review_body_after_confirmation = review_summary_after_confirmation.json()
    assert review_body_after_confirmation["counts"]["confirmed_split_count"] == 1
    assert review_body_after_confirmation["counts"]["missing_confirmation_count"] == 0
    assert review_body_after_confirmation["counts"]["pending_confirmation_count"] == 0
    assert review_body_after_confirmation["invoices"][0]["splits"][0]["confirmation"]["status"] == (
        "confirmed"
    )

    export_capabilities_response = client.get(
        f"/api/tasks/{task_id}/exports/capabilities",
        headers=admin_headers,
    )
    assert export_capabilities_response.status_code == 200
    export_capabilities = export_capabilities_response.json()
    assert export_capabilities["current_task_status"] == "ready_to_export"
    assert export_capabilities["export_allowed"] is True
    assert export_capabilities["blocking_reasons"] == []

    supported_kinds = {item["kind"]: item for item in export_capabilities["supported_exports"]}
    assert set(supported_kinds) == {
        "reimbursement_summary",
        "member_details",
        "invoice_details",
        "missing_materials",
        "finance_draft",
        "merged_pdf",
        "reimbursement_package",
    }
    assert supported_kinds["merged_pdf"]["implemented"] is True
    assert supported_kinds["merged_pdf"]["implemented_formats"] == ["pdf"]
    assert supported_kinds["reimbursement_package"]["implemented"] is True
    assert supported_kinds["reimbursement_package"]["implemented_formats"] == ["zip"]

    export_job_response = client.post(
        f"/api/tasks/{task_id}/exports",
        headers=admin_headers,
        json={
            "kind": "reimbursement_summary",
            "format": "csv",
            "parameters": {},
        },
    )
    assert export_job_response.status_code == 201
    export_job = export_job_response.json()
    assert export_job["status"] == "pending"
    export_job_id = export_job["id"]

    export_processor = build_export_processor(
        tmp_path,
        runtime_config=runtime_config,
    )
    assert export_processor.run_once() == 1
    assert export_processor.run_once() == 0

    export_status_response = client.get(
        f"/api/tasks/exports/{export_job_id}",
        headers=admin_headers,
    )
    assert export_status_response.status_code == 200
    export_status = export_status_response.json()
    assert export_status["status"] == "succeeded"
    assert export_status["failure_reason"] is None
    assert export_status["artifact"]["filename"] == f"{task_id}-reimbursement-summary.csv"
    assert export_status["artifact"]["content_type"] == "text/csv"

    export_artifact_response = client.get(
        f"/api/tasks/exports/{export_job_id}/artifact",
        headers=admin_headers,
    )
    assert export_artifact_response.status_code == 200
    assert export_artifact_response.headers["content-type"].startswith("text/csv")
    assert (
        export_artifact_response.headers["content-disposition"]
        == f'attachment; filename="{task_id}-reimbursement-summary.csv"'
    )
    assert "expense_type,total_amount_cents,2250001" in export_artifact_response.text
    assert "railway,12345,12345" in export_artifact_response.text
    assert "grand_total,12345,12345" in export_artifact_response.text
