from fastapi.testclient import TestClient

from trms_backend.domain.audit_logs import AuditLogResult
from trms_backend.domain.invoice_validation import (
    AIRFARE_CABIN_PROOF_RULE_CODE,
    AIRFARE_ITINERARY_REQUIRED_RULE_CODE,
    COMPETITION_LOCATION_RANGE_RULE_CODE,
    COMPETITION_TIME_RANGE_RULE_CODE,
    COMPETITION_NOTICE_REQUIRED_RULE_CODE,
    LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE,
    PAYMENT_RECORD_AMOUNT_MATCH_MODE,
    PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
)
from trms_backend.infrastructure.database import build_session_factory
from trms_backend.infrastructure.repositories import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyInvoiceRepository,
)
from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from test_tasks_api import admin_auth_headers, create_task as create_admin_task, valid_task_payload


def make_client(tmp_path):
    runtime_config = load_runtime_config(
        environment="test",
        database_url=f"sqlite:///{tmp_path}/test.db",
        material_storage_dir=tmp_path / "material-storage",
        cors_allowed_origins="http://127.0.0.1:5173",
        public_api_base_url="http://127.0.0.1:8000/api",
        api_host="127.0.0.1",
        api_port=8000,
        async_job_mode="worker",
    )
    return TestClient(
        create_app(
            runtime_config=runtime_config,
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def create_material(client: TestClient) -> tuple[str, str]:
    task = create_admin_task(client)
    client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    return task["id"], upload_material(client, task["id"])


def create_airfare_material(client: TestClient) -> tuple[str, str]:
    task_payload = valid_task_payload() | {"fee_categories": ["airfare"]}
    task = create_admin_task(client, payload=task_payload)
    client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    return task["id"], upload_material(client, task["id"], filename="airfare.pdf")


def create_local_transport_material(client: TestClient) -> tuple[str, str]:
    task_payload = valid_task_payload() | {"fee_categories": ["local_transport"]}
    task = create_admin_task(client, payload=task_payload)
    client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    return task["id"], upload_material(client, task["id"], filename="local-transport.pdf")


def upload_material(client: TestClient, task_id: str, filename: str = "ticket.pdf") -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": (filename, filename.encode(), "application/pdf")},
    )
    return response.json()["items"][0]["id"]


def upload_supporting_material(
    client: TestClient,
    task_id: str,
    *,
    material_type: str = "payment_record",
    filename: str = "payment.png",
    content_type: str = "image/png",
) -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": material_type,
        },
        files={"files": (filename, filename.encode(), content_type)},
    )
    return response.json()["items"][0]["id"]


def set_recognition_result(
    client: TestClient,
    material_id: str,
    *,
    recognized_fields: dict,
    target_status: str = "succeeded",
    document_type: str = "supporting_material",
):
    recognition_task_id = client.get(f"/api/materials/{material_id}/recognition-tasks").json()["items"][0][
        "id"
    ]
    response = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": target_status,
            "result": {
                "raw_response": {
                    "provider": "placeholder-ai",
                    "document_type": document_type,
                },
                "recognized_fields": recognized_fields,
            },
        },
    )
    assert response.status_code == 200
    return recognition_task_id


def list_recognition_task_audit_logs(tmp_path, recognition_task_id: str):
    repository = SqlAlchemyAuditLogRepository(
        build_session_factory(f"sqlite:///{tmp_path}/test.db")
    )
    return repository.list_by_object(
        object_type="recognition_task",
        object_id=recognition_task_id,
    )


def list_linked_invoice_ids_for_supporting_material(tmp_path, material_id: str) -> list[str]:
    repository = SqlAlchemyInvoiceRepository(
        build_session_factory(f"sqlite:///{tmp_path}/test.db")
    )
    return [invoice.id for invoice in repository.list_by_supporting_material(material_id)]


def set_recognition_amount_cents(
    client: TestClient,
    material_id: str,
    *,
    amount_cents: int | None,
    target_status: str = "succeeded",
):
    recognized_fields = {}
    if amount_cents is not None:
        recognized_fields["amount_cents"] = {
            "value": amount_cents,
            "source": "ai",
            "confidence": 0.98,
            "status": "recognized",
        }
    return set_recognition_result(
        client,
        material_id,
        recognized_fields=recognized_fields,
        target_status=target_status,
        document_type="payment_record",
    )


def valid_invoice_payload():
    return {
        "actor_id": "2250001",
        "invoice_number": "INV-001",
        "issue_date": "2026-11-04",
        "transaction_time": "2026-11-01T08:00:00+00:00",
        "buyer_name": "同济大学",
        "tax_number": "12100000425006117D",
        "seller_name": "铁路服务商",
        "amount_cents": 12345,
        "expense_type": "railway",
    }


def validation_by_code(response_body, rule_code: str):
    return next(item for item in response_body["validations"] if item["rule_code"] == rule_code)


def manual_corrections_by_field(recognition_task: dict, field_name: str) -> list[dict]:
    return [
        item
        for item in recognition_task["manual_corrections"]
        if item["field_name"] == field_name
    ]


def create_invoice_for_material(
    client: TestClient,
    material_id: str,
    **overrides,
) -> str:
    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload() | overrides,
    )
    assert response.status_code == 201
    return response.json()["invoice"]["id"]


