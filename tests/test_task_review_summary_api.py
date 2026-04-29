from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from test_tasks_api import (
    admin_auth_headers,
    auth_headers,
    create_task,
    register_and_get_token,
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


def upload_material(
    client: TestClient,
    task_id: str,
    *,
    material_type: str,
    submitter_id: str = "2250001",
    filename: str,
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


def create_review_fixture(client: TestClient) -> tuple[str, str, str, str]:
    task_id = create_open_task(client)
    invoice_material_id = upload_material(
        client,
        task_id,
        material_type="invoice",
        filename="invoice.pdf",
    )
    payment_material_id = upload_material(
        client,
        task_id,
        material_type="payment_record",
        filename="payment.pdf",
    )

    invoice_recognition_task_id = latest_recognition_task_id(client, invoice_material_id)
    response = client.patch(
        f"/api/recognition-tasks/{invoice_recognition_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "needs_confirmation",
            "result": {
                "raw_response": {"provider": "placeholder-ai", "document_type": "invoice"},
                "recognized_fields": {
                    "invoice_number": {
                        "value": "INV-001",
                        "source": "ai",
                        "confidence": 0.99,
                        "status": "recognized",
                    },
                    "buyer_name": {
                        "value": "同济大学",
                        "source": "ocr",
                        "confidence": 0.45,
                        "status": "needs_confirmation",
                    },
                },
            },
        },
    )
    assert response.status_code == 200

    payment_recognition_task_id = latest_recognition_task_id(client, payment_material_id)
    response = client.patch(
        f"/api/recognition-tasks/{payment_recognition_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "failed",
            "failure": {
                "stage": "ocr",
                "reason": "failed to extract amount from payment screenshot",
            },
        },
    )
    assert response.status_code == 200

    response = client.post(
        f"/api/materials/{invoice_material_id}/invoice",
        json=valid_invoice_payload(),
    )
    assert response.status_code == 201
    invoice_id = response.json()["invoice"]["id"]

    response = client.put(f"/api/invoices/{invoice_id}/supporting-materials/{payment_material_id}")
    assert response.status_code == 200

    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 6000, "note": "self paid"},
                {"member_id": "2250002", "amount_cents": 6345, "note": "team shared"},
            ],
        },
    )
    assert response.status_code == 200
    split_ids = {item["member_id"]: item["id"] for item in response.json()["items"]}

    response = client.put(
        f"/api/splits/{split_ids['2250001']}/confirmation",
        json={"actor_id": "2250001", "member_id": "2250001", "status": "confirmed"},
    )
    assert response.status_code == 200

    response = client.put(
        f"/api/splits/{split_ids['2250002']}/confirmation",
        json={
            "actor_id": "2250002",
            "member_id": "2250002",
            "status": "disputed",
            "dispute_reason": "shared amount should be lower",
        },
    )
    assert response.status_code == 200

    return task_id, invoice_id, invoice_material_id, payment_material_id


def test_task_administrator_can_get_review_summary(tmp_path):
    client = make_client(tmp_path)
    task_id, invoice_id, invoice_material_id, payment_material_id = create_review_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/review-summary",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["administrator_id"] == "admin-1"
    assert body["counts"]["material_count"] == 2
    assert body["counts"]["pending_assignment_material_count"] == 0
    assert body["counts"]["invoice_count"] == 1
    assert body["counts"]["split_count"] == 2
    assert body["counts"]["confirmed_split_count"] == 1
    assert body["counts"]["disputed_confirmation_count"] == 1
    assert body["counts"]["pending_confirmation_count"] == 0
    assert body["counts"]["missing_confirmation_count"] == 0
    assert body["counts"]["failed_recognition_count"] == 1
    assert body["counts"]["needs_confirmation_recognition_count"] == 1

    materials_by_id = {item["material"]["id"]: item for item in body["materials"]}
    assert materials_by_id[invoice_material_id]["invoice_id"] == invoice_id
    assert materials_by_id[invoice_material_id]["supporting_invoice_ids"] == []
    assert materials_by_id[invoice_material_id]["latest_recognition"]["status"] == (
        "needs_confirmation"
    )
    assert materials_by_id[payment_material_id]["invoice_id"] is None
    assert materials_by_id[payment_material_id]["supporting_invoice_ids"] == [invoice_id]
    assert materials_by_id[payment_material_id]["latest_recognition"]["status"] == "failed"
    assert materials_by_id[payment_material_id]["latest_recognition"]["failure"] == {
        "stage": "ocr",
        "reason": "failed to extract amount from payment screenshot",
    }
    assert body["pending_assignment_materials"] == []

    assert len(body["invoices"]) == 1
    invoice_item = body["invoices"][0]
    assert invoice_item["invoice"]["id"] == invoice_id
    assert invoice_item["supporting_material_ids"] == [payment_material_id]
    assert len(invoice_item["validations"]) == body["counts"]["validation_count"]
    splits_by_member_id = {
        item["split"]["member_id"]: item for item in invoice_item["splits"]
    }
    assert splits_by_member_id["2250001"]["confirmation"]["status"] == "confirmed"
    assert splits_by_member_id["2250002"]["confirmation"]["status"] == "disputed"
    assert splits_by_member_id["2250002"]["confirmation"]["dispute_reason"] == (
        "shared amount should be lower"
    )


def test_review_summary_includes_pending_assignment_materials_for_task_hint(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.post(
        "/api/materials/pending-assignment",
        data={
            "channel": "email",
            "material_type": "payment_record",
            "task_id_hint": task_id,
            "submitter_id_hint": "2250002",
        },
        files={"files": ("pending-pay.pdf", b"pending payment", "application/pdf")},
    )
    assert response.status_code == 201
    pending_material = response.json()["items"][0]

    response = client.get(
        f"/api/tasks/{task_id}/review-summary",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["material_count"] == 0
    assert body["counts"]["pending_assignment_material_count"] == 1
    assert len(body["pending_assignment_materials"]) == 1
    summary_pending_material = body["pending_assignment_materials"][0]
    assert summary_pending_material["id"] == pending_material["id"]
    assert summary_pending_material["status"] == "pending_assignment"
    assert summary_pending_material["task_id_hint"] == task_id
    assert summary_pending_material["submitter_id_hint"] == "2250002"
    assert summary_pending_material["original_filename"] == "pending-pay.pdf"
    assert body["materials"] == []


def test_non_administrator_cannot_get_review_summary(tmp_path):
    client = make_client(tmp_path)
    task_id, _, _, _ = create_review_fixture(client)
    member_token = register_and_get_token(
        client,
        username="member1",
        role="member",
        actor_id="2250001",
        member_code="2250001",
    )

    response = client.get(
        f"/api/tasks/{task_id}/review-summary",
        params={"actor_id": "2250001"},
        headers=auth_headers(member_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to view review summary for this task"
