from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject

from trms_backend.application.recognition_llm import (
    RecognitionLlmClient,
    RecognitionLlmExecutionError,
    RecognitionLlmExtractionResult,
)
from trms_backend.domain.recognitions import (
    RecognitionFailureDetail,
    RecognitionFieldResult,
    RecognitionFieldStatus,
)
from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from test_tasks_api import (
    admin_auth_headers,
    auth_headers,
    register_and_get_token,
    valid_task_payload,
)


class FakeRecognitionLlmClient(RecognitionLlmClient):
    def __init__(
        self,
        *,
        result: RecognitionLlmExtractionResult | None = None,
        error: RecognitionLlmExecutionError | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[dict[str, object]] = []

    def recognize(self, *, material, document_input) -> RecognitionLlmExtractionResult:
        self.calls.append(
            {
                "material_id": material.id,
                "material_type": material.material_type.value,
                "document_input": document_input.model_dump(mode="json"),
            }
        )
        if self._error is not None:
            raise self._error
        if self._result is None:
            raise AssertionError("fake LLM client requires either result or error")
        return self._result


def make_client(tmp_path, *, runtime_config=None, recognition_llm_client=None):
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
            runtime_config=runtime_config,
            recognition_llm_client=recognition_llm_client,
        )
    )


def make_llm_runtime_config(tmp_path):
    return load_runtime_config(
        environment="test",
        database_url=f"sqlite:///{tmp_path}/test.db",
        material_storage_dir=tmp_path / "material-storage",
        cors_allowed_origins="http://127.0.0.1:5173",
        public_api_base_url="http://127.0.0.1:8000/api",
        api_host="127.0.0.1",
        api_port=8000,
        llm_api_key="sk-test",
        llm_model="gpt-4.1-mini",
    )


def create_task(client: TestClient) -> str:
    task = client.post("/api/tasks", json=valid_task_payload()).json()
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
    filename: str,
    content: bytes,
    content_type: str,
) -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": (filename, content, content_type)},
    )
    assert response.status_code == 201
    return response.json()["items"][0]["id"]