def test_create_invoice_and_pass_basic_validations(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)

    response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["invoice"]["task_id"] == task_id
    assert body["invoice"]["material_id"] == material_id
    assert body["invoice"]["amount_cents"] == 12345
    title_validation = validation_by_code(body, "invoice_title_match")
    tax_validation = validation_by_code(body, "invoice_tax_number_match")
    duplicate_validation = validation_by_code(body, "invoice_number_unique")

    assert title_validation["target_type"] == "invoice"
    assert title_validation["target_id"] == body["invoice"]["id"]
    assert title_validation["severity"] == "blocker"
    assert title_validation["status"] == "passed"
    assert title_validation["evidence"] == {
        "expected_buyer_name": "同济大学",
        "actual_buyer_name": "同济大学",
    }
    assert tax_validation["status"] == "passed"
    assert tax_validation["evidence"] == {
        "expected_tax_number": "12100000425006117D",
        "actual_tax_number": "12100000425006117D",
    }
    assert duplicate_validation["status"] == "passed"
    assert duplicate_validation["evidence"] == {
        "invoice_number": "INV-001",
        "duplicate_invoice_id": None,
    }
    payment_record_validation = validation_by_code(body, "invoice_payment_record_required")
    assert payment_record_validation["status"] == "not_applicable"
    assert payment_record_validation["evidence"] == {
        "amount_cents": 12345,
        "threshold_amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
        "config_source": (
            "trms_backend.domain.invoice_validation."
            "PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS"
        ),
        "requires_payment_record": False,
        "payment_record_material_ids": [],
    }
    payment_amount_validation = validation_by_code(body, "invoice_payment_record_amount_match")
    assert payment_amount_validation["status"] == "not_applicable"
    assert payment_amount_validation["evidence"] == {
        "invoice_amount_cents": 12345,
        "threshold_amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
        "matching_mode": PAYMENT_RECORD_AMOUNT_MATCH_MODE,
        "config_source": (
            "trms_backend.domain.invoice_validation.PAYMENT_RECORD_AMOUNT_MATCH_MODE"
        ),
        "requires_payment_record": False,
        "payment_record_material_ids": [],
        "matched_payment_records": [],
        "missing_amount_materials": [],
        "payment_record_amount_total_cents": None,
    }
    competition_notice_validation = validation_by_code(
        body, COMPETITION_NOTICE_REQUIRED_RULE_CODE
    )
    assert competition_notice_validation["status"] == "not_applicable"
    assert competition_notice_validation["evidence"] == {
        "expense_type": "railway",
        "required_material_type": "competition_notice",
        "requires_competition_notice": False,
        "competition_notice_material_ids": [],
    }
    airfare_itinerary_validation = validation_by_code(body, AIRFARE_ITINERARY_REQUIRED_RULE_CODE)
    assert airfare_itinerary_validation["status"] == "not_applicable"
    assert airfare_itinerary_validation["evidence"] == {
        "expense_type": "railway",
        "invoice_material_id": material_id,
        "required_material_type": "itinerary",
        "requires_itinerary": False,
        "invoice_material_present": True,
        "itinerary_material_ids": [],
    }
    airfare_cabin_validation = validation_by_code(body, AIRFARE_CABIN_PROOF_RULE_CODE)
    assert airfare_cabin_validation["status"] == "not_applicable"
    assert airfare_cabin_validation["evidence"] == {
        "expense_type": "railway",
        "invoice_material_id": material_id,
        "cabin_field_names": ["cabin_class", "seat_class", "cabin"],
        "requires_cabin_proof": False,
        "itinerary_material_ids": [],
        "order_screenshot_material_ids": [],
        "recognized_cabin_materials": [],
    }
    local_transport_validation = validation_by_code(
        body, LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE
    )
    assert local_transport_validation["status"] == "not_applicable"
    assert local_transport_validation["evidence"] == {
        "expense_type": "railway",
        "invoice_material_id": material_id,
        "rideshare_indicator_field_names": [
            "is_rideshare",
            "transport_mode",
            "transport_type",
            "ride_service_type",
        ],
        "trip_field_groups": [
            ["trip_route"],
            ["trip_itinerary"],
            ["trip_start_location", "trip_end_location"],
            ["pickup_location", "dropoff_location"],
            ["start_location", "end_location"],
        ],
        "requires_local_transport_validation": False,
        "rideshare_detections": [],
        "trip_information_materials": [],
    }
    competition_time_validation = validation_by_code(body, COMPETITION_TIME_RANGE_RULE_CODE)
    assert competition_time_validation["severity"] == "warning"
    assert competition_time_validation["status"] == "passed"
    assert competition_time_validation["evidence"] == {
        "expense_type": "railway",
        "supported_expense_types": [
            "railway",
            "airfare",
            "local_transport",
            "hotel",
        ],
        "requires_competition_time_validation": True,
        "competition_start_date": "2026-11-01",
        "competition_end_date": "2026-11-03",
        "buffer_days_before": 1,
        "buffer_days_after": 1,
        "effective_start_date": "2026-10-31",
        "effective_end_date": "2026-11-04",
        "transaction_time": "2026-11-01T08:00:00+00:00",
        "transaction_date": "2026-11-01",
        "issue_date": "2026-11-04",
        "time_source": "transaction_time",
    }
    competition_location_validation = validation_by_code(
        body, COMPETITION_LOCATION_RANGE_RULE_CODE
    )
    assert competition_location_validation["severity"] == "warning"
    assert competition_location_validation["status"] == "pending"
    assert competition_location_validation["message"] == (
        "缺少可用于比赛地点范围校验的地点信息，需人工确认"
    )
    assert competition_location_validation["evidence"] == {
        "expense_type": "railway",
        "supported_expense_types": [
            "railway",
            "airfare",
            "local_transport",
            "hotel",
        ],
        "requires_competition_location_validation": True,
        "competition_location": "Shanghai",
        "location_field_groups": [
            ["transaction_location"],
            ["transaction_city"],
            ["location"],
            ["city"],
            ["merchant_location"],
            ["hotel_city"],
            ["trip_route"],
            ["trip_itinerary"],
            ["departure_location", "arrival_location"],
            ["departure_city", "arrival_city"],
            ["origin_location", "destination_location"],
            ["from_location", "to_location"],
            ["trip_start_location", "trip_end_location"],
            ["pickup_location", "dropoff_location"],
            ["start_location", "end_location"],
        ],
        "matched_location_materials": [],
        "unmatched_location_materials": [],
    }


def test_task_administrator_can_record_invoice_for_member_material(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload() | {"actor_id": "admin-1"},
    )

    assert response.status_code == 201
    assert response.json()["invoice"]["task_id"] == task_id


def test_create_invoice_rejects_actor_outside_submitter_and_administrator(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload() | {"actor_id": "outsider-1"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "only the material submitter or task administrator can record invoice fields"
    )


def test_create_invoice_reports_title_and_tax_mismatch(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)
    payload = valid_invoice_payload() | {
        "buyer_name": "错误抬头",
        "tax_number": "WRONG-TAX-NUMBER",
    }

    response = client.post(f"/api/materials/{material_id}/invoice", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert validation_by_code(body, "invoice_title_match")["status"] == "failed"
    assert validation_by_code(body, "invoice_title_match")["evidence"] == {
        "expected_buyer_name": "同济大学",
        "actual_buyer_name": "错误抬头",
    }
    assert validation_by_code(body, "invoice_tax_number_match")["status"] == "failed"
    assert validation_by_code(body, "invoice_tax_number_match")["evidence"] == {
        "expected_tax_number": "12100000425006117D",
        "actual_tax_number": "WRONG-TAX-NUMBER",
    }


def test_create_invoice_marks_missing_recognized_title_and_tax_as_pending(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)
    recognition_task_id = client.get(f"/api/materials/{material_id}/recognition-tasks").json()["items"][0][
        "id"
    ]

    recognition_update = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "succeeded",
            "result": {
                "raw_response": {
                    "provider": "placeholder-ai",
                    "document_type": "invoice",
                },
                "recognized_fields": {
                    "invoice_number": {
                        "value": "INV-001",
                        "source": "ai",
                        "confidence": 0.99,
                        "status": "recognized",
                    }
                },
            },
        },
    )

    assert recognition_update.status_code == 200

    response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    assert response.status_code == 201
    body = response.json()
    assert validation_by_code(body, "invoice_title_match")["status"] == "pending"
    assert validation_by_code(body, "invoice_title_match")["evidence"] == {
        "expected_buyer_name": "同济大学",
        "actual_buyer_name": "同济大学",
        "recognized_buyer_name": None,
        "recognition_task_status": "succeeded",
        "recognition_status": "missing",
    }
    assert validation_by_code(body, "invoice_tax_number_match")["status"] == "pending"
    assert validation_by_code(body, "invoice_tax_number_match")["evidence"] == {
        "expected_tax_number": "12100000425006117D",
        "actual_tax_number": "12100000425006117D",
        "recognized_tax_number": None,
        "recognition_task_status": "succeeded",
        "recognition_status": "missing",
    }


