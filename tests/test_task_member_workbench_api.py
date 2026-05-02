from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from test_task_member_status_api import (
    create_invoice,
    create_open_task,
    member_auth_headers,
    upload_material,
)
from test_tasks_api import admin_auth_headers, create_task, valid_task_payload


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


def mark_recognition_succeeded(
    client: TestClient,
    material_id: str,
    *,
    buyer_name: str = "同济大学",
    tax_number: str = "12100000425006117D",
    raw_response: dict[str, object] | None = None,
    recognized_fields: dict[str, object] | None = None,
) -> None:
    list_response = client.get(
        f"/api/materials/{material_id}/recognition-tasks",
        headers=admin_auth_headers(client),
    )
    assert list_response.status_code == 200
    latest_effective = list_response.json()["latest_effective"]
    if latest_effective is None:
        create_response = client.post(
            f"/api/materials/{material_id}/recognition-tasks",
            headers=admin_auth_headers(client),
        )
        assert create_response.status_code == 201
        list_response = client.get(
            f"/api/materials/{material_id}/recognition-tasks",
            headers=admin_auth_headers(client),
        )
        assert list_response.status_code == 200
        latest_effective = list_response.json()["items"][0]
    recognition_task_id = latest_effective["id"]

    update_response = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "succeeded",
            "result": {
                "raw_response": raw_response or {"provider": "test-provider", "trace": "raw"},
                "recognized_fields": {
                    "buyer_name": {
                        "value": buyer_name,
                        "source": "manual",
                        "confidence": 1,
                        "status": "recognized",
                    },
                    "tax_number": {
                        "value": tax_number,
                        "source": "manual",
                        "confidence": 1,
                        "status": "recognized",
                    },
                    **(recognized_fields or {}),
                },
            },
        },
    )
    assert update_response.status_code == 200


def create_ready_workbench_fixture(client: TestClient) -> tuple[str, str]:
    task_id = create_open_task(client)
    material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="ready-railway.pdf",
    )
    invoice_id = create_invoice(
        client,
        material_id,
        actor_id="2250001",
        invoice_number="READY-001",
        amount_cents=5000,
        expense_type="railway",
    )
    split_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 5000, "note": "self paid"},
            ],
        },
    )
    assert split_response.status_code == 200
    split_id = split_response.json()["items"][0]["id"]
    confirmation_response = client.put(
        f"/api/splits/{split_id}/confirmation",
        json={
            "actor_id": "2250001",
            "member_id": "2250001",
            "status": "confirmed",
        },
    )
    assert confirmation_response.status_code == 200
    mark_recognition_succeeded(client, material_id)
    return task_id, invoice_id


def create_blocked_workbench_fixture(client: TestClient) -> str:
    task_id = create_open_task(client)

    registration_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="registration.pdf",
    )
    create_invoice(
        client,
        registration_material_id,
        actor_id="2250001",
        invoice_number="REG-001",
        amount_cents=150000,
        expense_type="registration",
    )
    mark_recognition_succeeded(client, registration_material_id)

    railway_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="railway.pdf",
    )
    create_invoice(
        client,
        railway_material_id,
        actor_id="2250001",
        invoice_number="RAIL-001",
        amount_cents=5000,
        expense_type="railway",
    )
    mark_recognition_succeeded(client, railway_material_id)

    upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="order_screenshot",
        filename="order.png",
        content_type="image/png",
    )
    return task_id


def create_redaction_fixture(client: TestClient) -> str:
    task_id = create_open_task(client)

    shared_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="shared-registration.pdf",
    )
    shared_invoice_id = create_invoice(
        client,
        shared_material_id,
        actor_id="2250001",
        invoice_number="SHARED-001",
        amount_cents=20000,
        expense_type="registration",
    )
    mark_recognition_succeeded(client, shared_material_id)

    own_support_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="payment_record",
        filename="member-one-payment.png",
        content_type="image/png",
    )
    other_support_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250002",
        material_type="order_screenshot",
        filename="member-two-order.png",
        content_type="image/png",
    )
    assert client.put(
        f"/api/invoices/{shared_invoice_id}/supporting-materials/{own_support_material_id}",
        headers=admin_auth_headers(client),
    ).status_code == 200
    assert client.put(
        f"/api/invoices/{shared_invoice_id}/supporting-materials/{other_support_material_id}",
        headers=admin_auth_headers(client),
    ).status_code == 200
    split_response = client.put(
        f"/api/invoices/{shared_invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 12000, "note": "self paid"},
                {"member_id": "2250002", "amount_cents": 8000, "note": "shared"},
            ],
        },
    )
    assert split_response.status_code == 200

    own_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250002",
        material_type="invoice",
        filename="own-railway.pdf",
    )
    create_invoice(
        client,
        own_material_id,
        actor_id="2250002",
        invoice_number="OWN-001",
        amount_cents=5000,
        expense_type="railway",
    )
    mark_recognition_succeeded(
        client,
        own_material_id,
        raw_response={"provider": "sensitive-provider", "payload": {"token": "secret"}},
    )

    return task_id