def latest_recognition_task_id(client: TestClient, material_id: str) -> str:
    response = client.get(f"/api/materials/{material_id}/recognition-tasks")
    assert response.status_code == 200
    return response.json()["items"][-1]["id"]


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
        b"BT\n/F1 12 Tf\n72 100 Td\n(Invoice INV-001 Tongji University) Tj\n0 -16 Td\n"
        b"(Amount 123.45) Tj\nET\n"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def build_blank_pdf_bytes(*, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    if encrypted:
        writer.encrypt("secret")
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def build_image_only_pdf_bytes() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=100, height=100)
    image_stream = DecodedStreamObject()
    image_stream.set_data(bytes([255, 255, 255]))
    image_stream.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(1),
            NameObject("/Height"): NumberObject(1),
            NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
            NameObject("/BitsPerComponent"): NumberObject(8),
        }
    )
    image_ref = writer._add_object(image_stream)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): image_ref}),
        }
    )
    content_stream = DecodedStreamObject()
    content_stream.set_data(b"q\n100 0 0 100 0 0 cm\n/Im0 Do\nQ\n")
    page[NameObject("/Contents")] = writer._add_object(content_stream)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_execute_recognition_task_extracts_pdf_text_into_preparation_payload(tmp_path):
    client = make_client(tmp_path)
    sample_path = tmp_path / "text-invoice.pdf"
    sample_path.write_bytes(build_text_pdf_bytes())
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="application/pdf",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(
        f"/api/recognition-tasks/{recognition_task_id}/execute",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["status"] == "failed"
    assert item["failure"] == {
        "stage": "ai",
        "reason": "llm_provider_not_configured",
    }
    preparation = item["raw_response"]["preparation"]
    assert preparation["material_id"] == material_id
    assert preparation["original_filename"] == sample_path.name
    assert preparation["content_type"] == "application/pdf"
    assert preparation["recognition_input"] == {
        "source": "pdf_text",
        "text": "Invoice INV-001 Tongji University\nAmount 123.45",
        "page_count": 1,
        "text_character_count": 47,
    }


def test_execute_recognition_task_requires_admin_bearer(tmp_path):
    client = make_client(tmp_path)
    sample_path = tmp_path / "text-invoice.pdf"
    sample_path.write_bytes(build_text_pdf_bytes())
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="application/pdf",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    anonymous_response = client.post(f"/api/recognition-tasks/{recognition_task_id}/execute")
    assert anonymous_response.status_code == 401
    assert anonymous_response.json()["detail"] == "invalid or missing bearer token"

    forbidden_response = client.post(
        f"/api/recognition-tasks/{recognition_task_id}/execute",
        headers=member_auth_headers(client),
    )
    assert forbidden_response.status_code == 403
    assert forbidden_response.json()["detail"] == (
        "actor is not allowed to manage recognition tasks for this material"
    )


def test_execute_recognition_task_persists_structured_llm_result(tmp_path):
    fake_llm = FakeRecognitionLlmClient(
        result=RecognitionLlmExtractionResult(
            raw_response={"provider": "fake-openai", "attempts": 1},
            recognized_fields={
                "invoice_number": RecognitionFieldResult(
                    value="INV-001",
                    source="ai",
                    confidence=0.99,
                ),
                "amount_cents": RecognitionFieldResult(
                    value=12345,
                    source="ai",
                    confidence=0.97,
                ),
                "buyer_name": RecognitionFieldResult(
                    value="同济大学",
                    source="ai",
                    confidence=0.96,
                ),
                "tax_number": RecognitionFieldResult(
                    value="12100000425006117D",
                    source="ai",
                    confidence=0.95,
                ),
                "transaction_time": RecognitionFieldResult(
                    value="2026-11-01T08:00:00Z",
                    source="ai",
                    confidence=0.93,
                ),
                "location": RecognitionFieldResult(
                    value="上海",
                    source="ai",
                    confidence=0.92,
                ),
                "expense_type": RecognitionFieldResult(
                    value="registration",
                    source="ai",
                    confidence=0.91,
                ),
                "material_type": RecognitionFieldResult(
                    value="invoice",
                    source="ai",
                    confidence=0.98,
                ),
            },
        )
    )
    client = make_client(
        tmp_path,
        runtime_config=make_llm_runtime_config(tmp_path),
        recognition_llm_client=fake_llm,
    )
    sample_path = tmp_path / "structured-invoice.pdf"
    sample_path.write_bytes(build_text_pdf_bytes())
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="application/pdf",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(
        f"/api/recognition-tasks/{recognition_task_id}/execute",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["status"] == "succeeded"
    assert item["failure"] is None
    assert item["recognized_fields"]["invoice_number"]["value"] == "INV-001"
    assert item["recognized_fields"]["amount_cents"]["value"] == 12345
    assert item["recognized_fields"]["material_type"]["value"] == "invoice"
    assert item["raw_response"]["llm"] == {"provider": "fake-openai", "attempts": 1}
    assert fake_llm.calls[0]["material_id"] == material_id


def test_execute_recognition_task_marks_low_confidence_result_as_needs_confirmation(tmp_path):
    fake_llm = FakeRecognitionLlmClient(
        result=RecognitionLlmExtractionResult(
            raw_response={"provider": "fake-openai", "attempts": 1},
            recognized_fields={
                "invoice_number": RecognitionFieldResult(
                    value="INV-LOW-001",
                    source="ai",
                    confidence=0.98,
                ),
                "buyer_name": RecognitionFieldResult(
                    value="同济大学",
                    source="ai",
                    confidence=0.41,
                    status=RecognitionFieldStatus.NEEDS_CONFIRMATION,
                ),
            },
        )
    )
    client = make_client(
        tmp_path,
        runtime_config=make_llm_runtime_config(tmp_path),
        recognition_llm_client=fake_llm,
    )
    sample_path = tmp_path / "needs-confirmation.pdf"
    sample_path.write_bytes(build_text_pdf_bytes())
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="application/pdf",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(
        f"/api/recognition-tasks/{recognition_task_id}/execute",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["status"] == "needs_confirmation"
    assert item["recognized_fields"]["buyer_name"]["status"] == "needs_confirmation"


def test_execute_recognition_task_records_llm_failure_reason(tmp_path):
    fake_llm = FakeRecognitionLlmClient(
        error=RecognitionLlmExecutionError(
            failure=RecognitionFailureDetail(stage="ai", reason="llm_output_not_json"),
            raw_response={"response": {"choices": [{"message": {"content": "not-json"}}]}},
        )
    )
    client = make_client(
        tmp_path,
        runtime_config=make_llm_runtime_config(tmp_path),
        recognition_llm_client=fake_llm,
    )
    sample_path = tmp_path / "llm-failure.pdf"
    sample_path.write_bytes(build_text_pdf_bytes())
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="application/pdf",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(
        f"/api/recognition-tasks/{recognition_task_id}/execute",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["status"] == "failed"
    assert item["failure"] == {
        "stage": "ai",
        "reason": "llm_output_not_json",
    }
    assert item["raw_response"]["llm"]["response"]["choices"][0]["message"]["content"] == "not-json"


def test_execute_recognition_task_marks_image_upload_as_ocr_not_configured(tmp_path):
    client = make_client(tmp_path)
    sample_path = tmp_path / "invoice-scan.png"
    sample_path.write_bytes(b"fake-image-scan")
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="image/png",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(
        f"/api/recognition-tasks/{recognition_task_id}/execute",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["status"] == "failed"
    assert item["failure"] == {
        "stage": "ocr",
        "reason": "ocr_not_configured",
    }
    assert item["raw_response"]["preparation"]["material_id"] == material_id


def test_execute_recognition_task_marks_image_only_pdf_as_ocr_not_configured(tmp_path):
    client = make_client(tmp_path)
    sample_path = tmp_path / "image-only.pdf"
    sample_path.write_bytes(build_image_only_pdf_bytes())
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="application/pdf",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(
        f"/api/recognition-tasks/{recognition_task_id}/execute",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["item"]["failure"] == {
        "stage": "ocr",
        "reason": "ocr_not_configured",
    }


def test_execute_recognition_task_records_pdf_parse_failure_for_corrupted_pdf(tmp_path):
    client = make_client(tmp_path)
    sample_path = tmp_path / "broken.pdf"
    sample_path.write_bytes(b"not a pdf")
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="application/pdf",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(
        f"/api/recognition-tasks/{recognition_task_id}/execute",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["failure"] == {
        "stage": "pdf",
        "reason": "pdf_parse_failed",
    }
    assert item["raw_response"]["preparation"]["material_id"] == material_id


def test_execute_recognition_task_records_blank_pdf(tmp_path):
    client = make_client(tmp_path)
    sample_path = tmp_path / "blank.pdf"
    sample_path.write_bytes(build_blank_pdf_bytes())
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="application/pdf",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(
        f"/api/recognition-tasks/{recognition_task_id}/execute",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["failure"] == {
        "stage": "pdf",
        "reason": "blank_pdf",
    }
    assert item["raw_response"]["preparation"]["material_id"] == material_id


def test_execute_recognition_task_records_encrypted_pdf(tmp_path):
    client = make_client(tmp_path)
    sample_path = tmp_path / "encrypted.pdf"
    sample_path.write_bytes(build_blank_pdf_bytes(encrypted=True))
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="application/pdf",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(
        f"/api/recognition-tasks/{recognition_task_id}/execute",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["failure"] == {
        "stage": "pdf",
        "reason": "encrypted_pdf",
    }
    assert item["raw_response"]["preparation"]["material_id"] == material_id