def test_create_invoice_keeps_failed_when_manual_title_and_tax_mismatch_after_missing_recognition(
    tmp_path,
):
    client = make_client(tmp_path)
    _, material_id = create_material(client)
    recognition_task_id = client.get(f"/api/materials/{material_id}/recognition-tasks").json()["items"][0][
        "id"
    ]

    recognition_update = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "failed",
            "failure": {
                "stage": "ocr",
                "reason": "buyer name and tax number were not recognized",
            },
        },
    )

    assert recognition_update.status_code == 200

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {
            "buyer_name": "错误抬头",
            "tax_number": "WRONG-TAX-NUMBER",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert validation_by_code(body, "invoice_title_match")["status"] == "failed"
    assert validation_by_code(body, "invoice_title_match")["evidence"] == {
        "expected_buyer_name": "同济大学",
        "actual_buyer_name": "错误抬头",
        "recognized_buyer_name": None,
        "recognition_task_status": "failed",
        "recognition_status": "missing",
    }
    assert validation_by_code(body, "invoice_tax_number_match")["status"] == "failed"
    assert validation_by_code(body, "invoice_tax_number_match")["evidence"] == {
        "expected_tax_number": "12100000425006117D",
        "actual_tax_number": "WRONG-TAX-NUMBER",
        "recognized_tax_number": None,
        "recognition_task_status": "failed",
        "recognition_status": "missing",
    }


def test_create_invoice_reports_duplicate_invoice_number(tmp_path):
    client = make_client(tmp_path)
    task_id, first_material_id = create_material(client)
    second_material_id = upload_material(client, task_id, "ticket-2.pdf")
    client.post(f"/api/materials/{first_material_id}/invoice", json=valid_invoice_payload())

    response = client.post(f"/api/materials/{second_material_id}/invoice", json=valid_invoice_payload())

    assert response.status_code == 201
    duplicate = validation_by_code(response.json(), "invoice_number_unique")
    assert duplicate["status"] == "failed"
    assert "重复" in duplicate["message"]
    assert duplicate["evidence"]["invoice_number"] == "INV-001"
    assert duplicate["evidence"]["duplicate_invoice_id"] is not None


def test_create_invoice_fails_payment_record_validation_when_amount_reaches_threshold(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {"amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS},
    )

    assert response.status_code == 201
    payment_record_validation = validation_by_code(
        response.json(), "invoice_payment_record_required"
    )
    assert payment_record_validation["status"] == "failed"
    assert payment_record_validation["message"] == "发票金额达到阈值，缺少支付记录"
    assert payment_record_validation["evidence"] == {
        "amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
        "threshold_amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
        "config_source": (
            "trms_backend.domain.invoice_validation."
            "PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS"
        ),
        "requires_payment_record": True,
        "payment_record_material_ids": [],
    }
    payment_amount_validation = validation_by_code(
        response.json(), "invoice_payment_record_amount_match"
    )
    assert payment_amount_validation["status"] == "not_applicable"
    assert payment_amount_validation["message"] == "尚未关联支付记录，暂不执行金额匹配"


def test_create_invoice_marks_competition_time_validation_pending_when_transaction_time_is_missing(
    tmp_path,
):
    client = make_client(tmp_path)
    _, material_id = create_material(client)

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {
            "transaction_time": None,
            "issue_date": "2026-11-02",
        },
    )

    assert response.status_code == 201
    competition_time_validation = validation_by_code(
        response.json(),
        COMPETITION_TIME_RANGE_RULE_CODE,
    )
    assert competition_time_validation["severity"] == "warning"
    assert competition_time_validation["status"] == "pending"
    assert competition_time_validation["message"] == (
        "缺少交易时间，需人工确认是否与比赛时间范围相关"
    )
    assert competition_time_validation["evidence"] == {
        "expense_type": "railway",
        "supported_expense_types": [
            "railway",
            "airfare",
            "local_transport",
            "hotel",
        ],
        "requires_competition_time_validation": True,
        "competition_start_date": "2026-11-01",
        "competition_end_date": "2026-11-03",
        "buffer_days_before": 1,
        "buffer_days_after": 1,
        "effective_start_date": "2026-10-31",
        "effective_end_date": "2026-11-04",
        "transaction_time": None,
        "transaction_date": None,
        "issue_date": "2026-11-02",
        "time_source": "missing_transaction_time",
    }


def test_create_invoice_warns_when_transaction_time_is_outside_default_competition_buffer(
    tmp_path,
):
    client = make_client(tmp_path)
    _, material_id = create_material(client)

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload() | {"transaction_time": "2026-10-29T08:00:00Z"},
    )

    assert response.status_code == 201
    competition_time_validation = validation_by_code(
        response.json(),
        COMPETITION_TIME_RANGE_RULE_CODE,
    )
    assert competition_time_validation["severity"] == "warning"
    assert competition_time_validation["status"] == "failed"
    assert competition_time_validation["message"] == "交易时间超出默认比赛时间缓冲范围，需人工确认"
    assert competition_time_validation["evidence"] == {
        "expense_type": "railway",
        "supported_expense_types": [
            "railway",
            "airfare",
            "local_transport",
            "hotel",
        ],
        "requires_competition_time_validation": True,
        "competition_start_date": "2026-11-01",
        "competition_end_date": "2026-11-03",
        "buffer_days_before": 1,
        "buffer_days_after": 1,
        "effective_start_date": "2026-10-31",
        "effective_end_date": "2026-11-04",
        "transaction_time": "2026-10-29T08:00:00+00:00",
        "transaction_date": "2026-10-29",
        "issue_date": "2026-11-04",
        "time_source": "transaction_time",
    }


def test_create_invoice_passes_competition_location_validation_when_route_matches_task_city(
    tmp_path,
):
    client = make_client(tmp_path)
    _, material_id = create_material(client)
    recognition_task_id = set_recognition_result(
        client,
        material_id,
        document_type="invoice",
        recognized_fields={
            "departure_location": {
                "value": "Nanjing South Railway Station",
                "source": "ai",
                "confidence": 0.95,
                "status": "recognized",
            },
            "arrival_location": {
                "value": "Shanghai Hongqiao Railway Station",
                "source": "ai",
                "confidence": 0.95,
                "status": "recognized",
            },
        },
    )

    response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    assert response.status_code == 201
    competition_location_validation = validation_by_code(
        response.json(),
        COMPETITION_LOCATION_RANGE_RULE_CODE,
    )
    assert competition_location_validation["severity"] == "warning"
    assert competition_location_validation["status"] == "passed"
    assert competition_location_validation["message"] == "交易地点与比赛地点或往返路径基础匹配"
    assert competition_location_validation["evidence"] == {
        "expense_type": "railway",
        "supported_expense_types": [
            "railway",
            "airfare",
            "local_transport",
            "hotel",
        ],
        "requires_competition_location_validation": True,
        "competition_location": "Shanghai",
        "location_field_groups": [
            ["transaction_location"],
            ["transaction_city"],
            ["location"],
            ["city"],
            ["merchant_location"],
            ["hotel_city"],
            ["trip_route"],
            ["trip_itinerary"],
            ["departure_location", "arrival_location"],
            ["departure_city", "arrival_city"],
            ["origin_location", "destination_location"],
            ["from_location", "to_location"],
            ["trip_start_location", "trip_end_location"],
            ["pickup_location", "dropoff_location"],
            ["start_location", "end_location"],
        ],
        "matched_location_materials": [
            {
                "material_id": material_id,
                "material_type": "invoice",
                "matched_fields": {
                    "departure_location": "Nanjing South Railway Station",
                    "arrival_location": "Shanghai Hongqiao Railway Station",
                },
                "competition_location_match": True,
                "recognition_task_id": recognition_task_id,
                "recognition_task_status": "succeeded",
            }
        ],
        "unmatched_location_materials": [],
    }