def test_member_workbench_summary_returns_ready_state_and_submission_status(tmp_path):
    client = make_client(tmp_path)
    task_id, invoice_id = create_ready_workbench_fixture(client)

    before_submit = client.get(
        f"/api/tasks/{task_id}/member-workbench",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert before_submit.status_code == 200
    ready_item = before_submit.json()["items"][0]
    assert ready_item["invoice"]["invoice_number"] == "READY-001"
    assert ready_item["invoice"]["member_submission_status"] == "unsubmitted"
    assert ready_item["ready_for_submission"] is True
    assert ready_item["queue_group"] == "ready"
    assert ready_item["blocking_reasons"] == []

    submit_response = client.post(
        f"/api/tasks/{task_id}/invoice-submissions",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
        json={"invoice_ids": [invoice_id]},
    )
    assert submit_response.status_code == 200

    after_submit = client.get(
        f"/api/tasks/{task_id}/member-workbench",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert after_submit.status_code == 200
    ready_item = after_submit.json()["items"][0]
    assert ready_item["invoice"]["member_submission_status"] == "submitted"
    assert ready_item["ready_for_submission"] is True


def test_member_workbench_summary_maps_blocking_reasons_and_pending_linkage(tmp_path):
    client = make_client(tmp_path)
    task_id = create_blocked_workbench_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/member-workbench",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["pending_supporting_material_linkage_items"]) == 1

    items_by_invoice_number = {
        item["invoice"]["invoice_number"]: item
        for item in body["items"]
        if item["invoice"] is not None
    }
    assert items_by_invoice_number["REG-001"]["ready_for_submission"] is False
    assert items_by_invoice_number["REG-001"]["queue_group"] == "missing_materials"
    assert items_by_invoice_number["REG-001"]["blocking_reasons"] == [
        "missing_materials",
    ]
    assert sorted(
        entry["required_material_type"]
        for entry in items_by_invoice_number["REG-001"]["missing_materials"]
    ) == ["competition_notice", "payment_record"]

    assert items_by_invoice_number["RAIL-001"]["ready_for_submission"] is True
    assert items_by_invoice_number["RAIL-001"]["queue_group"] == "ready"
    assert items_by_invoice_number["RAIL-001"]["blocking_reasons"] == []


def test_member_workbench_paper_invoice_ignores_receipt_confirmation_for_member_submission_readiness(
    tmp_path,
):
    client = make_client(tmp_path)
    task = create_task(
        client,
        payload=valid_task_payload() | {"fee_categories": ["registration", "railway", "hotel"]},
    )
    assert client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    ).status_code == 200
    member_headers = member_auth_headers(client, username="paper-workbench-member", actor_id="2250001")

    create_response = client.post(
        f"/api/tasks/{task['id']}/paper-invoices",
        json={"expense_type": "railway", "amount_cents": 8800},
        headers=member_headers,
    )
    assert create_response.status_code == 201

    response = client.get(
        f"/api/tasks/{task['id']}/member-workbench",
        headers=member_headers,
    )
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["invoice"]["is_paper_invoice"] is True
    assert item["ready_for_submission"] is True
    assert item["queue_group"] == "ready"
    assert item["blocking_reasons"] == []


def test_member_workbench_non_invoice_success_without_invoice_is_not_marked_as_recognition_review(
    tmp_path,
):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    supporting_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="payment_record",
        filename="payment.png",
        content_type="image/png",
    )
    mark_recognition_succeeded(
        client,
        supporting_material_id,
        recognized_fields={
            "material_type": {
                "value": "payment_record",
                "source": "ai",
                "confidence": 0.98,
                "status": "recognized",
                "updated_at": None,
            },
            "amount_cents": {
                "value": 12345,
                "source": "ai",
                "confidence": 0.93,
                "status": "recognized",
                "updated_at": None,
            },
        },
    )

    response = client.get(
        f"/api/tasks/{task_id}/member-workbench",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert response.status_code == 200
    body = response.json()
    payment_item = next(
        item
        for item in body["items"]
        if item["material"]["material_id"] == supporting_material_id
    )
    assert payment_item["invoice"] is None
    assert payment_item["recognition"]["status"] == "succeeded"
    assert payment_item["queue_group"] == "ready"
    assert payment_item["blocking_reasons"] == []
    assert payment_item["ready_for_submission"] is True


def test_member_workbench_summary_redacts_shared_attachment_details_and_recognition_raw_response(tmp_path):
    client = make_client(tmp_path)
    task_id = create_redaction_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/member-workbench",
        headers=member_auth_headers(client, username="member2", actor_id="2250002"),
    )

    assert response.status_code == 200
    body = response.json()

    own_item = next(
        item
        for item in body["items"]
        if item["invoice"] is not None and item["invoice"]["invoice_number"] == "OWN-001"
    )
    assert "raw_response" not in own_item["recognition"]
    assert own_item["recognition"]["recognized_fields"]["buyer_name"]["value"] == "同济大学"

    shared_item = next(
        item for item in body["shared_invoices"] if item["invoice_number"] == "SHARED-001"
    )
    assert shared_item["original_filename"] == "shared-registration.pdf"
    assert shared_item["submitter_id"] == "2250001"
    assert shared_item["validation_status"] == "failed"
    assert shared_item["supporting_materials"] == [
        {"material_type": "order_screenshot", "count": 1},
        {"material_type": "payment_record", "count": 1},
    ]
    assert "tax_number" not in shared_item
    assert "transaction_time" not in shared_item
    assert all("original_filename" not in item for item in shared_item["supporting_materials"])


