from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_tasks_api import admin_auth_headers, create_task, valid_task_payload


def make_client(tmp_path):
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def create_open_task(client: TestClient) -> str:
    task_id = create_task(
        client,
        payload=valid_task_payload() | {"fee_categories": ["registration", "railway"]},
    )["id"]
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
    submitter_id: str,
    filename: str,
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


def create_invoice(
    client: TestClient,
    material_id: str,
    *,
    actor_id: str,
    invoice_number: str,
    amount_cents: int,
    expense_type: str,
) -> str:
    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json={
            "actor_id": actor_id,
            "invoice_number": invoice_number,
            "issue_date": "2026-11-04",
            "transaction_time": "2026-11-01T08:00:00Z",
            "buyer_name": "同济大学",
            "tax_number": "12100000425006117D",
            "seller_name": "服务商",
            "amount_cents": amount_cents,
            "expense_type": expense_type,
        },
    )
    assert response.status_code == 201
    return response.json()["invoice"]["id"]


def create_missing_materials_fixture(client: TestClient) -> str:
    task_id = create_open_task(client)

    registration_material_id = upload_invoice_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="registration.pdf",
    )
    create_invoice(
        client,
        registration_material_id,
        actor_id="2250001",
        invoice_number="REG-001",
        amount_cents=150_000,
        expense_type="registration",
    )

    railway_material_id = upload_invoice_material(
        client,
        task_id,
        submitter_id="2250002",
        filename="railway.pdf",
    )
    create_invoice(
        client,
        railway_material_id,
        actor_id="2250002",
        invoice_number="RAIL-001",
        amount_cents=150_000,
        expense_type="railway",
    )

    return task_id


def test_task_administrator_can_list_missing_materials(tmp_path):
    client = make_client(tmp_path)
    task_id = create_missing_materials_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/missing-materials",
        params={"actor_id": "admin-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["actor_id"] == "admin-1"
    assert body["scope"] == "task"
    assert sorted(
        (item["member_id"], item["invoice_number"], item["required_material_type"])
        for item in body["items"]
    ) == [
        ("2250001", "REG-001", "competition_notice"),
        ("2250001", "REG-001", "payment_record"),
        ("2250002", "RAIL-001", "payment_record"),
    ]


def test_member_can_only_list_own_missing_materials(tmp_path):
    client = make_client(tmp_path)
    task_id = create_missing_materials_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/missing-materials",
        params={"actor_id": "2250002"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["actor_id"] == "2250002"
    assert body["scope"] == "member"
    assert [
        (item["member_id"], item["invoice_number"], item["required_material_type"])
        for item in body["items"]
    ] == [("2250002", "RAIL-001", "payment_record")]


def test_non_member_cannot_list_task_missing_materials(tmp_path):
    client = make_client(tmp_path)
    task_id = create_missing_materials_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/missing-materials",
        params={"actor_id": "2250999"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to view missing materials for this task"
