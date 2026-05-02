from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from test_tasks_api import (
    admin_auth_headers,
    auth_headers,
    create_task,
    register_and_get_token,
    valid_task_payload,
    valid_invoice_payload,
)


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


def create_open_task(client: TestClient) -> str:
    task_id = create_task(client)["id"]
    response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    assert response.status_code == 200
    return task_id


def create_open_task_with_payload(client: TestClient, payload: dict) -> str:
    task_id = create_task(client, payload=payload)["id"]
    response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    assert response.status_code == 200
    return task_id


def upload_material(
    client: TestClient,
    task_id: str,
    *,
    material_type: str,
    filename: str,
    submitter_id: str = "2250001",
) -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": submitter_id,
            "channel": "web",
            "material_type": material_type,
        },
        files={"files": (filename, filename.encode(), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["items"][0]["id"]


def latest_recognition_task_id(client: TestClient, material_id: str) -> str:
    response = client.get(f"/api/materials/{material_id}/recognition-tasks")
    assert response.status_code == 200
    return response.json()["items"][-1]["id"]


def mark_invoice_recognition_succeeded(
    client: TestClient,
    material_id: str,
    *,
    invoice_number: str,
) -> None:
    recognition_task_id = latest_recognition_task_id(client, material_id)
    response = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "succeeded",
            "result": {
                "raw_response": {"provider": "placeholder-ai"},
                "recognized_fields": {
                    "invoice_number": {
                        "value": invoice_number,
                        "source": "ai",
                        "confidence": 0.99,
                        "status": "recognized",
                    },
                    "buyer_name": {
                        "value": "同济大学",
                        "source": "ai",
                        "confidence": 0.99,
                        "status": "recognized",
                    },
                    "tax_number": {
                        "value": "12100000425006117D",
                        "source": "ai",
                        "confidence": 0.99,
                        "status": "recognized",
                    },
                },
            },
        },
    )
    assert response.status_code == 200


def create_invoice(client: TestClient, material_id: str, **overrides) -> str:
    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload() | overrides,
    )
    assert response.status_code == 201
    return response.json()["invoice"]["id"]


def replace_splits(
    client: TestClient,
    invoice_id: str,
    *,
    actor_id: str = "2250001",
    items: list[dict] | None = None,
) -> list[dict]:
    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": actor_id,
            "items": items
            if items is not None
            else [{"member_id": "2250001", "amount_cents": 12345}],
        },
    )
    assert response.status_code == 200
    return response.json()["items"]


def confirm_split(
    client: TestClient,
    split_id: str,
    *,
    actor_id: str = "2250001",
    member_id: str = "2250001",
    status: str = "confirmed",
    dispute_reason: str | None = None,
) -> None:
    payload = {"actor_id": actor_id, "member_id": member_id, "status": status}
    if dispute_reason is not None:
        payload["dispute_reason"] = dispute_reason
    response = client.put(f"/api/splits/{split_id}/confirmation", json=payload)
    assert response.status_code == 200


def move_task_to_ready_to_export(client: TestClient, task_id: str) -> None:
    for target_status in ("closed", "reviewing", "ready_to_export"):
        response = client.patch(
            f"/api/tasks/{task_id}/status",
            json={"target_status": target_status},
            headers=admin_auth_headers(client),
        )
        assert response.status_code == 200


