from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_tasks_api import update_task_row, valid_task_payload


def make_client(tmp_path):
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def create_open_task(client: TestClient) -> str:
    response = client.post("/api/tasks", json=valid_task_payload())
    task_id = response.json()["id"]
    response = client.patch(f"/api/tasks/{task_id}/status", json={"target_status": "open"})
    assert response.status_code == 200
    return task_id


def upload_invoice_material(
    client: TestClient,
    task_id: str,
    *,
    submitter_id: str = "2250001",
    filename: str = "ticket.pdf",
) -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": submitter_id,
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": (filename, filename.encode(), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["items"][0]["id"]


def create_registration_invoice(client: TestClient, material_id: str) -> str:
    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json={
            "actor_id": "2250001",
            "invoice_number": "INV-REMINDER-001",
            "issue_date": "2026-11-04",
            "transaction_time": "2026-11-01T08:00:00Z",
            "buyer_name": "同济大学",
            "tax_number": "12100000425006117D",
            "seller_name": "竞赛平台",
            "amount_cents": 150000,
            "expense_type": "registration",
        },
    )
    assert response.status_code == 201
    return response.json()["invoice"]["id"]


def create_unconfirmed_split(client: TestClient, invoice_id: str) -> str:
    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250002", "amount_cents": 150000, "note": "waiting confirmation"}
            ],
        },
    )
    assert response.status_code == 200
    return response.json()["items"][0]["id"]


def test_generate_automatic_reminder_tasks_creates_missing_material_and_unconfirmed_placeholders(
    tmp_path,
):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    material_id = upload_invoice_material(client, task_id)
    invoice_id = create_registration_invoice(client, material_id)
    split_id = create_unconfirmed_split(client, invoice_id)
    update_task_row(
        tmp_path,
        task_id,
        deadline=datetime.now(UTC) + timedelta(days=1),
    )

    response = client.post(
        f"/api/tasks/{task_id}/automatic-reminder-tasks",
        json={"actor_id": "admin-1"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["created_count"] == 2
    assert body["reused_count"] == 0
    items_by_kind = {item["kind"]: item for item in body["items"]}
    assert set(items_by_kind) == {"missing_materials", "unconfirmed_expenses"}

    missing_materials = items_by_kind["missing_materials"]
    assert missing_materials["member_id"] == "2250001"
    assert missing_materials["requested_by"] == "admin-1"
    assert missing_materials["status"] == "pending"
    assert missing_materials["payload"]["invoice_ids"] == [invoice_id]
    assert missing_materials["payload"]["required_material_types"] == [
        "payment_record",
        "competition_notice",
    ]

    unconfirmed = items_by_kind["unconfirmed_expenses"]
    assert unconfirmed["member_id"] == "2250002"
    assert unconfirmed["requested_by"] == "admin-1"
    assert unconfirmed["status"] == "pending"
    assert unconfirmed["payload"]["split_ids"] == [split_id]
    assert unconfirmed["payload"]["statuses"] == ["missing"]

    listed = client.get(
        f"/api/tasks/{task_id}/automatic-reminder-tasks",
        params={"actor_id": "admin-1"},
    )

    assert listed.status_code == 200
    assert listed.json() == {"items": body["items"]}


def test_generate_automatic_reminder_tasks_is_idempotent_for_same_snapshot(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    material_id = upload_invoice_material(client, task_id, filename="idempotent.pdf")
    invoice_id = create_registration_invoice(client, material_id)
    create_unconfirmed_split(client, invoice_id)

    first = client.post(
        f"/api/tasks/{task_id}/automatic-reminder-tasks",
        json={"actor_id": "admin-1"},
    )
    second = client.post(
        f"/api/tasks/{task_id}/automatic-reminder-tasks",
        json={"actor_id": "admin-1"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    first_body = first.json()
    second_body = second.json()
    assert first_body["created_count"] == 2
    assert first_body["reused_count"] == 0
    assert second_body["created_count"] == 0
    assert second_body["reused_count"] == 2
    assert [item["id"] for item in second_body["items"]] == [
        item["id"] for item in first_body["items"]
    ]


def test_non_administrator_cannot_manage_automatic_reminder_tasks(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    create_response = client.post(
        f"/api/tasks/{task_id}/automatic-reminder-tasks",
        json={"actor_id": "2250001"},
    )
    list_response = client.get(
        f"/api/tasks/{task_id}/automatic-reminder-tasks",
        params={"actor_id": "2250001"},
    )

    assert create_response.status_code == 403
    assert create_response.json()["detail"] == (
        "actor is not allowed to manage automatic reminder tasks for this task"
    )
    assert list_response.status_code == 403
    assert list_response.json()["detail"] == (
        "actor is not allowed to manage automatic reminder tasks for this task"
    )