def test_create_invoice_warns_when_competition_location_does_not_match_route(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)
    recognition_task_id = set_recognition_result(
        client,
        material_id,
        document_type="invoice",
        recognized_fields={
            "departure_location": {
                "value": "Nanjing South Railway Station",
                "source": "ai",
                "confidence": 0.95,
                "status": "recognized",
            },
            "arrival_location": {
                "value": "Suzhou Railway Station",
                "source": "ai",
                "confidence": 0.95,
                "status": "recognized",
            },
        },
    )

    response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    assert response.status_code == 201
    competition_location_validation = validation_by_code(
        response.json(),
        COMPETITION_LOCATION_RANGE_RULE_CODE,
    )
    assert competition_location_validation["severity"] == "warning"
    assert competition_location_validation["status"] == "failed"
    assert competition_location_validation["message"] == (
        "交易地点与比赛地点或往返路径不匹配，需人工确认"
    )
    assert competition_location_validation["evidence"] == {
        "expense_type": "railway",
        "supported_expense_types": [
            "railway",
            "airfare",
            "local_transport",
            "hotel",
        ],
        "requires_competition_location_validation": True,
        "competition_location": "Shanghai",
        "location_field_groups": [
            ["transaction_location"],
            ["transaction_city"],
            ["location"],
            ["city"],
            ["merchant_location"],
            ["hotel_city"],
            ["trip_route"],
            ["trip_itinerary"],
            ["departure_location", "arrival_location"],
            ["departure_city", "arrival_city"],
            ["origin_location", "destination_location"],
            ["from_location", "to_location"],
            ["trip_start_location", "trip_end_location"],
            ["pickup_location", "dropoff_location"],
            ["start_location", "end_location"],
        ],
        "matched_location_materials": [],
        "unmatched_location_materials": [
            {
                "material_id": material_id,
                "material_type": "invoice",
                "matched_fields": {
                    "departure_location": "Nanjing South Railway Station",
                    "arrival_location": "Suzhou Railway Station",
                },
                "competition_location_match": False,
                "recognition_task_id": recognition_task_id,
                "recognition_task_status": "succeeded",
            }
        ],
    }


def test_create_registration_invoice_fails_when_competition_notice_is_missing(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload() | {"expense_type": "registration"},
    )

    assert response.status_code == 201
    competition_notice_validation = validation_by_code(
        response.json(), COMPETITION_NOTICE_REQUIRED_RULE_CODE
    )
    assert competition_notice_validation["status"] == "failed"
    assert competition_notice_validation["message"] == "参赛费缺少比赛通知"
    assert competition_notice_validation["evidence"] == {
        "expense_type": "registration",
        "required_material_type": "competition_notice",
        "requires_competition_notice": True,
        "competition_notice_material_ids": [],
    }


def test_create_airfare_invoice_fails_when_itinerary_and_cabin_proof_are_missing(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_airfare_material(client)

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {
            "seller_name": "东方航空",
            "expense_type": "airfare",
        },
    )

    assert response.status_code == 201
    itinerary_validation = validation_by_code(
        response.json(),
        AIRFARE_ITINERARY_REQUIRED_RULE_CODE,
    )
    assert itinerary_validation["status"] == "failed"
    assert itinerary_validation["message"] == "航空费用缺少行程单"
    assert itinerary_validation["evidence"] == {
        "expense_type": "airfare",
        "invoice_material_id": material_id,
        "required_material_type": "itinerary",
        "requires_itinerary": True,
        "invoice_material_present": True,
        "itinerary_material_ids": [],
    }
    cabin_validation = validation_by_code(response.json(), AIRFARE_CABIN_PROOF_RULE_CODE)
    assert cabin_validation["status"] == "failed"
    assert cabin_validation["message"] == "航空费用缺少舱位信息，且未关联订单截图"
    assert cabin_validation["evidence"] == {
        "expense_type": "airfare",
        "invoice_material_id": material_id,
        "cabin_field_names": ["cabin_class", "seat_class", "cabin"],
        "requires_cabin_proof": True,
        "itinerary_material_ids": [],
        "order_screenshot_material_ids": [],
        "recognized_cabin_materials": [],
    }


def test_create_local_transport_invoice_marks_pending_when_rideshare_cannot_be_determined(
    tmp_path,
):
    client = make_client(tmp_path)
    _, material_id = create_local_transport_material(client)

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {
            "seller_name": "上海市交通服务商",
            "expense_type": "local_transport",
        },
    )

    assert response.status_code == 201
    local_transport_validation = validation_by_code(
        response.json(),
        LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE,
    )
    assert local_transport_validation["status"] == "pending"
    assert local_transport_validation["message"] == "市内交通无法判断是否为网约车，需人工确认"
    assert local_transport_validation["evidence"] == {
        "expense_type": "local_transport",
        "invoice_material_id": material_id,
        "rideshare_indicator_field_names": [
            "is_rideshare",
            "transport_mode",
            "transport_type",
            "ride_service_type",
        ],
        "trip_field_groups": [
            ["trip_route"],
            ["trip_itinerary"],
            ["trip_start_location", "trip_end_location"],
            ["pickup_location", "dropoff_location"],
            ["start_location", "end_location"],
        ],
        "requires_local_transport_validation": True,
        "rideshare_detections": [],
        "trip_information_materials": [],
    }


def test_create_rideshare_invoice_fails_when_trip_information_is_missing(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_local_transport_material(client)
    set_recognition_result(
        client,
        material_id,
        document_type="invoice",
        recognized_fields={
            "transport_mode": {
                "value": "rideshare",
                "source": "ai",
                "confidence": 0.96,
                "status": "recognized",
            }
        },
    )

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {
            "seller_name": "滴滴出行",
            "expense_type": "local_transport",
        },
    )

    assert response.status_code == 201
    local_transport_validation = validation_by_code(
        response.json(),
        LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE,
    )
    assert local_transport_validation["status"] == "failed"
    assert local_transport_validation["message"] == "网约车费用缺少行程信息"
    assert local_transport_validation["evidence"] == {
        "expense_type": "local_transport",
        "invoice_material_id": material_id,
        "rideshare_indicator_field_names": [
            "is_rideshare",
            "transport_mode",
            "transport_type",
            "ride_service_type",
        ],
        "trip_field_groups": [
            ["trip_route"],
            ["trip_itinerary"],
            ["trip_start_location", "trip_end_location"],
            ["pickup_location", "dropoff_location"],
            ["start_location", "end_location"],
        ],
        "requires_local_transport_validation": True,
        "rideshare_detections": [
            {
                "material_id": material_id,
                "material_type": "invoice",
                "field_name": "transport_mode",
                "field_value": "rideshare",
                "is_rideshare": True,
                "recognition_task_id": local_transport_validation["evidence"][
                    "rideshare_detections"
                ][0]["recognition_task_id"],
                "recognition_task_status": "succeeded",
            }
        ],
        "trip_information_materials": [],
    }


