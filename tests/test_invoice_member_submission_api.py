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
        payload=valid_task_payload() | {"fee_categories": ["railway", "hotel"]},
    )
    response = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    assert response.status_code == 200
    return task["id"]


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
        files={"files": (filename, b"fake-pdf-content", "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["items"][0]["id"]


def create_invoice(
    client: TestClient,
    material_id: str,
    *,
    actor_id: str,
    invoice_number: str,
    expense_type: str,
    amount_cents: int = 12345,
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


def replace_invoice_splits(client: TestClient, invoice_id: str, *, actor_id: str, member_id: str) -> str:
    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": actor_id,
            "items": [{"member_id": member_id, "amount_cents": 12345, "note": "self paid"}],
        },
    )
    assert response.status_code == 200
    return response.json()["items"][0]["id"]


def confirm_split(client: TestClient, split_id: str, *, actor_id: str, member_id: str) -> None:
    response = client.put(
        f"/api/splits/{split_id}/confirmation",
        json={
            "actor_id": actor_id,
            "member_id": member_id,
            "status": "confirmed",
        },
    )
    assert response.status_code == 200


def test_member_can_batch_submit_ready_invoices(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    first_material_id = upload_invoice_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="first.pdf",
    )
    second_material_id = upload_invoice_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="second.pdf",
    )
    first_invoice_id = create_invoice(
        client,
        first_material_id,
        actor_id="2250001",
        invoice_number="INV-001",
        expense_type="railway",
    )
    second_invoice_id = create_invoice(
        client,
        second_material_id,
        actor_id="2250001",
        invoice_number="INV-002",
        expense_type="hotel",
    )
    first_split_id = replace_invoice_splits(
        client,
        first_invoice_id,
        actor_id="2250001",
        member_id="2250001",
    )
    second_split_id = replace_invoice_splits(
        client,
        second_invoice_id,
        actor_id="2250001",
        member_id="2250001",
    )
    confirm_split(client, first_split_id, actor_id="2250001", member_id="2250001")
    confirm_split(client, second_split_id, actor_id="2250001", member_id="2250001")

    response = client.post(
        f"/api/tasks/{task_id}/invoice-submissions",
        json={"invoice_ids": [first_invoice_id, second_invoice_id]},
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert [item["id"] for item in body["items"]] == [first_invoice_id, second_invoice_id]
    assert body["failures"] == []
    assert all(item["member_submission_status"] == "submitted" for item in body["items"])
    assert all(item["submitted_by_member_id"] == "2250001" for item in body["items"])
    assert all(item["submitted_at"] is not None for item in body["items"])


def test_batch_submit_reports_partial_success_when_some_invoices_are_not_ready(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    ready_material_id = upload_invoice_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="ready.pdf",
    )
    blocked_material_id = upload_invoice_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="blocked.pdf",
    )
    ready_invoice_id = create_invoice(
        client,
        ready_material_id,
        actor_id="2250001",
        invoice_number="INV-READY",
        expense_type="railway",
    )
    blocked_invoice_id = create_invoice(
        client,
        blocked_material_id,
        actor_id="2250001",
        invoice_number="INV-BLOCKED",
        expense_type="railway",
        amount_cents=150000,
    )
    ready_split_id = replace_invoice_splits(
        client,
        ready_invoice_id,
        actor_id="2250001",
        member_id="2250001",
    )
    confirm_split(client, ready_split_id, actor_id="2250001", member_id="2250001")

    response = client.post(
        f"/api/tasks/{task_id}/invoice-submissions",
        json={"invoice_ids": [ready_invoice_id, blocked_invoice_id]},
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial_success"
    assert [item["id"] for item in body["items"]] == [ready_invoice_id]
    assert body["items"][0]["member_submission_status"] == "submitted"
    assert body["failures"] == [
        {
            "invoice_id": blocked_invoice_id,
            "error_code": "invoice_not_ready_for_submission",
            "detail": f"blocker validations are not resolved for invoices: {blocked_invoice_id}",
        }
    ]


def test_invoice_creation_defaults_full_amount_to_submitter_and_locks_after_submission(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    material_id = upload_invoice_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="self.pdf",
    )
    invoice_id = create_invoice(
        client,
        material_id,
        actor_id="2250001",
        invoice_number="INV-SELF",
        expense_type="railway",
    )

    splits_response = client.get(
        f"/api/invoices/{invoice_id}/splits",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )
    assert splits_response.status_code == 200
    split = splits_response.json()["items"][0]
    assert split["member_id"] == "2250001"
    assert split["amount_cents"] == 12345

    confirmations_response = client.get(
        f"/api/invoices/{invoice_id}/confirmations",
        headers=member_auth_headers(client, username="member1b", actor_id="2250001"),
    )
    assert confirmations_response.status_code == 200
    assert confirmations_response.json()["items"][0]["status"] == "confirmed"

    submit_response = client.post(
        f"/api/tasks/{task_id}/invoice-submissions",
        json={"invoice_ids": [invoice_id]},
        headers=member_auth_headers(client, username="member1c", actor_id="2250001"),
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "success"

    update_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [{"member_id": "2250001", "amount_cents": 12345, "note": "late change"}],
        },
        headers=member_auth_headers(client, username="member1d", actor_id="2250001"),
    )
    assert update_response.status_code == 409
    assert update_response.json()["detail"] == "submitted invoice splits cannot be modified by members"


