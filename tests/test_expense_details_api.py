from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_invoices_api import valid_invoice_payload
from test_tasks_api import valid_task_payload


def make_client(tmp_path):
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def create_task(client: TestClient) -> str:
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


def create_split_fixture(client: TestClient) -> tuple[str, str, dict[str, str]]:
    task_id = create_task(client)
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
                {"member_id": "2250001", "amount_cents": 6000, "note": "self paid"},
                {"member_id": "2250002", "amount_cents": 6345, "note": "team shared"},
            ],
        },
    )
    assert response.status_code == 200
    split_ids = {item["member_id"]: item["id"] for item in response.json()["items"]}

    response = client.put(
        f"/api/splits/{split_ids['2250002']}/confirmation",
        json={"member_id": "2250002", "status": "confirmed"},
    )
    assert response.status_code == 200

    return task_id, invoice_id, split_ids


def test_member_can_list_only_own_expense_details(tmp_path):
    client = make_client(tmp_path)
    task_id, invoice_id, _ = create_split_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        params={"actor_id": "2250002"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "member"
    assert body["actor_id"] == "2250002"
    assert body["total_amount_cents"] == 6345
    assert len(body["items"]) == 1
    assert body["items"][0]["member_id"] == "2250002"
    assert body["items"][0]["amount_cents"] == 6345
    assert body["items"][0]["invoice"]["id"] == invoice_id
    assert body["items"][0]["confirmation"]["status"] == "confirmed"


def test_task_member_without_related_splits_gets_empty_expense_details(tmp_path):
    client = make_client(tmp_path)
    task_id, _, _ = create_split_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        params={"actor_id": "2250003"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "actor_id": "2250003",
        "scope": "member",
        "total_amount_cents": 0,
        "items": [],
    }


def test_task_administrator_can_list_all_expense_details(tmp_path):
    client = make_client(tmp_path)
    task_id, invoice_id, split_ids = create_split_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        params={"actor_id": "admin-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "task"
    assert body["actor_id"] == "admin-1"
    assert body["total_amount_cents"] == 12345
    assert len(body["items"]) == 2
    items_by_split_id = {item["split_id"]: item for item in body["items"]}
    assert set(items_by_split_id) == set(split_ids.values())
    assert items_by_split_id[split_ids["2250001"]]["confirmation"] is None
    assert items_by_split_id[split_ids["2250001"]]["invoice"]["id"] == invoice_id
    assert items_by_split_id[split_ids["2250002"]]["confirmation"]["status"] == "confirmed"


def test_non_member_cannot_list_task_expense_details(tmp_path):
    client = make_client(tmp_path)
    task_id, _, _ = create_split_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        params={"actor_id": "outsider-1"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to view expense details for this task"
