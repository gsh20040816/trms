import json

import httpx
import pytest

from trms_backend.application.recognition_llm import (
    OpenAiCompatibleRecognitionClient,
    RecognitionDocumentInput,
    RecognitionLlmExecutionError,
)
from trms_backend.domain.materials import MaterialRecord, MaterialStatus, MaterialType, SubmissionChannel
from trms_backend.domain.recognitions import RecognitionFieldStatus
from trms_backend.runtime_config import load_runtime_config


def build_provider_config():
    config = load_runtime_config(
        environment="test",
        database_url="sqlite:///./test.db",
        material_storage_dir="./data/materials",
        cors_allowed_origins="http://127.0.0.1:5173",
        public_api_base_url="http://127.0.0.1:8000/api",
        api_host="127.0.0.1",
        api_port=8000,
        llm_api_key="sk-test",
        llm_model="gpt-4.1-mini",
        llm_max_retries=1,
    )
    assert config.llm_provider is not None
    return config.llm_provider


def build_material() -> MaterialRecord:
    return MaterialRecord(
        id="material-1",
        status=MaterialStatus.ASSIGNED,
        task_id="task-1",
        submitter_id="2250001",
        task_id_hint=None,
        submitter_id_hint=None,
        channel=SubmissionChannel.WEB,
        material_type=MaterialType.INVOICE,
        storage_key="task-1/invoice.pdf",
        original_filename="invoice.pdf",
        content_type="application/pdf",
        size_bytes=128,
        sha256="a" * 64,
        duplicate_of=None,
        claimed_by=None,
        claimed_at=None,
        created_at="2026-04-28T00:00:00Z",
    )


def build_document_input() -> RecognitionDocumentInput:
    return RecognitionDocumentInput(
        source="pdf_text",
        text="Invoice INV-001 Tongji University Amount 123.45",
        page_count=1,
        text_character_count=46,
    )


def test_openai_compatible_recognition_client_parses_json_schema_response():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["path"] = request.url.path
        captured_request["authorization"] = request.headers["Authorization"]
        captured_request["payload"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "output": {
                                        "invoice_number": {
                                            "value": "INV-001",
                                            "confidence": 0.98,
                                        },
                                        "location": {
                                            "value": "上海",
                                            "confidence": 0.42,
                                        },
                                        "material_type": {
                                            "value": "invoice",
                                            "confidence": 0.95,
                                        },
                                    }
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )

    client = OpenAiCompatibleRecognitionClient(
        build_provider_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://llm.example.com/v1",
        ),
    )

    result = client.recognize(material=build_material(), document_input=build_document_input())

    assert captured_request["path"] == "/v1/chat/completions"
    assert captured_request["authorization"] == "Bearer sk-test"
    assert captured_request["payload"]["response_format"]["type"] == "json_schema"
    assert result.recognized_fields["invoice_number"].value == "INV-001"
    assert result.recognized_fields["location"].status is RecognitionFieldStatus.NEEDS_CONFIRMATION
    assert result.recognized_fields["material_type"].value == "invoice"
    assert result.raw_response["attempts"] == 1


def test_openai_compatible_recognition_client_rejects_non_json_content():
    client = OpenAiCompatibleRecognitionClient(
        build_provider_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"choices": [{"message": {"content": "not-json"}}]},
                )
            ),
            base_url="https://llm.example.com/v1",
        ),
    )

    with pytest.raises(RecognitionLlmExecutionError) as error:
        client.recognize(material=build_material(), document_input=build_document_input())

    assert error.value.failure.reason == "llm_output_not_json"


def test_openai_compatible_recognition_client_rejects_missing_fields_output():
    client = OpenAiCompatibleRecognitionClient(
        build_provider_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"choices": [{"message": {"content": json.dumps({"output": {}})}}]},
                )
            ),
            base_url="https://llm.example.com/v1",
        ),
    )

    with pytest.raises(RecognitionLlmExecutionError) as error:
        client.recognize(material=build_material(), document_input=build_document_input())

    assert error.value.failure.reason == "llm_output_missing_fields"


def test_openai_compatible_recognition_client_reports_timeout_after_retries():
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = OpenAiCompatibleRecognitionClient(
        build_provider_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(timeout_handler),
            base_url="https://llm.example.com/v1",
        ),
    )

    with pytest.raises(RecognitionLlmExecutionError) as error:
        client.recognize(material=build_material(), document_input=build_document_input())

    assert error.value.failure.reason == "llm_timeout"
    assert error.value.raw_response["attempts"] == 2
