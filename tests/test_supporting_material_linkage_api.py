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
    task = create_task(
        client,
        payload=valid_task_payload()
        | {"member_ids": ["2250001", "2250002", "2250003"]},
    )
    response = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    assert response.status_code == 200
    return task["id"]


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


def test_admin_can_list_pending_supporting_material_linkage_items(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    member_one_invoice_material = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="member-one-invoice.pdf",
    )
    create_invoice(
        client,
        member_one_invoice_material,
        actor_id="2250001",
        invoice_number="M1-001",
        amount_cents=10000,
        expense_type="railway",
    )
    member_one_auto_linked_supporting = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="payment_record",
        filename="member-one-payment.png",
        content_type="image/png",
    )

    member_two_first_invoice_material = upload_material(
        client,
        task_id,
        submitter_id="2250002",
        material_type="invoice",
        filename="member-two-first.pdf",
    )
    member_two_second_invoice_material = upload_material(
        client,
        task_id,
        submitter_id="2250002",
        material_type="invoice",
        filename="member-two-second.pdf",
    )
    member_two_first_invoice_id = create_invoice(
        client,
        member_two_first_invoice_material,
        actor_id="2250002",
        invoice_number="M2-001",
        amount_cents=20000,
        expense_type="railway",
    )
    member_two_second_invoice_id = create_invoice(
        client,
        member_two_second_invoice_material,
        actor_id="2250002",
        invoice_number="M2-002",
        amount_cents=30000,
        expense_type="hotel",
    )
    member_two_pending_supporting = upload_material(
        client,
        task_id,
        submitter_id="2250002",
        material_type="payment_record",
        filename="member-two-payment.png",
        content_type="image/png",
    )

    member_three_pending_supporting = upload_material(
        client,
        task_id,
        submitter_id="2250003",
        material_type="competition_notice",
        filename="member-three-notice.pdf",
    )

    response = client.get(
        f"/api/tasks/{task_id}/supporting-material-linkage",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["actor_id"] == "admin-1"
    items_by_id = {item["material_id"]: item for item in body["items"]}
    assert member_one_auto_linked_supporting not in items_by_id
    assert items_by_id[member_three_pending_supporting] == {
        "material_id": member_three_pending_supporting,
        "submitter_id": "2250003",
        "material_type": "competition_notice",
        "original_filename": "member-three-notice.pdf",
        "pending_reason": "no_candidate",
        "candidate_invoices": [],
        "created_at": items_by_id[member_three_pending_supporting]["created_at"],
    }
    assert items_by_id[member_two_pending_supporting]["pending_reason"] == "multiple_candidates"
    assert items_by_id[member_two_pending_supporting]["submitter_id"] == "2250002"
    assert items_by_id[member_two_pending_supporting]["candidate_invoices"] == [
        {
            "invoice_id": member_two_first_invoice_id,
            "invoice_number": "M2-001",
            "amount_cents": 20000,
            "expense_type": "railway",
        },
        {
            "invoice_id": member_two_second_invoice_id,
            "invoice_number": "M2-002",
            "amount_cents": 30000,
            "expense_type": "hotel",
        },
    ]


def test_member_only_sees_own_pending_supporting_material_linkage_items(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    member_one_invoice_material = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="member-one-invoice.pdf",
    )
    create_invoice(
        client,
        member_one_invoice_material,
        actor_id="2250001",
        invoice_number="M1-001",
        amount_cents=10000,
        expense_type="railway",
    )
    upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="payment_record",
        filename="member-one-payment.png",
        content_type="image/png",
    )

    member_two_pending_supporting = upload_material(
        client,
        task_id,
        submitter_id="2250002",
        material_type="competition_notice",
        filename="member-two-notice.pdf",
    )

    member_one_response = client.get(
        f"/api/tasks/{task_id}/supporting-material-linkage",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )
    assert member_one_response.status_code == 200
    assert member_one_response.json()["items"] == []

    member_two_response = client.get(
        f"/api/tasks/{task_id}/supporting-material-linkage",
        headers=member_auth_headers(client, username="member2", actor_id="2250002"),
    )
    assert member_two_response.status_code == 200
    assert [item["material_id"] for item in member_two_response.json()["items"]] == [
        member_two_pending_supporting
    ]
    assert member_two_response.json()["items"][0]["pending_reason"] == "no_candidate"


def test_outsider_cannot_view_task_supporting_material_linkage(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.get(
        f"/api/tasks/{task_id}/supporting-material-linkage",
        headers=member_auth_headers(client, username="outsider", actor_id="2250999"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "actor is not allowed to view supporting material linkage for this task"
    )
