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
    assert "Prompt version: trms-recognition-v4." in captured_requests[0]["payload"]["messages"][0]["content"]
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
        "trms-recognition-v4"
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
    assert "document_family.value must be exactly one of: invoice, competition_notice, payment_record, order_screenshot, itinerary, other_attachment" in captured_requests[0]["messages"][0]["content"]
    assert "material_type.value must be exactly one of: invoice, payment_record, competition_notice, itinerary, order_screenshot, other_attachment" in captured_requests[0]["messages"][0]["content"]
    assert "Never invent subtype categories such as hotel_invoice, railway_invoice, hotel_order, train_order, accommodation, transportation, or taxi." in captured_requests[0]["messages"][0]["content"]
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
            "document_family.value must be exactly one of: invoice, competition_notice, payment_record, order_screenshot, itinerary, other_attachment.",
            "material_type.value must be exactly one of: invoice, payment_record, competition_notice, itinerary, order_screenshot, other_attachment.",
            "expense_type_candidate.value must be exactly one of: registration, railway, airfare, local_transport, hotel, other; use other when no stronger category is supported.",
            "Do not invent subtype categories such as hotel_invoice, railway_invoice, hotel_order, train_order, accommodation, transportation, or taxi.",
            "Use material_type.value=invoice for VAT invoices, paper invoice scans, railway e-ticket invoices, airline reimbursement vouchers, and any direct voucher with tax-supervision marks.",
            "Use material_type.value=order_screenshot for platform hotel/train/flight/taxi order screenshots that are not direct tax invoices.",
            "For local_transport electronic invoices or e-tickets, classify them as invoice, set expense_type_candidate.value=local_transport, and treat them as rideshare evidence requiring a matching itinerary/order trip record.",
            "Set is_reimbursement_voucher to true only when the document itself can directly serve as a reimbursement voucher.",
            "If a document shows a tax authority seal or equivalent tax-supervision mark, classify it as invoice.",
            "Treat railway e-tickets, railway electronic itineraries, and airline e-ticket reimbursement vouchers as invoice materials instead of itinerary or other_attachment when they are direct reimbursement vouchers.",
            "classification_confidence.value must be a float between 0 and 1 describing the overall confidence of the classification result.",
        ],
        "prompt_version": "trms-recognition-v4",
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
        "departure_airport_code",
        "arrival_airport_code",
        "return_departure_airport_code",
        "return_arrival_airport_code",
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