def test_outsider_member_cannot_submit_task_invoices(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    material_id = upload_invoice_material(
        client,
        task_id,
        submitter_id="2250001",
        filename="only.pdf",
    )
    invoice_id = create_invoice(
        client,
        material_id,
        actor_id="2250001",
        invoice_number="INV-001",
        expense_type="railway",
    )

    response = client.post(
        f"/api/tasks/{task_id}/invoice-submissions",
        json={"invoice_ids": [invoice_id]},
        headers=member_auth_headers(client, username="outsider", actor_id="2250999"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to submit invoices for this task"


def test_member_can_submit_paper_invoice_before_admin_confirms_receipt_but_task_cannot_enter_ready_to_export(
    tmp_path,
):
    client = make_client(tmp_path)
    task = create_task(
        client,
        payload=valid_task_payload() | {"fee_categories": ["registration", "railway", "hotel"]},
    )
    open_response = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    assert open_response.status_code == 200
    task_id = task["id"]
    member_headers = member_auth_headers(client, username="paper-submit-member", actor_id="2250001")

    create_response = client.post(
        f"/api/tasks/{task_id}/paper-invoices",
        json={
            "expense_type": "railway",
            "amount_cents": 8800,
        },
        headers=member_headers,
    )
    assert create_response.status_code == 201
    invoice_id = create_response.json()["invoice"]["id"]

    split_response = client.get(
        f"/api/invoices/{invoice_id}/splits",
        headers=member_headers,
    )
    assert split_response.status_code == 200
    split_id = split_response.json()["items"][0]["id"]
    confirm_split(client, split_id, actor_id="2250001", member_id="2250001")

    submit_response = client.post(
        f"/api/tasks/{task_id}/invoice-submissions",
        json={"invoice_ids": [invoice_id]},
        headers=member_headers,
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "success"
    assert submit_response.json()["items"][0]["member_submission_status"] == "submitted"

    closed_response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": "closed"},
        headers=admin_auth_headers(client),
    )
    assert closed_response.status_code == 200
    reviewing_response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": "reviewing"},
        headers=admin_auth_headers(client),
    )
    assert reviewing_response.status_code == 200
    ready_response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": "ready_to_export"},
        headers=admin_auth_headers(client),
    )
    assert ready_response.status_code == 409
    assert "blocker validations are not resolved" in ready_response.json()["detail"]
