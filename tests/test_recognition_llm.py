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


def build_classification_output(
    *,
    document_family: str = "invoice",
    material_type: str = "invoice",
    expense_type_candidate: str = "registration",
    is_reimbursement_voucher: bool = True,
    classification_confidence: float = 0.97,
    field_confidence: float = 0.97,
):
    return {
        "output": {
            "document_family": {
                "value": document_family,
                "confidence": field_confidence,
            },
            "material_type": {
                "value": material_type,
                "confidence": field_confidence,
            },
            "expense_type_candidate": {
                "value": expense_type_candidate,
                "confidence": field_confidence,
            },
            "is_reimbursement_voucher": {
                "value": is_reimbursement_voucher,
                "confidence": field_confidence,
            },
            "classification_confidence": {
                "value": classification_confidence,
                "confidence": field_confidence,
            },
        }
    }


def build_two_stage_handler(
    *,
    classification_content: dict,
    extraction_content: dict,
):
    call_count = {"value": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["value"] += 1
        content = classification_content if call_count["value"] == 1 else extraction_content
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(content, ensure_ascii=False),
                        }
                    }
                ]
            },
        )

    return handler


def _deepseek_two_stage_response(
    request: httpx.Request,
    call_count: dict[str, int],
) -> httpx.Response:
    call_count["value"] += 1
    if call_count["value"] == 1:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                build_classification_output(
                                    document_family="发票",
                                    material_type="电子发票",
                                    expense_type_candidate="报名费",
                                    classification_confidence=0.95,
                                    field_confidence=0.95,
                                ),
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )
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
                                }
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        },
    )


def test_openai_compatible_recognition_client_uses_json_object_response_format():
    captured_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        captured_requests.append(
            {
                "path": request.url.path,
                "authorization": request.headers["Authorization"],
                "payload": payload,
            }
        )
        if len(captured_requests) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    build_classification_output(),
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
            )
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

    assert len(captured_requests) == 2
    assert captured_requests[0]["path"] == "/v1/chat/completions"
    assert captured_requests[0]["authorization"] == "Bearer sk-test"
    assert captured_requests[0]["payload"]["response_format"] == {"type": "json_object"}
    assert captured_requests[1]["payload"]["response_format"] == {"type": "json_object"}
    assert "Prompt version: trms-recognition-v3." in captured_requests[0]["payload"]["messages"][0]["content"]
    assert "Stage 1 only" in captured_requests[0]["payload"]["messages"][1]["content"]
    assert "Selected schema: invoice." in captured_requests[1]["payload"]["messages"][0]["content"]
    assert result.recognized_fields["invoice_number"].value == "INV-001"
    assert result.recognized_fields["location"].status is RecognitionFieldStatus.NEEDS_CONFIRMATION
    assert result.recognized_fields["material_type"].value == "invoice"
    assert result.recognized_fields["document_family"].value == "invoice"
    assert result.recognized_fields["expense_type_candidate"].value == "registration"
    assert result.recognized_fields["is_reimbursement_voucher"].value is True
    assert result.recognized_fields["classification_confidence"].value == 0.97
    assert result.raw_response["classification"]["attempts"] == 1
    assert result.raw_response["classification"]["request"]["user_prompt"]["prompt_version"] == (
        "trms-recognition-v3"
    )
    assert (
        result.raw_response["classification"]["request"]["user_prompt"]["recognition_input"]["source"]
        == "pdf_text"
    )
    assert result.raw_response["selected_schema"]["name"] == "invoice"
    assert result.raw_response["extraction"]["attempts"] == 1