def test_openai_itinerary_extraction_prompt_requests_local_transport_amount_and_time():
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
                                "content": json.dumps(
                                    build_classification_output(
                                        document_family="itinerary",
                                        material_type="itinerary",
                                        expense_type_candidate="local_transport",
                                        is_reimbursement_voucher=False,
                                        classification_confidence=0.94,
                                        field_confidence=0.94,
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
                                        "amount_cents": {
                                            "value": 4250,
                                            "confidence": 0.95,
                                        },
                                        "transaction_time": {
                                            "value": "2026-04-28T09:30:00+08:00",
                                            "confidence": 0.93,
                                        },
                                        "expense_type": {
                                            "value": "local_transport",
                                            "confidence": 0.94,
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

    extraction_request = captured_requests[1]
    extraction_user_prompt = json.loads(extraction_request["messages"][1]["content"])
    assert extraction_user_prompt["selected_schema"]["name"] == "itinerary"
    assert extraction_user_prompt["selected_schema"]["allowed_fields"] == [
        "transaction_time",
        "amount_cents",
        "location",
        "expense_type",
        "trip_route",
        "transport_mode",
        "cabin_class",
        "departure_airport_code",
        "arrival_airport_code",
        "return_departure_airport_code",
        "return_arrival_airport_code",
    ]
    assert (
        "For itinerary materials that describe local_transport trips, extract amount_cents "
        "and transaction_time whenever the trip record shows them, and keep "
        "expense_type.value=local_transport."
    ) in extraction_user_prompt["instructions"]
    assert result.recognized_fields["amount_cents"].value == 4250
    assert result.raw_response["selected_schema"]["name"] == "itinerary"


def test_openai_compatible_recognition_client_runs_airfare_route_stage_for_airfare_invoice():
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
                                "content": json.dumps(
                                    build_classification_output(
                                        expense_type_candidate="airfare",
                                        classification_confidence=0.98,
                                    ),
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
            )
        if len(captured_requests) == 2:
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
                                                "value": "AIR-001",
                                                "confidence": 0.96,
                                            },
                                            "expense_type": {
                                                "value": "airfare",
                                                "confidence": 0.96,
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
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "output": {
                                        "departure_airport_code": {
                                            "value": "sha",
                                            "confidence": 0.94,
                                        },
                                        "arrival_airport_code": {
                                            "value": "wuh",
                                            "confidence": 0.94,
                                        },
                                        "return_departure_airport_code": {
                                            "value": "WUH",
                                            "confidence": 0.94,
                                        },
                                        "return_arrival_airport_code": {
                                            "value": "SHA",
                                            "confidence": 0.94,
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

    assert len(captured_requests) == 3
    route_user_prompt = json.loads(captured_requests[2]["messages"][1]["content"])
    assert route_user_prompt["stage"] == "airfare_route_extraction"
    assert route_user_prompt["selected_schema"]["allowed_fields"] == [
        "departure_airport_code",
        "arrival_airport_code",
        "return_departure_airport_code",
        "return_arrival_airport_code",
    ]
    assert result.recognized_fields["departure_airport_code"].value == "SHA"
    assert result.recognized_fields["arrival_airport_code"].value == "WUH"
    assert result.recognized_fields["return_departure_airport_code"].value == "WUH"
    assert result.recognized_fields["return_arrival_airport_code"].value == "SHA"
    assert result.raw_response["airfare_route"]["attempts"] == 1


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


def test_openai_compatible_recognition_client_normalizes_scalar_classification_fields():
    client = OpenAiCompatibleRecognitionClient(
        build_provider_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                build_two_stage_handler(
                    classification_content={
                        "output": {
                            "document_family": "order_screenshot",
                            "material_type": "hotel_order",
                            "expense_type_candidate": "hotel",
                            "is_reimbursement_voucher": False,
                            "classification_confidence": {"value": 0.9},
                        }
                    },
                    extraction_content={
                        "output": {
                            "amount_cents": {
                                "value": 308700,
                                "confidence": "high",
                            }
                        }
                    },
                )
            ),
            base_url="https://llm.example.com/v1",
        ),
    )

    result = client.recognize(material=build_material(), document_input=build_document_input())

    assert result.recognized_fields["document_family"].value == "order_screenshot"
    assert result.recognized_fields["material_type"].value == "order_screenshot"
    assert result.recognized_fields["expense_type_candidate"].value == "hotel"
    assert result.recognized_fields["is_reimbursement_voucher"].value is False
    assert result.recognized_fields["classification_confidence"].value == 0.9
    assert result.recognized_fields["material_type"].status is RecognitionFieldStatus.NEEDS_CONFIRMATION
    assert result.recognized_fields["amount_cents"].value == 308700
    assert result.raw_response["selected_schema"]["name"] == "order_screenshot"


def test_openai_compatible_recognition_client_fills_material_type_from_document_family():
    client = OpenAiCompatibleRecognitionClient(
        build_provider_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                build_two_stage_handler(
                    classification_content={
                        "output": {
                            "document_family": {
                                "value": "invoice",
                                "confidence": 0.95,
                            },
                            "expense_type_candidate": {
                                "value": "other",
                                "confidence": 0.95,
                            },
                            "is_reimbursement_voucher": {
                                "value": True,
                                "confidence": 0.95,
                            },
                            "classification_confidence": {
                                "value": 0.95,
                            },
                        }
                    },
                    extraction_content={
                        "output": {
                            "amount_cents": {
                                "value": 291226,
                                "confidence": 0.91,
                            }
                        }
                    },
                )
            ),
            base_url="https://llm.example.com/v1",
        ),
    )

    result = client.recognize(material=build_material(), document_input=build_document_input())

    assert result.recognized_fields["document_family"].value == "invoice"
    assert result.recognized_fields["material_type"].value == "invoice"
    assert result.recognized_fields["classification_confidence"].value == 0.95
    assert result.raw_response["selected_schema"]["name"] == "invoice"


def test_openai_compatible_recognition_client_normalizes_provider_subtype_aliases():
    client = OpenAiCompatibleRecognitionClient(
        build_provider_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                build_two_stage_handler(
                    classification_content={
                        "output": {
                            "document_family": "invoice",
                            "material_type": "railway_invoice",
                            "expense_type_candidate": "transportation",
                            "is_reimbursement_voucher": True,
                            "classification_confidence": {"value": 0.94},
                        }
                    },
                    extraction_content={"output": {}},
                )
            ),
            base_url="https://llm.example.com/v1",
        ),
    )

    result = client.recognize(material=build_material(), document_input=build_document_input())

    assert result.recognized_fields["document_family"].value == "invoice"
    assert result.recognized_fields["material_type"].value == "invoice"
    assert result.recognized_fields["expense_type_candidate"].value == "local_transport"
    assert result.raw_response["selected_schema"]["name"] == "invoice"


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
    assert error.value.raw_response["request"]["user_prompt"]["prompt_version"] == "trms-recognition-v4"
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
    assert error.value.raw_response["request"]["user_prompt"]["prompt_version"] == "trms-recognition-v4"
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
    assert error.value.raw_response["request"]["user_prompt"]["prompt_version"] == "trms-recognition-v4"
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