def test_attach_order_screenshot_revalidates_rideshare_invoice_to_pass(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_local_transport_material(client)
    set_recognition_result(
        client,
        material_id,
        document_type="invoice",
        recognized_fields={
            "is_rideshare": {
                "value": True,
                "source": "ai",
                "confidence": 0.95,
                "status": "recognized",
            }
        },
    )
    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {
            "seller_name": "滴滴出行",
            "expense_type": "local_transport",
        },
    )
    invoice_id = invoice_response.json()["invoice"]["id"]
    order_screenshot_material_id = upload_supporting_material(
        client,
        task_id,
        material_type="order_screenshot",
        filename="rideshare-order.png",
        content_type="image/png",
    )
    recognition_task_id = set_recognition_result(
        client,
        order_screenshot_material_id,
        document_type="order_screenshot",
        recognized_fields={
            "pickup_location": {
                "value": "嘉定校区",
                "source": "ai",
                "confidence": 0.93,
                "status": "recognized",
            },
            "dropoff_location": {
                "value": "虹桥火车站",
                "source": "ai",
                "confidence": 0.93,
                "status": "recognized",
            },
        },
    )

    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{order_screenshot_material_id}",
        headers=admin_auth_headers(client),
    )

    assert attach_response.status_code == 200

    validations_response = client.get(f"/api/invoices/{invoice_id}/validations")

    assert validations_response.status_code == 200
    local_transport_validation = next(
        item
        for item in validations_response.json()["items"]
        if item["rule_code"] == LOCAL_TRANSPORT_RIDESHARE_TRIP_RULE_CODE
    )
    assert local_transport_validation["status"] == "passed"
    assert local_transport_validation["message"] == "网约车费用已具备行程信息"
    assert local_transport_validation["evidence"] == {
        "expense_type": "local_transport",
        "invoice_material_id": material_id,
        "rideshare_indicator_field_names": [
            "is_rideshare",
            "transport_mode",
            "transport_type",
            "ride_service_type",
        ],
        "trip_field_groups": [
            ["trip_route"],
            ["trip_itinerary"],
            ["trip_start_location", "trip_end_location"],
            ["pickup_location", "dropoff_location"],
            ["start_location", "end_location"],
        ],
        "requires_local_transport_validation": True,
        "rideshare_detections": [
            {
                "material_id": material_id,
                "material_type": "invoice",
                "field_name": "is_rideshare",
                "field_value": True,
                "is_rideshare": True,
                "recognition_task_id": local_transport_validation["evidence"][
                    "rideshare_detections"
                ][0]["recognition_task_id"],
                "recognition_task_status": "succeeded",
            }
        ],
        "trip_information_materials": [
            {
                "material_id": order_screenshot_material_id,
                "material_type": "order_screenshot",
                "matched_fields": {
                    "pickup_location": "嘉定校区",
                    "dropoff_location": "虹桥火车站",
                },
                "recognition_task_id": recognition_task_id,
                "recognition_task_status": "succeeded",
            }
        ],
    }


def test_attach_payment_record_revalidates_large_amount_invoice_to_pass(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)
    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {"amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS},
    )
    invoice_id = invoice_response.json()["invoice"]["id"]
    payment_record_material_id = upload_supporting_material(
        client,
        task_id,
        material_type="payment_record",
    )
    recognition_task_id = set_recognition_amount_cents(
        client,
        payment_record_material_id,
        amount_cents=PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
    )

    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{payment_record_material_id}",
        headers=admin_auth_headers(client),
    )

    assert attach_response.status_code == 200

    validations_response = client.get(f"/api/invoices/{invoice_id}/validations")

    assert validations_response.status_code == 200
    payment_record_validation = next(
        item
        for item in validations_response.json()["items"]
        if item["rule_code"] == "invoice_payment_record_required"
    )
    assert payment_record_validation["status"] == "passed"
    assert payment_record_validation["evidence"] == {
        "amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
        "threshold_amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
        "config_source": (
            "trms_backend.domain.invoice_validation."
            "PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS"
        ),
        "requires_payment_record": True,
        "payment_record_material_ids": [payment_record_material_id],
    }
    payment_amount_validation = next(
        item
        for item in validations_response.json()["items"]
        if item["rule_code"] == "invoice_payment_record_amount_match"
    )
    assert payment_amount_validation["status"] == "passed"
    assert payment_amount_validation["message"] == "支付记录金额与发票金额一致"
    assert payment_amount_validation["evidence"] == {
        "invoice_amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
        "threshold_amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
        "matching_mode": PAYMENT_RECORD_AMOUNT_MATCH_MODE,
        "config_source": (
            "trms_backend.domain.invoice_validation.PAYMENT_RECORD_AMOUNT_MATCH_MODE"
        ),
        "requires_payment_record": True,
        "payment_record_material_ids": [payment_record_material_id],
        "matched_payment_records": [
            {
                "material_id": payment_record_material_id,
                "recognized_amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
                "recognition_task_id": recognition_task_id,
                "recognition_task_status": "succeeded",
            }
        ],
        "missing_amount_materials": [],
        "payment_record_amount_total_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
    }


def test_attach_competition_notice_revalidates_registration_invoice_to_pass(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)
    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload() | {"expense_type": "registration"},
    )
    invoice_id = invoice_response.json()["invoice"]["id"]
    competition_notice_material_id = upload_supporting_material(
        client,
        task_id,
        material_type="competition_notice",
        filename="notice.pdf",
        content_type="application/pdf",
    )

    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{competition_notice_material_id}",
        headers=admin_auth_headers(client),
    )

    assert attach_response.status_code == 200

    validations_response = client.get(f"/api/invoices/{invoice_id}/validations")

    assert validations_response.status_code == 200
    competition_notice_validation = next(
        item
        for item in validations_response.json()["items"]
        if item["rule_code"] == COMPETITION_NOTICE_REQUIRED_RULE_CODE
    )
    assert competition_notice_validation["status"] == "passed"
    assert competition_notice_validation["message"] == "参赛费已关联比赛通知"
    assert competition_notice_validation["evidence"] == {
        "expense_type": "registration",
        "required_material_type": "competition_notice",
        "requires_competition_notice": True,
        "competition_notice_material_ids": [competition_notice_material_id],
    }


def test_attach_itinerary_with_cabin_info_revalidates_airfare_invoice_to_pass(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_airfare_material(client)
    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {
            "seller_name": "中国国航",
            "expense_type": "airfare",
        },
    )
    invoice_id = invoice_response.json()["invoice"]["id"]
    itinerary_material_id = upload_supporting_material(
        client,
        task_id,
        material_type="itinerary",
        filename="itinerary.pdf",
        content_type="application/pdf",
    )
    recognition_task_id = set_recognition_result(
        client,
        itinerary_material_id,
        document_type="itinerary",
        recognized_fields={
            "cabin_class": {
                "value": "Economy",
                "source": "ai",
                "confidence": 0.97,
                "status": "recognized",
            }
        },
    )

    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{itinerary_material_id}",
        headers=admin_auth_headers(client),
    )

    assert attach_response.status_code == 200

    validations_response = client.get(f"/api/invoices/{invoice_id}/validations")

    assert validations_response.status_code == 200
    itinerary_validation = next(
        item
        for item in validations_response.json()["items"]
        if item["rule_code"] == AIRFARE_ITINERARY_REQUIRED_RULE_CODE
    )
    assert itinerary_validation["status"] == "passed"
    assert itinerary_validation["message"] == "航空费用已关联行程单"
    assert itinerary_validation["evidence"] == {
        "expense_type": "airfare",
        "invoice_material_id": material_id,
        "required_material_type": "itinerary",
        "requires_itinerary": True,
        "invoice_material_present": True,
        "itinerary_material_ids": [itinerary_material_id],
    }
    cabin_validation = next(
        item
        for item in validations_response.json()["items"]
        if item["rule_code"] == AIRFARE_CABIN_PROOF_RULE_CODE
    )
    assert cabin_validation["status"] == "passed"
    assert cabin_validation["message"] == "航空费用已具备舱位信息"
    assert cabin_validation["evidence"] == {
        "expense_type": "airfare",
        "invoice_material_id": material_id,
        "cabin_field_names": ["cabin_class", "seat_class", "cabin"],
        "requires_cabin_proof": True,
        "itinerary_material_ids": [itinerary_material_id],
        "order_screenshot_material_ids": [],
        "recognized_cabin_materials": [
            {
                "material_id": itinerary_material_id,
                "material_type": "itinerary",
                "field_name": "cabin_class",
                "field_value": "Economy",
                "recognition_task_id": recognition_task_id,
                "recognition_task_status": "succeeded",
            }
        ],
    }


