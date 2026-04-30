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


def member_auth_headers(client: TestClient, *, username: str, actor_id: str) -> dict[str, str]:
    return auth_headers(
        register_and_get_token(
            client,
            username=username,
            role="member",
            actor_id=actor_id,
            member_code=actor_id,
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


def create_split_fixture(client: TestClient, invoice_id: str) -> dict[str, str]:
    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 100000, "note": "self paid"},
                {"member_id": "2250002", "amount_cents": 50000, "note": "shared"},
            ],
        },
    )
    assert response.status_code == 200
    split_ids = {item["member_id"]: item["id"] for item in response.json()["items"]}
    response = client.put(
        f"/api/splits/{split_ids['2250002']}/confirmation",
        json={"actor_id": "2250002", "member_id": "2250002", "status": "confirmed"},
    )
    assert response.status_code == 200
    return split_ids


def create_member_status_fixture(client: TestClient) -> str:
    task_id = create_open_task(client)

    member_one_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="registration.pdf",
    )
    member_one_invoice_id = create_invoice(
        client,
        member_one_material_id,
        actor_id="2250001",
        invoice_number="REG-001",
        amount_cents=150000,
        expense_type="registration",
    )
    create_split_fixture(client, member_one_invoice_id)

    member_two_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250002",
        material_type="invoice",
        filename="railway.pdf",
    )
    create_invoice(
        client,
        member_two_material_id,
        actor_id="2250002",
        invoice_number="RAIL-001",
        amount_cents=12345,
        expense_type="railway",
    )

    return task_id


def test_member_status_returns_only_actor_related_materials_and_confirmations(tmp_path):
    client = make_client(tmp_path)
    task_id = create_member_status_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/member-status",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["actor_id"] == "2250001"
    assert body["total_expense_amount_cents"] == 100000
    assert body["counts"]["material_count"] == 1
    assert body["counts"]["recognition_needs_confirmation_count"] == 1
    assert body["counts"]["validation_failed_count"] == 1
    assert body["counts"]["missing_material_count"] == 2
    assert body["counts"]["expense_detail_count"] == 1
    assert body["counts"]["confirmed_expense_count"] == 1
    assert body["counts"]["missing_confirmation_count"] == 0
    assert [item["original_filename"] for item in body["materials"]] == ["registration.pdf"]
    assert body["materials"][0]["recognition_status"] == "needs_confirmation"
    assert body["materials"][0]["validation_status"] == "failed"
    assert "railway.pdf" not in {item["original_filename"] for item in body["materials"]}
    assert sorted(
        (item["invoice_number"], item["required_material_type"]) for item in body["missing_materials"]
    ) == [
        ("REG-001", "competition_notice"),
        ("REG-001", "payment_record"),
    ]
    assert len(body["expense_details"]) == 1
    expense_detail = body["expense_details"][0]
    assert expense_detail["split_version"] == 2
    assert expense_detail["member_id"] == "2250001"
    assert expense_detail["amount_cents"] == 100000
    assert expense_detail["note"] == "self paid"
    assert expense_detail["confirmation"]["status"] == "confirmed"
    assert expense_detail["invoice"]["invoice_number"] == "REG-001"
    assert expense_detail["invoice"]["amount_cents"] == 150000
    assert expense_detail["invoice"]["expense_type"] == "registration"


def test_anonymous_request_cannot_self_report_member_status_actor_id(tmp_path):
    client = make_client(tmp_path)
    task_id = create_member_status_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/member-status",
        params={"actor_id": "2250001"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid or missing bearer token"


def test_member_bearer_cannot_impersonate_other_member_for_member_status(tmp_path):
    client = make_client(tmp_path)
    task_id = create_member_status_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/member-status",
        params={"actor_id": "2250002"},
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "actor_id does not match the authenticated request identity: "
        "expected '2250001', got '2250002'"
    )


def test_non_member_cannot_view_task_member_status(tmp_path):
    client = make_client(tmp_path)
    task_id = create_member_status_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/member-status",
        headers=member_auth_headers(client, username="outsider", actor_id="2250999"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to view member status for this task"