def test_openai_compatible_recognition_client_includes_chinese_invoice_rules_in_prompt():
    captured_requests = []
    chinese_text = "电子发票 发票号码 12345678 购买方名称 同济大学 纳税人识别号 12100000425006117D 价税合计￥123.45"

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        captured_requests.append(payload)
        if len(captured_requests) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    build_classification_output(),
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
            )
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

    classification_user_prompt = json.loads(captured_requests[0]["messages"][1]["content"])
    extraction_system_prompt = captured_requests[1]["messages"][0]["content"]
    extraction_user_prompt = json.loads(captured_requests[1]["messages"][1]["content"])
    assert "document_family must be one of" in captured_requests[0]["messages"][0]["content"]
    assert "Selected schema: invoice." in extraction_system_prompt
    assert "For buyer_name and tax_number, only extract them when the invoice header or tax identifier is explicitly visible." in extraction_system_prompt
    assert classification_user_prompt == {
        "material_id": "material-1",
        "uploaded_material_type": "invoice",
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
            "Stage 1 only: classify the document before extracting detailed metadata.",
            "Always populate document_family, material_type, expense_type_candidate, is_reimbursement_voucher, and classification_confidence.",
            "Use only TRMS enums for document_family, material_type, and expense_type_candidate.",
            "Set is_reimbursement_voucher to true only when the document itself can directly serve as a reimbursement voucher.",
            "If a document shows a tax authority seal or equivalent tax-supervision mark, classify it as invoice.",
            "Treat railway e-tickets, railway electronic itineraries, and airline e-ticket reimbursement vouchers as invoice materials instead of itinerary or other_attachment when they are direct reimbursement vouchers.",
            "classification_confidence.value must be a float between 0 and 1 describing the overall confidence of the classification result.",
        ],
        "prompt_version": "trms-recognition-v3",
        "stage": "classification",
    }
    assert extraction_user_prompt["stage"] == "metadata_extraction"
    assert extraction_user_prompt["classification_result"]["material_type"]["value"] == "invoice"
    assert extraction_user_prompt["selected_schema"]["name"] == "invoice"
    assert extraction_user_prompt["selected_schema"]["allowed_fields"] == [
        "invoice_number",
        "amount_cents",
        "buyer_name",
        "tax_number",
        "transaction_time",
        "location",
        "expense_type",
        "trip_route",
        "transport_mode",
        "cabin_class",
    ]


def test_openai_classification_prompt_includes_tax_seal_and_direct_voucher_rules():
    captured_requests = []
    railway_text = (
        "铁路电子客票 报销凭证 乘车日期 2026-04-01 发票号码 1234567890 "
        "税务监制章 票价合计 553.00"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        captured_requests.append(payload)
        if len(captured_requests) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    build_classification_output(
                                        document_family="invoice",
                                        material_type="invoice",
                                        expense_type_candidate="railway",
                                        is_reimbursement_voucher=True,
                                        classification_confidence=0.98,
                                    ),
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
            )
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
                                            "value": "1234567890",
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
    railway_input = RecognitionDocumentInput(
        source="pdf_text",
        text=railway_text,
        page_count=1,
        text_character_count=len(railway_text),
    )

    result = client.recognize(material=build_material(), document_input=railway_input)

    classification_system_prompt = captured_requests[0]["messages"][0]["content"]
    classification_user_prompt = json.loads(captured_requests[0]["messages"][1]["content"])
    assert (
        "If a document shows a tax authority seal or an equivalent tax-supervision mark, classify it as invoice."
        in classification_system_prompt
    )
    assert (
        "Railway e-tickets, railway electronic itineraries, and airline e-ticket reimbursement vouchers must be classified as invoice"
        in classification_system_prompt
    )
    assert "If a document shows a tax authority seal or equivalent tax-supervision mark, classify it as invoice." in classification_user_prompt["instructions"]
    assert (
        "Treat railway e-tickets, railway electronic itineraries, and airline e-ticket reimbursement vouchers as invoice materials instead of itinerary or other_attachment when they are direct reimbursement vouchers."
        in classification_user_prompt["instructions"]
    )
    assert result.recognized_fields["document_family"].value == "invoice"
    assert result.recognized_fields["material_type"].value == "invoice"
    assert result.recognized_fields["expense_type_candidate"].value == "railway"
    assert result.recognized_fields["is_reimbursement_voucher"].value is True


def test_openai_compatible_recognition_client_sends_pdf_file_input_for_scanned_pdf():
    captured_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        captured_requests.append(payload)
        if len(captured_requests) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(build_classification_output())
                            }
                        }
                    ]
                },
            )
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

    for payload in captured_requests:
        user_content = payload["messages"][1]["content"]
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
    captured_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        captured_requests.append(payload)
        if len(captured_requests) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(build_classification_output())
                            }
                        }
                    ]
                },
            )
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
                                            "value": "IMG-001",
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

    for payload in captured_requests:
        user_content = payload["messages"][1]["content"]
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
    assert result.recognized_fields["invoice_number"].value == "IMG-001"