def test_task_readiness_reports_all_clear_when_task_can_export(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    invoice_material_id = upload_material(
        client,
        task_id,
        material_type="invoice",
        filename="invoice.pdf",
    )
    mark_invoice_recognition_succeeded(client, invoice_material_id, invoice_number="INV-READY-001")
    invoice_id = create_invoice(client, invoice_material_id)
    split_id = replace_splits(client, invoice_id)[0]["id"]
    confirm_split(client, split_id)
    move_task_to_ready_to_export(client, task_id)

    response = client.get(
        f"/api/tasks/{task_id}/readiness",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["administrator_id"] == "admin-1"
    assert body["ready_for_export"] is True
    assert body["counts"] == {
        "pending_recognition_count": 0,
        "failed_recognition_count": 0,
        "needs_confirmation_recognition_count": 0,
        "pending_supporting_material_linkage_count": 0,
        "missing_material_count": 0,
        "blocker_validation_count": 0,
        "split_incomplete_count": 0,
        "pending_confirmation_count": 0,
        "disputed_confirmation_count": 0,
        "export_blocking_reason_count": 0,
    }
    assert body["issues"] == []
    assert body["export_blocking_reasons"] == []


def test_task_readiness_reports_recognition_blockers(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    pending_material_id = upload_material(
        client,
        task_id,
        material_type="invoice",
        filename="pending.pdf",
    )
    failed_material_id = upload_material(
        client,
        task_id,
        material_type="payment_record",
        filename="failed.pdf",
    )
    review_material_id = upload_material(
        client,
        task_id,
        material_type="invoice",
        filename="review.pdf",
    )

    failed_task_id = latest_recognition_task_id(client, failed_material_id)
    failed_response = client.patch(
        f"/api/recognition-tasks/{failed_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "failed",
            "failure": {
                "stage": "ocr",
                "reason": "failed to extract payment fields",
            },
        },
    )
    assert failed_response.status_code == 200

    review_task_id = latest_recognition_task_id(client, review_material_id)
    review_response = client.patch(
        f"/api/recognition-tasks/{review_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "needs_confirmation",
            "result": {
                "raw_response": {"provider": "placeholder-ai"},
                "recognized_fields": {
                    "buyer_name": {
                        "value": "同济大学",
                        "source": "ocr",
                        "confidence": 0.42,
                        "status": "needs_confirmation",
                    }
                },
            },
        },
    )
    assert review_response.status_code == 200

    response = client.get(
        f"/api/tasks/{task_id}/readiness",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["pending_recognition_count"] == 1
    assert body["counts"]["failed_recognition_count"] == 1
    assert body["counts"]["needs_confirmation_recognition_count"] == 1
    issues_by_kind = {item["kind"]: item for item in body["issues"]}
    assert issues_by_kind["recognition_pending"]["material_ids"] == [pending_material_id]
    assert issues_by_kind["recognition_failed"]["material_ids"] == [failed_material_id]
    assert issues_by_kind["recognition_needs_confirmation"]["material_ids"] == [
        review_material_id
    ]


def test_task_readiness_does_not_count_non_invoice_needs_confirmation_as_review_blocker(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    payment_material_id = upload_material(
        client,
        task_id,
        material_type="payment_record",
        filename="payment.png",
    )

    payment_recognition_task_id = latest_recognition_task_id(client, payment_material_id)
    response = client.patch(
        f"/api/recognition-tasks/{payment_recognition_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "needs_confirmation",
            "result": {
                "raw_response": {"provider": "placeholder-ai", "document_type": "payment_record"},
                "recognized_fields": {
                    "material_type": {
                        "value": "payment_record",
                        "source": "ai",
                        "confidence": 0.95,
                        "status": "recognized",
                    },
                    "location": {
                        "value": "如家商旅酒店武汉大学街道口店",
                        "source": "ai",
                        "confidence": 0.7,
                        "status": "needs_confirmation",
                    },
                },
            },
        },
    )
    assert response.status_code == 200

    response = client.get(
        f"/api/tasks/{task_id}/readiness",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["needs_confirmation_recognition_count"] == 0
    issues_by_kind = {item["kind"]: item for item in body["issues"]}
    assert "recognition_needs_confirmation" not in issues_by_kind


def test_task_readiness_reports_supporting_material_and_missing_material_blockers(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task_with_payload(
        client,
        {
            "competition_name": "ICPC Asia Regional",
            "competition_location": "Shanghai",
            "competition_start_date": "2026-11-01",
            "competition_end_date": "2026-11-03",
            "deadline": "2026-12-01T00:00:00Z",
            "member_ids": ["2250001", "2250002", "2250003"],
            "fee_categories": ["registration", "railway", "hotel", "airfare"],
            "administrator_id": "admin-1",
            "project_info": "ACM competition project",
            "reimburser_info": "Lab reimbursement owner",
            "invoice_title": "同济大学",
            "tax_number": "12100000425006117D",
        },
    )
    invoice_material_id = upload_material(
        client,
        task_id,
        material_type="invoice",
        filename="ticket.pdf",
    )
    mark_invoice_recognition_succeeded(client, invoice_material_id, invoice_number="AIR-001")
    invoice_id = create_invoice(
        client,
        invoice_material_id,
        invoice_number="AIR-001",
        expense_type="airfare",
    )
    second_invoice_material_id = upload_material(
        client,
        task_id,
        material_type="invoice",
        filename="ticket-2.pdf",
    )
    mark_invoice_recognition_succeeded(client, second_invoice_material_id, invoice_number="AIR-002")
    second_invoice_id = create_invoice(
        client,
        second_invoice_material_id,
        invoice_number="AIR-002",
        expense_type="airfare",
        amount_cents=8888,
    )
    upload_material(
        client,
        task_id,
        material_type="order_screenshot",
        filename="order.png",
    )

    response = client.get(
        f"/api/tasks/{task_id}/readiness",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["pending_supporting_material_linkage_count"] == 1
    assert body["counts"]["missing_material_count"] >= 1
    assert body["counts"]["blocker_validation_count"] == 2
    issues_by_kind = {item["kind"]: item for item in body["issues"]}
    assert issues_by_kind["supporting_material_linkage"]["count"] == 1
    assert issues_by_kind["supporting_material_linkage"]["invoice_ids"] == [
        invoice_id,
        second_invoice_id,
    ]
    assert invoice_id in issues_by_kind["missing_materials"]["invoice_ids"]
    assert issues_by_kind["validation_blocker"]["invoice_ids"] == [
        invoice_id,
        second_invoice_id,
    ]


def test_task_readiness_reports_confirmation_and_split_blockers(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    first_invoice_material_id = upload_material(
        client,
        task_id,
        material_type="invoice",
        filename="first.pdf",
    )
    first_invoice_id = create_invoice(
        client,
        first_invoice_material_id,
        invoice_number="CONFIRM-001",
    )
    split_ids = [
        item["id"]
        for item in replace_splits(
            client,
            first_invoice_id,
            items=[
                {"member_id": "2250001", "amount_cents": 6000},
                {"member_id": "2250002", "amount_cents": 6345},
            ],
        )
    ]
    confirm_split(client, split_ids[0])
    confirm_split(
        client,
        split_ids[1],
        actor_id="2250002",
        member_id="2250002",
        status="disputed",
        dispute_reason="shared amount should be lower",
    )

    second_invoice_material_id = upload_material(
        client,
        task_id,
        material_type="invoice",
        filename="second.pdf",
    )
    second_invoice_id = create_invoice(
        client,
        second_invoice_material_id,
        invoice_number="SPLIT-001",
        amount_cents=20000,
    )
    create_invoice(
        client,
        second_invoice_material_id,
        actor_id="admin-1",
        invoice_number="SPLIT-001",
        amount_cents=21000,
    )

    response = client.get(
        f"/api/tasks/{task_id}/readiness",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["split_incomplete_count"] == 1
    assert body["counts"]["pending_confirmation_count"] == 0
    assert body["counts"]["disputed_confirmation_count"] == 1
    issues_by_kind = {item["kind"]: item for item in body["issues"]}
    assert issues_by_kind["split_incomplete"]["invoice_ids"] == [second_invoice_id]
    assert issues_by_kind["member_confirmation_disputed"]["split_ids"] == [split_ids[1]]


def test_non_administrator_cannot_get_task_readiness(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    outsider_admin_token = register_and_get_token(
        client,
        username="admin2",
        role="admin",
        actor_id="admin-2",
        member_code=None,
    )

    response = client.get(
        f"/api/tasks/{task_id}/readiness",
        params={"actor_id": "admin-2"},
        headers=auth_headers(outsider_admin_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to view task readiness for this task"


def test_secondary_administrator_can_get_task_readiness(tmp_path):
    client = make_client(tmp_path)
    secondary_admin_token = register_and_get_token(
        client,
        username="admin2",
        role="admin",
        actor_id="admin-2",
        member_code=None,
    )
    task_id = create_open_task_with_payload(
        client,
        {
            **valid_task_payload(),
            "administrator_ids": ["admin-1", "admin-2"],
        },
    )

    response = client.get(
        f"/api/tasks/{task_id}/readiness",
        params={"actor_id": "admin-2"},
        headers=auth_headers(secondary_admin_token),
    )

    assert response.status_code == 200
    assert response.json()["administrator_id"] == "admin-2"
