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
    text = "Invoice INV-001 Tongji University Amount 123.45"
    return RecognitionDocumentInput(
        source="pdf_text",
        text=text,
        page_count=1,
        text_character_count=len(text),
    )


def test_openai_compatible_recognition_client_uses_json_object_response_format():
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
    assert captured_request["payload"]["response_format"] == {"type": "json_object"}
    assert "Prompt version: trms-recognition-v2." in captured_request["payload"]["messages"][0]["content"]
    assert "Do not guess missing fields." in captured_request["payload"]["messages"][0]["content"]
    assert result.recognized_fields["invoice_number"].value == "INV-001"
    assert result.recognized_fields["location"].status is RecognitionFieldStatus.NEEDS_CONFIRMATION
    assert result.recognized_fields["material_type"].value == "invoice"
    assert result.raw_response["attempts"] == 1
    assert result.raw_response["request"]["user_prompt"]["prompt_version"] == "trms-recognition-v2"
    assert result.raw_response["request"]["user_prompt"]["recognition_input"]["source"] == "pdf_text"


def test_openai_compatible_recognition_client_includes_chinese_invoice_rules_in_prompt():
    captured_request = {}
    chinese_text = "电子发票 发票号码 12345678 购买方名称 同济大学 纳税人识别号 12100000425006117D 价税合计￥123.45"

    def handler(request: httpx.Request) -> httpx.Response:
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
                                        "buyer_name": {
                                            "value": "同济大学",
                                            "confidence": 0.96,
                                        }
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
    chinese_input = RecognitionDocumentInput(
        source="pdf_text",
        text=chinese_text,
        page_count=1,
        text_character_count=len(chinese_text),
    )

    client.recognize(material=build_material(), document_input=chinese_input)

    system_prompt = captured_request["payload"]["messages"][0]["content"]
    user_prompt = json.loads(captured_request["payload"]["messages"][1]["content"])
    assert "VAT electronic invoices" in system_prompt
    assert "For amount_cents, convert RMB yuan to integer cents" in system_prompt
    assert "For buyer_name and tax_number, only extract them when the invoice header or tax identifier is explicitly visible." in system_prompt
    assert user_prompt == {
        "material_id": "material-1",
        "material_type": "invoice",
        "original_filename": "invoice.pdf",
        "content_type": "application/pdf",
        "recognition_input": {
            "source": "pdf_text",
            "text": chinese_text,
            "page_count": 1,
            "text_character_count": len(chinese_text),
        },
        "instructions": [
            "Return JSON only.",
            "Do not fabricate fields that are not supported by the provided document.",
            "Use amount_cents as integer cents.",
            "Use ISO 8601 with timezone for transaction_time when available.",
            "Use TRMS enums for expense_type and material_type.",
            "For Chinese invoices, only extract buyer_name and tax_number when they are explicitly visible on the document.",
            "If the document only shows a date but not a complete time, keep transaction_time absent instead of inventing a time.",
            "For RMB amounts, normalize yuan to integer cents and ignore currency symbols such as 元, ￥ and commas.",
        ],
        "prompt_version": "trms-recognition-v2",
    }


def test_openai_compatible_recognition_client_sends_pdf_file_input_for_scanned_pdf():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
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
                                            "value": "INV-SCAN-001",
                                            "confidence": 0.93,
                                        }
                                    }
                                }
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
    document_input = RecognitionDocumentInput(
        source="pdf_file",
        file_name="scan.pdf",
        media_type="application/pdf",
        data_url="data:application/pdf;base64,c2Nhbi1wZGY=",
        byte_count=8,
        page_count=2,
    )

    result = client.recognize(material=build_material(), document_input=document_input)

    user_content = captured_request["payload"]["messages"][1]["content"]
    assert isinstance(user_content, list)
    assert user_content[0]["type"] == "text"
    assert user_content[1] == {
        "type": "file",
        "file": {
            "filename": "scan.pdf",
            "file_data": "data:application/pdf;base64,c2Nhbi1wZGY=",
        },
    }
    assert result.recognized_fields["invoice_number"].value == "INV-SCAN-001"


def test_openai_compatible_recognition_client_sends_image_input_for_uploaded_image():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
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
                                        "material_type": {
                                            "value": "invoice",
                                            "confidence": 0.92,
                                        }
                                    }
                                }
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
    document_input = RecognitionDocumentInput(
        source="image_file",
        file_name="invoice.png",
        media_type="image/png",
        data_url="data:image/png;base64,aW1hZ2UtYnl0ZXM=",
        byte_count=11,
    )

    result = client.recognize(material=build_material(), document_input=document_input)

    user_content = captured_request["payload"]["messages"][1]["content"]
    assert isinstance(user_content, list)
    assert user_content[0]["type"] == "text"
    assert user_content[1] == {
        "type": "image_url",
        "image_url": {
            "url": "data:image/png;base64,aW1hZ2UtYnl0ZXM=",
            "detail": "high",
        },
    }
    assert result.recognized_fields["material_type"].value == "invoice"


