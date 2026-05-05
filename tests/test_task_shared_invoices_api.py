from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_task_member_status_api import member_auth_headers
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


def upload_material(
    client: TestClient,
    task_id: str,
    *,
    submitter_id: str,
    material_type: str,
    filename: str,
    content_type: str = "application/pdf",
) -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": submitter_id,
            "channel": "web",
            "material_type": material_type,
        },
        files={"files": (filename, filename.encode(), content_type)},
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


def create_shared_invoice_fixture(client: TestClient) -> str:
    task_id = create_open_task(client)

    member_one_invoice_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="member-one-registration.pdf",
    )
    member_one_invoice_id = create_invoice(
        client,
        member_one_invoice_material_id,
        actor_id="2250001",
        invoice_number="REG-001",
        amount_cents=20000,
        expense_type="railway",
    )

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
        f"/api/invoices/{member_one_invoice_id}/supporting-materials/{own_support_material_id}",
        headers=admin_auth_headers(client),
    ).status_code == 200
    assert client.put(
        f"/api/invoices/{member_one_invoice_id}/supporting-materials/{other_support_material_id}",
        headers=admin_auth_headers(client),
    ).status_code == 200

    split_response = client.put(
        f"/api/invoices/{member_one_invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 12000, "note": "self paid"},
                {"member_id": "2250002", "amount_cents": 8000, "note": "shared"},
            ],
        },
    )
    assert split_response.status_code == 200
    split_ids = {item["member_id"]: item["id"] for item in split_response.json()["items"]}
    for member_id, split_id in split_ids.items():
        assert client.put(
            f"/api/splits/{split_id}/confirmation",
            json={
                "actor_id": member_id,
                "member_id": member_id,
                "status": "confirmed",
            },
        ).status_code == 200
    assert client.post(
        f"/api/tasks/{task_id}/invoice-submissions",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
        json={"invoice_ids": [member_one_invoice_id]},
    ).status_code == 200

    member_one_draft_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="member-one-draft.pdf",
    )
    create_invoice(
        client,
        member_one_draft_material_id,
        actor_id="2250001",
        invoice_number="DRAFT-001",
        amount_cents=9999,
        expense_type="railway",
    )

    member_two_invoice_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250002",
        material_type="invoice",
        filename="member-two-railway.pdf",
    )
    create_invoice(
        client,
        member_two_invoice_material_id,
        actor_id="2250002",
        invoice_number="RAIL-001",
        amount_cents=12345,
        expense_type="railway",
    )

    return task_id


def test_task_member_can_view_shared_invoice_summary_without_sensitive_attachment_fields(tmp_path):
    client = make_client(tmp_path)
    task_id = create_shared_invoice_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/shared-invoices",
        headers=member_auth_headers(client, username="member2", actor_id="2250002"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["actor_id"] == "2250002"

    items_by_invoice_number = {item["invoice_number"]: item for item in body["items"]}
    assert set(items_by_invoice_number) == {"REG-001", "RAIL-001"}

    shared_invoice = items_by_invoice_number["REG-001"]
    assert shared_invoice["original_filename"] == "member-one-registration.pdf"
    assert shared_invoice["submitter_id"] == "2250001"
    assert shared_invoice["validation_status"] == "passed"
    assert shared_invoice["buyer_name"] == "同济大学"
    assert shared_invoice["amount_cents"] == 20000
    assert shared_invoice["splits"] == [
        {"member_id": "2250001", "amount_cents": 12000},
        {"member_id": "2250002", "amount_cents": 8000},
    ]
    assert shared_invoice["supporting_materials"] == [
        {"material_type": "order_screenshot", "count": 1},
        {"material_type": "payment_record", "count": 1},
    ]
    assert "tax_number" not in shared_invoice
    assert "transaction_time" not in shared_invoice
    assert all("original_filename" not in item for item in shared_invoice["supporting_materials"])
    assert all("note" not in item for item in shared_invoice["splits"])


def test_task_administrator_shared_invoice_summary_only_includes_submitted_invoices(tmp_path):
    client = make_client(tmp_path)
    task_id = create_shared_invoice_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/shared-invoices",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert [item["invoice_number"] for item in response.json()["items"]] == ["REG-001"]


def test_non_member_cannot_view_task_shared_invoice_summary(tmp_path):
    client = make_client(tmp_path)
    task_id = create_shared_invoice_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/shared-invoices",
        headers=member_auth_headers(client, username="outsider", actor_id="2250999"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to view shared invoices for this task"


def test_anonymous_request_cannot_self_report_shared_invoice_actor_id(tmp_path):
    client = make_client(tmp_path)
    task_id = create_shared_invoice_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/shared-invoices",
        params={"actor_id": "2250001"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid or missing bearer token"