def test_attach_order_screenshot_marks_airfare_cabin_validation_pending_when_cabin_missing(
    tmp_path,
):
    client = make_client(tmp_path)
    task_id, material_id = create_airfare_material(client)
    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {
            "seller_name": "海南航空",
            "expense_type": "airfare",
        },
    )
    invoice_id = invoice_response.json()["invoice"]["id"]
    itinerary_material_id = upload_supporting_material(
        client,
        task_id,
        material_type="itinerary",
        filename="itinerary.pdf",
        content_type="application/pdf",
    )
    order_screenshot_material_id = upload_supporting_material(
        client,
        task_id,
        material_type="order_screenshot",
        filename="order.png",
        content_type="image/png",
    )
    client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{itinerary_material_id}",
        headers=admin_auth_headers(client),
    )

    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{order_screenshot_material_id}",
        headers=admin_auth_headers(client),
    )

    assert attach_response.status_code == 200

    validations_response = client.get(f"/api/invoices/{invoice_id}/validations")

    assert validations_response.status_code == 200
    cabin_validation = next(
        item
        for item in validations_response.json()["items"]
        if item["rule_code"] == AIRFARE_CABIN_PROOF_RULE_CODE
    )
    assert cabin_validation["status"] == "pending"
    assert cabin_validation["message"] == "航空费用未识别到舱位信息，需结合订单截图人工确认"
    assert cabin_validation["evidence"] == {
        "expense_type": "airfare",
        "invoice_material_id": material_id,
        "cabin_field_names": ["cabin_class", "seat_class", "cabin"],
        "requires_cabin_proof": True,
        "itinerary_material_ids": [itinerary_material_id],
        "order_screenshot_material_ids": [order_screenshot_material_id],
        "recognized_cabin_materials": [],
    }


def test_attach_payment_record_fails_amount_match_when_total_differs_from_invoice(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)
    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {"amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS},
    )
    invoice_id = invoice_response.json()["invoice"]["id"]
    payment_record_material_id = upload_supporting_material(
        client,
        task_id,
        material_type="payment_record",
    )
    set_recognition_amount_cents(
        client,
        payment_record_material_id,
        amount_cents=PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS - 1,
    )

    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{payment_record_material_id}",
        headers=admin_auth_headers(client),
    )

    assert attach_response.status_code == 200

    validations_response = client.get(f"/api/invoices/{invoice_id}/validations")

    assert validations_response.status_code == 200
    payment_amount_validation = next(
        item
        for item in validations_response.json()["items"]
        if item["rule_code"] == "invoice_payment_record_amount_match"
    )
    assert payment_amount_validation["status"] == "failed"
    assert payment_amount_validation["message"] == "支付记录金额合计与发票金额不一致"
    assert payment_amount_validation["evidence"]["payment_record_amount_total_cents"] == (
        PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS - 1
    )


def test_retry_payment_record_recognition_revalidates_failed_amount_match_to_pass(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)
    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {"amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS},
    )
    invoice_id = invoice_response.json()["invoice"]["id"]
    payment_record_material_id = upload_supporting_material(
        client,
        task_id,
        material_type="payment_record",
    )
    set_recognition_amount_cents(
        client,
        payment_record_material_id,
        amount_cents=PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS - 1,
    )

    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{payment_record_material_id}",
        headers=admin_auth_headers(client),
    )

    assert attach_response.status_code == 200

    failed_validations = client.get(f"/api/invoices/{invoice_id}/validations")

    assert failed_validations.status_code == 200
    assert next(
        item
        for item in failed_validations.json()["items"]
        if item["rule_code"] == "invoice_payment_record_amount_match"
    )["status"] == "failed"

    retry_create = client.post(
        f"/api/materials/{payment_record_material_id}/recognition-tasks",
        headers=admin_auth_headers(client),
    )

    assert retry_create.status_code == 201
    retry_task_id = retry_create.json()["item"]["id"]
    retry_update = client.patch(
        f"/api/recognition-tasks/{retry_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "succeeded",
            "result": {
                "raw_response": {
                    "provider": "placeholder-ai",
                    "document_type": "payment_record",
                },
                "recognized_fields": {
                    "amount_cents": {
                        "value": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
                        "source": "ai",
                        "confidence": 0.98,
                        "status": "recognized",
                    }
                },
            },
        },
    )

    assert retry_update.status_code == 200

    validations_response = client.get(f"/api/invoices/{invoice_id}/validations")

    assert validations_response.status_code == 200
    payment_amount_validation = next(
        item
        for item in validations_response.json()["items"]
        if item["rule_code"] == "invoice_payment_record_amount_match"
    )
    assert payment_amount_validation["status"] == "passed"
    assert payment_amount_validation["message"] == "支付记录金额与发票金额一致"
    assert payment_amount_validation["evidence"] == {
        "invoice_amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
        "threshold_amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
        "matching_mode": PAYMENT_RECORD_AMOUNT_MATCH_MODE,
        "config_source": (
            "trms_backend.domain.invoice_validation.PAYMENT_RECORD_AMOUNT_MATCH_MODE"
        ),
        "requires_payment_record": True,
        "payment_record_material_ids": [payment_record_material_id],
        "matched_payment_records": [
            {
                "material_id": payment_record_material_id,
                "recognized_amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
                "recognition_task_id": retry_task_id,
                "recognition_task_status": "succeeded",
            }
        ],
        "missing_amount_materials": [],
        "payment_record_amount_total_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
    }


def test_attach_payment_record_marks_amount_match_pending_when_amount_missing(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)
    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {"amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS},
    )
    invoice_id = invoice_response.json()["invoice"]["id"]
    payment_record_material_id = upload_supporting_material(
        client,
        task_id,
        material_type="payment_record",
    )
    recognition_task_id = set_recognition_amount_cents(
        client,
        payment_record_material_id,
        amount_cents=None,
    )

    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{payment_record_material_id}",
        headers=admin_auth_headers(client),
    )

    assert attach_response.status_code == 200

    validations_response = client.get(f"/api/invoices/{invoice_id}/validations")

    assert validations_response.status_code == 200
    payment_amount_validation = next(
        item
        for item in validations_response.json()["items"]
        if item["rule_code"] == "invoice_payment_record_amount_match"
    )
    assert payment_amount_validation["status"] == "pending"
    assert payment_amount_validation["message"] == "支付记录金额缺失，需人工确认"
    assert payment_amount_validation["evidence"] == {
        "invoice_amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
        "threshold_amount_cents": PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS,
        "matching_mode": PAYMENT_RECORD_AMOUNT_MATCH_MODE,
        "config_source": (
            "trms_backend.domain.invoice_validation.PAYMENT_RECORD_AMOUNT_MATCH_MODE"
        ),
        "requires_payment_record": True,
        "payment_record_material_ids": [payment_record_material_id],
        "matched_payment_records": [],
        "missing_amount_materials": [
            {
                "material_id": payment_record_material_id,
                "recognition_task_id": recognition_task_id,
                "recognition_task_status": "succeeded",
            }
        ],
        "payment_record_amount_total_cents": 0,
    }