def test_deepseek_compatible_recognition_client_uses_json_object_response_format():
    captured_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        captured_requests.append(payload)
        if len(captured_requests) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(build_classification_output())
                            }
                        }
                    ]
                },
            )
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

    assert captured_requests[0]["response_format"] == {"type": "json_object"}
    assert captured_requests[1]["response_format"] == {"type": "json_object"}
    assert result.recognized_fields["invoice_number"].value == "INV-001"


def test_deepseek_compatible_recognition_client_accepts_direct_field_object():
    provider_config = build_provider_config().model_copy(
        update={"base_url": "https://api.deepseek.com"}
    )
    client = OpenAiCompatibleRecognitionClient(
        provider_config,
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                build_two_stage_handler(
                    classification_content={
                        "document_family": {
                            "value": "invoice",
                            "confidence": 0.96,
                        },
                        "material_type": {
                            "value": "invoice",
                            "confidence": 0.96,
                        },
                        "expense_type_candidate": {
                            "value": "registration",
                            "confidence": 0.96,
                        },
                        "is_reimbursement_voucher": {
                            "value": True,
                            "confidence": 0.96,
                        },
                        "classification_confidence": {
                            "value": 0.96,
                            "confidence": 0.96,
                        },
                    },
                    extraction_content={
                        "output": {
                            "invoice_number": {
                                "value": "INV-002",
                                "confidence": 0.88,
                            }
                        }
                    },
                )
            ),
            base_url="https://api.deepseek.com",
        ),
    )

    result = client.recognize(material=build_material(), document_input=build_document_input())

    assert result.recognized_fields["document_family"].value == "invoice"
    assert result.recognized_fields["invoice_number"].value == "INV-002"


def test_deepseek_compatible_recognition_client_normalizes_textual_confidence_and_chinese_labels():
    provider_config = build_provider_config().model_copy(
        update={"base_url": "https://api.deepseek.com"}
    )
    call_count = {"value": 0}
    client = OpenAiCompatibleRecognitionClient(
        provider_config,
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: _deepseek_two_stage_response(request, call_count)
            ),
            base_url="https://api.deepseek.com",
        ),
    )

    result = client.recognize(material=build_material(), document_input=build_document_input())

    assert result.recognized_fields["invoice_number"].confidence == 0.95
    assert result.recognized_fields["amount_cents"].confidence == 0.95
    assert result.recognized_fields["material_type"].value == "invoice"
    assert result.recognized_fields["document_family"].value == "invoice"
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
    assert error.value.raw_response["request"]["user_prompt"]["prompt_version"] == "trms-recognition-v3"
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
    assert error.value.raw_response["request"]["user_prompt"]["prompt_version"] == "trms-recognition-v3"
    assert error.value.raw_response["parsed_content"]["output"]["document_family"] is None
    assert error.value.raw_response["parsed_content"]["output"]["classification_confidence"] is None


def test_openai_compatible_recognition_client_reports_invalid_schema_details():
    client = OpenAiCompatibleRecognitionClient(
        build_provider_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                build_two_stage_handler(
                    classification_content={
                        "output": {
                            "document_family": {
                                "value": "invoice",
                                "confidence": 0.91,
                            },
                            "material_type": {
                                "value": "invoice",
                                "confidence": 0.91,
                            },
                            "expense_type_candidate": {
                                "value": "registration",
                                "confidence": 0.91,
                            },
                            "is_reimbursement_voucher": {
                                "value": True,
                                "confidence": 0.91,
                            },
                            "classification_confidence": {
                                "value": "not-a-float",
                                "confidence": 0.91,
                            },
                        }
                    },
                    extraction_content={"output": {}},
                )
            ),
            base_url="https://llm.example.com/v1",
        ),
    )

    with pytest.raises(RecognitionLlmExecutionError) as error:
        client.recognize(material=build_material(), document_input=build_document_input())

    assert error.value.failure.reason == "llm_output_invalid"
    assert error.value.raw_response["request"]["user_prompt"]["prompt_version"] == "trms-recognition-v3"
    assert error.value.raw_response["parsed_content"] == {
        "output": {
            "document_family": {
                "value": "invoice",
                "confidence": 0.91,
            },
            "material_type": {
                "value": "invoice",
                "confidence": 0.91,
            },
            "expense_type_candidate": {
                "value": "registration",
                "confidence": 0.91,
            },
            "is_reimbursement_voucher": {
                "value": True,
                "confidence": 0.91,
            },
        }
    }
    assert error.value.raw_response["validation_errors"][0]["type"] == "missing"


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