def test_deepseek_compatible_recognition_client_uses_json_object_response_format():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
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
                                            "confidence": 0.91,
                                        }
                                    }
                                }
                            )
                        }
                    }
                ]
            },
        )

    provider_config = build_provider_config().model_copy(
        update={"base_url": "https://api.deepseek.com"}
    )
    client = OpenAiCompatibleRecognitionClient(
        provider_config,
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://api.deepseek.com",
        ),
    )

    result = client.recognize(material=build_material(), document_input=build_document_input())

    assert captured_request["payload"]["response_format"] == {"type": "json_object"}
    assert result.recognized_fields["invoice_number"].value == "INV-001"


def test_deepseek_compatible_recognition_client_accepts_direct_field_object():
    provider_config = build_provider_config().model_copy(
        update={"base_url": "https://api.deepseek.com"}
    )
    client = OpenAiCompatibleRecognitionClient(
        provider_config,
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "choices": [
                            {
                                "message": {
                                    "content": json.dumps(
                                        {
                                            "invoice_number": {
                                                "value": "INV-002",
                                                "confidence": 0.88,
                                            }
                                        }
                                    )
                                }
                            }
                        ]
                    },
                )
            ),
            base_url="https://api.deepseek.com",
        ),
    )

    result = client.recognize(material=build_material(), document_input=build_document_input())

    assert result.recognized_fields["invoice_number"].value == "INV-002"


def test_deepseek_compatible_recognition_client_normalizes_textual_confidence_and_chinese_labels():
    provider_config = build_provider_config().model_copy(
        update={"base_url": "https://api.deepseek.com"}
    )
    client = OpenAiCompatibleRecognitionClient(
        provider_config,
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "choices": [
                            {
                                "message": {
                                    "content": json.dumps(
                                        {
                                            "output": {
                                                "invoice_number": {
                                                    "value": "25112000000125800852",
                                                    "confidence": "high",
                                                },
                                                "amount_cents": {
                                                    "value": 50000,
                                                    "confidence": "high",
                                                },
                                                "buyer_name": {
                                                    "value": "同济大学",
                                                    "confidence": "high",
                                                },
                                                "tax_number": {
                                                    "value": "12100000425006125J",
                                                    "confidence": "high",
                                                },
                                                "expense_type": {
                                                    "value": "培训费",
                                                    "confidence": "high",
                                                },
                                                "material_type": {
                                                    "value": "电子发票",
                                                    "confidence": "high",
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
            ),
            base_url="https://api.deepseek.com",
        ),
    )

    result = client.recognize(material=build_material(), document_input=build_document_input())

    assert result.recognized_fields["invoice_number"].confidence == 0.95
    assert result.recognized_fields["amount_cents"].confidence == 0.95
    assert result.recognized_fields["material_type"].value == "invoice"
    assert "expense_type" not in result.recognized_fields


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
    assert error.value.raw_response["request"]["user_prompt"]["prompt_version"] == "trms-recognition-v2"
    assert error.value.raw_response["raw_content"] == "not-json"


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
    assert error.value.raw_response["request"]["user_prompt"]["prompt_version"] == "trms-recognition-v2"
    assert error.value.raw_response["parsed_content"]["output"]["invoice_number"] is None
    assert error.value.raw_response["parsed_content"]["output"]["amount_cents"] is None


def test_openai_compatible_recognition_client_reports_invalid_schema_details():
    client = OpenAiCompatibleRecognitionClient(
        build_provider_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "choices": [
                            {
                                "message": {
                                    "content": json.dumps(
                                        {
                                            "output": {
                                                "amount_cents": {
                                                    "value": "not-an-integer",
                                                    "confidence": 0.91,
                                                }
                                            }
                                        }
                                    )
                                }
                            }
                        ]
                    },
                )
            ),
            base_url="https://llm.example.com/v1",
        ),
    )

    with pytest.raises(RecognitionLlmExecutionError) as error:
        client.recognize(material=build_material(), document_input=build_document_input())

    assert error.value.failure.reason == "llm_output_invalid"
    assert error.value.raw_response["request"]["user_prompt"]["prompt_version"] == "trms-recognition-v2"
    assert error.value.raw_response["parsed_content"] == {
        "output": {
            "amount_cents": {
                "value": "not-an-integer",
                "confidence": 0.91,
            }
        }
    }
    assert error.value.raw_response["validation_errors"][0]["type"] == "int_parsing"


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