def test_retry_invoice_recognition_revalidates_failed_competition_location_to_pass(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)
    set_recognition_result(
        client,
        material_id,
        document_type="invoice",
        recognized_fields={
            "departure_location": {
                "value": "Nanjing South Railway Station",
                "source": "ai",
                "confidence": 0.95,
                "status": "recognized",
            },
            "arrival_location": {
                "value": "Suzhou Railway Station",
                "source": "ai",
                "confidence": 0.95,
                "status": "recognized",
            },
        },
    )

    create_response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    assert create_response.status_code == 201
    invoice_id = create_response.json()["invoice"]["id"]
    assert validation_by_code(
        create_response.json(),
        COMPETITION_LOCATION_RANGE_RULE_CODE,
    )["status"] == "failed"

    retry_create = client.post(
        f"/api/materials/{material_id}/recognition-tasks",
        headers=admin_auth_headers(client),
    )

    assert retry_create.status_code == 201
    retry_task_id = retry_create.json()["item"]["id"]
    retry_update = client.patch(
        f"/api/recognition-tasks/{retry_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "succeeded",
            "result": {
                "raw_response": {
                    "provider": "placeholder-ai",
                    "document_type": "invoice",
                },
                "recognized_fields": {
                    "departure_location": {
                        "value": "Nanjing South Railway Station",
                        "source": "ai",
                        "confidence": 0.95,
                        "status": "recognized",
                    },
                    "arrival_location": {
                        "value": "Shanghai Hongqiao Railway Station",
                        "source": "ai",
                        "confidence": 0.95,
                        "status": "recognized",
                    },
                },
            },
        },
    )

    assert retry_update.status_code == 200

    validations_response = client.get(f"/api/invoices/{invoice_id}/validations")

    assert validations_response.status_code == 200
    competition_location_validation = next(
        item
        for item in validations_response.json()["items"]
        if item["rule_code"] == COMPETITION_LOCATION_RANGE_RULE_CODE
    )
    assert competition_location_validation["status"] == "passed"
    assert competition_location_validation["message"] == "交易地点与比赛地点或往返路径基础匹配"
    assert competition_location_validation["evidence"]["matched_location_materials"] == [
        {
            "material_id": material_id,
            "material_type": "invoice",
            "matched_fields": {
                "departure_location": "Nanjing South Railway Station",
                "arrival_location": "Shanghai Hongqiao Railway Station",
            },
            "competition_location_match": True,
            "recognition_task_id": retry_task_id,
            "recognition_task_status": "succeeded",
        }
    ]
    assert competition_location_validation["evidence"]["unmatched_location_materials"] == []


def test_list_invoice_validations_returns_structured_evidence(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)

    create_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload() | {"buyer_name": "错误抬头"},
    )

    assert create_response.status_code == 201
    invoice_id = create_response.json()["invoice"]["id"]

    response = client.get(f"/api/invoices/{invoice_id}/validations")

    assert response.status_code == 200
    title_validation = next(
        item for item in response.json()["items"] if item["rule_code"] == "invoice_title_match"
    )
    assert title_validation["target_type"] == "invoice"
    assert title_validation["target_id"] == invoice_id
    assert title_validation["severity"] == "blocker"
    assert title_validation["status"] == "failed"
    assert title_validation["evidence"] == {
        "expected_buyer_name": "同济大学",
        "actual_buyer_name": "错误抬头",
    }


def test_create_invoice_updates_existing_material_invoice_instead_of_creating_duplicate(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)
    first_response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())
    first_invoice_id = first_response.json()["invoice"]["id"]

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {
            "amount_cents": 54321,
            "buyer_name": "错误抬头",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["invoice"]["id"] == first_invoice_id
    assert body["invoice"]["amount_cents"] == 54321
    assert validation_by_code(body, "invoice_title_match")["status"] == "failed"

    listed = client.get(f"/api/tasks/{task_id}/invoices")

    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1
    assert listed.json()["items"][0]["id"] == first_invoice_id
    assert listed.json()["items"][0]["amount_cents"] == 54321


def test_manual_invoice_correction_updates_recognition_fields_and_keeps_diff_history(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)
    recognition_task_id = client.get(f"/api/materials/{material_id}/recognition-tasks").json()["items"][0][
        "id"
    ]
    recognition_result = {
        "raw_response": {
            "provider": "placeholder-ai",
            "document_type": "invoice",
        },
        "recognized_fields": {
            "invoice_number": {
                "value": "INV-AI-001",
                "source": "ai",
                "confidence": 0.83,
                "status": "recognized",
            },
            "buyer_name": {
                "value": "Tongji ACM Lab",
                "source": "ocr",
                "confidence": 0.41,
                "status": "needs_confirmation",
            },
            "tax_number": {
                "value": "WRONG-TAX-NUMBER",
                "source": "ocr",
                "confidence": 0.38,
                "status": "needs_confirmation",
            },
        },
    }
    client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "needs_confirmation",
            "result": recognition_result,
        },
    )

    first_response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    assert first_response.status_code == 201
    assert validation_by_code(first_response.json(), "invoice_title_match")["status"] == "passed"
    assert validation_by_code(first_response.json(), "invoice_tax_number_match")["status"] == "passed"

    second_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload() | {"buyer_name": "错误抬头"},
    )

    assert second_response.status_code == 201
    assert validation_by_code(second_response.json(), "invoice_title_match")["status"] == "failed"

    recognition_task = client.get(f"/api/materials/{material_id}/recognition-tasks").json()["items"][0]

    assert recognition_task["recognized_fields"]["buyer_name"]["value"] == "错误抬头"
    assert recognition_task["recognized_fields"]["buyer_name"]["source"] == "manual"
    assert recognition_task["recognized_fields"]["buyer_name"]["updated_at"] is not None
    assert recognition_task["recognized_fields"]["tax_number"]["value"] == "12100000425006117D"
    assert recognition_task["recognized_fields"]["tax_number"]["source"] == "manual"

    buyer_name_corrections = manual_corrections_by_field(recognition_task, "buyer_name")
    tax_number_corrections = manual_corrections_by_field(recognition_task, "tax_number")

    assert len(buyer_name_corrections) == 2
    assert len(tax_number_corrections) == 1
    assert buyer_name_corrections[0]["before"]["value"] == "Tongji ACM Lab"
    assert buyer_name_corrections[0]["before"]["source"] == "ocr"
    assert buyer_name_corrections[0]["after"]["value"] == "同济大学"
    assert buyer_name_corrections[0]["after"]["source"] == "manual"
    assert buyer_name_corrections[0]["revalidation_status"] == "triggered"
    assert buyer_name_corrections[0]["corrected_at"] is not None
    assert buyer_name_corrections[1]["before"]["value"] == "同济大学"
    assert buyer_name_corrections[1]["before"]["source"] == "manual"
    assert buyer_name_corrections[1]["after"]["value"] == "错误抬头"
    assert tax_number_corrections[0]["before"]["value"] == "WRONG-TAX-NUMBER"
    assert tax_number_corrections[0]["after"]["value"] == "12100000425006117D"

    audit_logs = list_recognition_task_audit_logs(tmp_path, recognition_task_id)

    assert [item.action for item in audit_logs] == [
        "record_recognition_result",
        "apply_manual_recognition_corrections",
        "apply_manual_recognition_corrections",
    ]
    assert audit_logs[1].actor_id == "2250001"
    assert audit_logs[1].result is AuditLogResult.SUCCEEDED
    assert audit_logs[1].detail["material_id"] == material_id
    assert audit_logs[1].detail["correction_count"] == 8
    assert audit_logs[1].detail["changed_fields"][0]["field_name"] == "invoice_number"
    assert audit_logs[1].detail["changed_fields"][0]["before"]["value"] == "INV-AI-001"
    assert audit_logs[1].detail["changed_fields"][0]["before"]["source"] == "ai"
    assert audit_logs[1].detail["changed_fields"][0]["after"]["value"] == "INV-001"
    assert audit_logs[2].actor_id == "2250001"
    assert audit_logs[2].result is AuditLogResult.SUCCEEDED
    assert audit_logs[2].detail["correction_count"] == 1
    changed_field = audit_logs[2].detail["changed_fields"][0]
    assert changed_field["field_name"] == "buyer_name"
    assert changed_field["before"]["value"] == "同济大学"
    assert changed_field["before"]["source"] == "manual"
    assert changed_field["before"]["status"] == "recognized"
    assert changed_field["before"]["confidence"] == 1.0
    assert changed_field["before"]["updated_at"] is not None
    assert changed_field["after"]["value"] == "错误抬头"
    assert changed_field["after"]["source"] == "manual"
    assert changed_field["after"]["status"] == "recognized"
    assert changed_field["after"]["confidence"] == 1.0
    assert changed_field["after"]["updated_at"] is not None
    assert changed_field["revalidation_status"] == "triggered"
    assert changed_field["corrected_at"] is not None


