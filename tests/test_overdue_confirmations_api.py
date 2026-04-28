from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_invoices_api import valid_invoice_payload
from test_tasks_api import (
    admin_auth_headers,
    auth_headers,
    create_task,
    register_and_get_token,
    update_task_row,
)


def make_client(tmp_path):
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
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


def create_split_fixture(client: TestClient) -> tuple[str, str, dict[str, str]]:
    task_id = create_open_task(client)
    material_id = upload_invoice_material(client, task_id)
    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload(),
    )
    assert response.status_code == 201
    invoice_id = response.json()["invoice"]["id"]

    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 4000, "note": "leader share"},
                {"member_id": "2250002", "amount_cents": 4000, "note": "missing confirmation"},
                {"member_id": "2250003", "amount_cents": 4345, "note": "needs reconfirmation"},
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
        f"/api/splits/{split_ids['2250003']}/confirmation",
        json={"actor_id": "2250003", "member_id": "2250003", "status": "confirmed"},
    )
    assert response.status_code == 200

    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "admin-1",
            "items": [
                {"member_id": "2250001", "amount_cents": 4000, "note": "leader share"},
                {"member_id": "2250002", "amount_cents": 4000, "note": "missing confirmation"},
                {"member_id": "2250003", "amount_cents": 4345, "note": "needs reconfirmation updated"},
            ],
        },
    )
    assert response.status_code == 200

    return task_id, invoice_id, split_ids


def test_task_administrator_can_list_overdue_unconfirmed_members_after_deadline(tmp_path):
    client = make_client(tmp_path)
    task_id, invoice_id, split_ids = create_split_fixture(client)
    update_task_row(
        tmp_path,
        task_id,
        deadline=datetime.now(UTC) - timedelta(seconds=1),
    )

    response = client.get(
        f"/api/tasks/{task_id}/overdue-confirmations",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["administrator_id"] == "admin-1"
    assert body["is_overdue"] is True
    assert body["total_overdue_members"] == 2
    assert body["overdue_member_ids"] == ["2250002", "2250003"]
    items_by_split_id = {item["split_id"]: item for item in body["items"]}
    assert set(items_by_split_id) == {split_ids["2250002"], split_ids["2250003"]}
    assert items_by_split_id[split_ids["2250002"]]["status"] == "missing"
    assert items_by_split_id[split_ids["2250002"]]["invoice"]["id"] == invoice_id
    assert items_by_split_id[split_ids["2250002"]]["last_confirmation_at"] is None
    assert items_by_split_id[split_ids["2250003"]]["status"] == "pending"
    assert items_by_split_id[split_ids["2250003"]]["split_version"] == 2
    assert items_by_split_id[split_ids["2250003"]]["last_confirmation_at"] is not None


def test_task_overdue_confirmation_list_is_empty_before_deadline(tmp_path):
    client = make_client(tmp_path)
    task_id, _, _ = create_split_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/overdue-confirmations",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json() == {
        "task_id": task_id,
        "administrator_id": "admin-1",
        "confirmation_deadline": "2026-12-01T00:00:00",
        "is_overdue": False,
        "total_overdue_members": 0,
        "overdue_member_ids": [],
        "items": [],
    }


def test_non_administrator_cannot_list_task_overdue_confirmations(tmp_path):
    client = make_client(tmp_path)
    task_id, _, _ = create_split_fixture(client)
    update_task_row(
        tmp_path,
        task_id,
        deadline=datetime.now(UTC) - timedelta(seconds=1),
    )
    member_token = register_and_get_token(
        client,
        username="member1",
        role="member",
        actor_id="2250001",
        member_code="2250001",
    )

    response = client.get(
        f"/api/tasks/{task_id}/overdue-confirmations",
        params={"actor_id": "2250001"},
        headers=auth_headers(member_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "actor is not allowed to view overdue confirmations for this task"
    )