def test_member_workbench_pending_linkage_keeps_remaining_candidates_after_partial_attachment(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    first_invoice_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="shared-first.pdf",
    )
    first_invoice_id = create_invoice(
        client,
        first_invoice_material_id,
        actor_id="2250001",
        invoice_number="PARTIAL-001",
        amount_cents=12345,
        expense_type="railway",
    )
    mark_recognition_succeeded(client, first_invoice_material_id)

    second_invoice_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="shared-second.pdf",
    )
    second_invoice_id = create_invoice(
        client,
        second_invoice_material_id,
        actor_id="2250001",
        invoice_number="PARTIAL-002",
        amount_cents=23456,
        expense_type="railway",
    )
    mark_recognition_succeeded(client, second_invoice_material_id)

    supporting_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="order_screenshot",
        filename="shared-order.png",
        content_type="image/png",
    )
    attach_response = client.put(
        f"/api/invoices/{first_invoice_id}/supporting-materials/{supporting_material_id}",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )
    assert attach_response.status_code == 200

    response = client.get(
        f"/api/tasks/{task_id}/member-workbench",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert response.status_code == 200
    body = response.json()
    item = next(
        item
        for item in body["pending_supporting_material_linkage_items"]
        if item["material_id"] == supporting_material_id
    )
    assert item["linked_invoices"] == [
        {
            "invoice_id": first_invoice_id,
            "invoice_number": "PARTIAL-001",
            "amount_cents": 12345,
            "expense_type": "railway",
            "original_filename": "shared-first.pdf",
        }
    ]
    assert item["candidate_invoices"] == [
        {
            "invoice_id": second_invoice_id,
            "invoice_number": "PARTIAL-002",
            "amount_cents": 23456,
            "expense_type": "railway",
            "original_filename": "shared-second.pdf",
        }
    ]


def test_member_workbench_shows_single_manual_candidate_when_auto_link_is_not_safe(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    invoice_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="member-one-invoice.pdf",
    )
    invoice_id = create_invoice(
        client,
        invoice_material_id,
        actor_id="2250001",
        invoice_number="MANUAL-001",
        amount_cents=10000,
        expense_type="railway",
    )
    mark_recognition_succeeded(client, invoice_material_id)

    supporting_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="payment_record",
        filename="member-one-payment.png",
        content_type="image/png",
    )

    response = client.get(
        f"/api/tasks/{task_id}/member-workbench",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert response.status_code == 200
    body = response.json()
    item = next(
        item
        for item in body["pending_supporting_material_linkage_items"]
        if item["material_id"] == supporting_material_id
    )
    assert item["pending_reason"] == "manual_confirmation_required"
    assert item["candidate_invoices"] == [
        {
            "invoice_id": invoice_id,
            "invoice_number": "MANUAL-001",
            "amount_cents": 10000,
            "expense_type": "railway",
            "original_filename": "member-one-invoice.pdf",
        }
    ]


def test_non_member_cannot_view_member_workbench_summary(tmp_path):
    client = make_client(tmp_path)
    task_id, _ = create_ready_workbench_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/member-workbench",
        headers=member_auth_headers(client, username="outsider", actor_id="2250999"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to view member workbench summary for this task"