def test_manual_invoice_correction_on_retry_keeps_older_recognition_history_unchanged(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)
    first_recognition_task_id = client.get(f"/api/materials/{material_id}/recognition-tasks").json()[
        "items"
    ][0]["id"]
    first_result = {
        "raw_response": {
            "provider": "placeholder-ai",
            "document_type": "invoice",
        },
        "recognized_fields": {
            "buyer_name": {
                "value": "Tongji ACM Lab",
                "source": "ocr",
                "confidence": 0.44,
                "status": "needs_confirmation",
            }
        },
    }
    first_update = client.patch(
        f"/api/recognition-tasks/{first_recognition_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "needs_confirmation",
            "result": first_result,
        },
    )

    assert first_update.status_code == 200

    retry_create = client.post(
        f"/api/materials/{material_id}/recognition-tasks",
        headers=admin_auth_headers(client),
    )

    assert retry_create.status_code == 201
    retry_task_id = retry_create.json()["item"]["id"]

    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload(),
    )

    assert invoice_response.status_code == 201

    listed = client.get(f"/api/materials/{material_id}/recognition-tasks")

    assert listed.status_code == 200
    body = listed.json()
    assert [item["id"] for item in body["items"]] == [first_recognition_task_id, retry_task_id]
    assert body["items"][0]["recognized_fields"]["buyer_name"]["value"] == "Tongji ACM Lab"
    assert body["items"][0]["recognized_fields"]["buyer_name"]["source"] == "ocr"
    assert body["items"][0]["manual_corrections"] == []
    assert body["items"][1]["status"] == "needs_confirmation"
    assert body["items"][1]["recognized_fields"]["buyer_name"]["value"] == "同济大学"
    assert body["items"][1]["recognized_fields"]["buyer_name"]["source"] == "manual"
    assert body["items"][1]["manual_corrections"] != []
    assert body["latest_effective"]["id"] == retry_task_id


def test_create_invoice_rejects_expense_type_not_allowed_by_task(tmp_path):
    client = make_client(tmp_path)
    task_payload = valid_task_payload() | {"fee_categories": ["registration", "hotel"]}
    task = create_admin_task(client, payload=task_payload)
    client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    material_id = upload_material(client, task["id"])

    response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "invoice expense type railway is not allowed for task; "
        "allowed fee categories: registration, hotel"
    )


def test_list_invoices_by_task(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)
    client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    response = client.get(f"/api/tasks/{task_id}/invoices")

    assert response.status_code == 200
    assert [item["invoice_number"] for item in response.json()["items"]] == ["INV-001"]


def test_create_invoice_rejects_missing_material(tmp_path):
    client = make_client(tmp_path)

    response = client.post("/api/materials/missing/invoice", json=valid_invoice_payload())

    assert response.status_code == 404
    assert response.json()["detail"] == "material not found"


def test_create_invoice_rejects_non_invoice_material(tmp_path):
    client = make_client(tmp_path)
    task = create_admin_task(client)
    client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    material_id = upload_supporting_material(client, task["id"], material_type="payment_record")

    response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    assert response.status_code == 409
    assert response.json()["detail"] == "invoice can only be created from invoice material"


def test_attach_supporting_material_allows_same_attachment_for_multiple_invoices(tmp_path):
    client = make_client(tmp_path)
    task_id, first_material_id = create_material(client)
    second_material_id = upload_material(client, task_id, "ticket-2.pdf")
    supporting_material_id = upload_supporting_material(client, task_id)
    first_invoice_id = client.post(
        f"/api/materials/{first_material_id}/invoice",
        json=valid_invoice_payload(),
    ).json()["invoice"]["id"]
    second_invoice_id = client.post(
        f"/api/materials/{second_material_id}/invoice",
        json=valid_invoice_payload() | {"invoice_number": "INV-002"},
    ).json()["invoice"]["id"]

    first_response = client.put(
        f"/api/invoices/{first_invoice_id}/supporting-materials/{supporting_material_id}",
        headers=admin_auth_headers(client),
    )
    second_response = client.put(
        f"/api/invoices/{second_invoice_id}/supporting-materials/{supporting_material_id}",
        headers=admin_auth_headers(client),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    listed_first = client.get(f"/api/invoices/{first_invoice_id}/supporting-materials")
    listed_second = client.get(f"/api/invoices/{second_invoice_id}/supporting-materials")

    assert listed_first.status_code == 200
    assert listed_second.status_code == 200
    assert [item["id"] for item in listed_first.json()["items"]] == [supporting_material_id]
    assert [item["id"] for item in listed_second.json()["items"]] == [supporting_material_id]


def test_create_invoice_auto_links_existing_same_submitter_supporting_materials_when_single_candidate(tmp_path):
    client = make_client(tmp_path)
    task_id, invoice_material_id = create_material(client)
    payment_record_material_id = upload_supporting_material(
        client,
        task_id,
        material_type="payment_record",
        filename="payment.png",
    )
    competition_notice_material_id = upload_supporting_material(
        client,
        task_id,
        material_type="competition_notice",
        filename="notice.pdf",
        content_type="application/pdf",
    )

    response = client.post(
        f"/api/materials/{invoice_material_id}/invoice",
        json=valid_invoice_payload(),
    )

    assert response.status_code == 201
    invoice_id = response.json()["invoice"]["id"]
    listed = client.get(f"/api/invoices/{invoice_id}/supporting-materials")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [
        payment_record_material_id,
        competition_notice_material_id,
    ]


def test_detach_supporting_material_removes_invoice_association(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)
    invoice_id = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload(),
    ).json()["invoice"]["id"]
    supporting_material_id = upload_supporting_material(client, task_id)
    client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}",
        headers=admin_auth_headers(client),
    )

    response = client.delete(
        f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    listed = client.get(f"/api/invoices/{invoice_id}/supporting-materials")

    assert listed.status_code == 200
    assert listed.json()["items"] == []


def test_upload_supporting_material_keeps_unlinked_when_no_invoice_candidate(tmp_path):
    client = make_client(tmp_path)
    task = create_admin_task(client)
    client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )

    response = client.post(
        f"/api/tasks/{task['id']}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "payment_record",
        },
        files={"files": ("payment.png", b"payment-proof", "image/png")},
    )

    assert response.status_code == 201
    material_id = response.json()["items"][0]["id"]
    assert list_linked_invoice_ids_for_supporting_material(tmp_path, material_id) == []


def test_upload_supporting_material_keeps_unlinked_when_multiple_invoice_candidates_exist(tmp_path):
    client = make_client(tmp_path)
    task_id, first_material_id = create_material(client)
    second_material_id = upload_material(client, task_id, "ticket-2.pdf")
    create_invoice_for_material(client, first_material_id)
    create_invoice_for_material(client, second_material_id, invoice_number="INV-002")

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "payment_record",
        },
        files={"files": ("payment.png", b"payment-proof", "image/png")},
    )

    assert response.status_code == 201
    material_id = response.json()["items"][0]["id"]
    assert list_linked_invoice_ids_for_supporting_material(tmp_path, material_id) == []


def test_attach_supporting_material_rejects_invoice_type_material(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)
    invoice_id = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload(),
    ).json()["invoice"]["id"]
    another_invoice_material_id = upload_material(client, task_id, "ticket-2.pdf")

    response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{another_invoice_material_id}",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "supporting material must not be invoice type"
