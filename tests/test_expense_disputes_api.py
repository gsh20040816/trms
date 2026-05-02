from fastapi.testclient import TestClient

from trms_backend.domain.audit_logs import AuditLogResult
from trms_backend.infrastructure.database import build_session_factory
from trms_backend.infrastructure.repositories import SqlAlchemyAuditLogRepository
from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from test_invoices_api import valid_invoice_payload
from test_tasks_api import (
    admin_auth_headers,
    auth_headers,
    create_task as create_admin_task,
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


def list_split_audit_logs(tmp_path, split_id: str):
    repository = SqlAlchemyAuditLogRepository(
        build_session_factory(f"sqlite:///{tmp_path}/test.db")
    )
    return repository.list_by_object(object_type="expense_split", object_id=split_id)


def create_task(client: TestClient) -> str:
    task_id = create_admin_task(client)["id"]
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


def create_disputed_split_fixture(client: TestClient) -> tuple[str, str, str]:
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

    return task_id, invoice_id, split_ids["2250002"]


def move_task_to_reviewing(client: TestClient, task_id: str) -> None:
    for target_status in ("closed", "reviewing"):
        response = client.patch(
            f"/api/tasks/{task_id}/status",
            json={"target_status": target_status},
            headers=admin_auth_headers(client),
        )
        assert response.status_code == 200


def test_task_administrator_can_list_expense_disputes(tmp_path):
    client = make_client(tmp_path)
    task_id, invoice_id, split_id = create_disputed_split_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/expense-disputes",
        params={"actor_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["administrator_id"] == "admin-1"
    assert body["total_count"] == 1
    item = body["items"][0]
    assert item["split_id"] == split_id
    assert item["member_id"] == "2250002"
    assert item["amount_cents"] == 6345
    assert item["note"] == "team shared"
    assert item["dispute_reason"] == "shared amount should be lower"
    assert item["disputed_at"]
    assert item["updated_at"]
    assert item["invoice"]["id"] == invoice_id
    assert item["invoice"]["invoice_number"] == "INV-001"
    assert item["invoice"]["expense_type"] == "railway"


def test_non_administrator_cannot_list_expense_disputes(tmp_path):
    client = make_client(tmp_path)
    task_id, _, _ = create_disputed_split_fixture(client)
    member_token = register_and_get_token(
        client,
        username="member2",
        role="member",
        actor_id="2250002",
        member_code="2250002",
    )

    response = client.get(
        f"/api/tasks/{task_id}/expense-disputes",
        params={"actor_id": "2250002"},
        headers=auth_headers(member_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "actor is not allowed to view or resolve expense disputes for this task"
    )


def test_secondary_task_administrator_can_list_and_resolve_expense_disputes(tmp_path):
    client = make_client(tmp_path)
    secondary_admin_token = register_and_get_token(
        client,
        username="admin2",
        role="admin",
        actor_id="admin-2",
        member_code=None,
    )
    task_id = create_admin_task(
        client,
        payload={
            **valid_task_payload(),
            "administrator_ids": ["admin-1", "admin-2"],
        },
    )["id"]
    response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    assert response.status_code == 200
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
    split_id = {item["member_id"]: item["id"] for item in response.json()["items"]}["2250002"]
    response = client.put(
        f"/api/splits/{split_id}/confirmation",
        json={
            "actor_id": "2250002",
            "member_id": "2250002",
            "status": "disputed",
            "dispute_reason": "shared amount should be lower",
        },
    )
    assert response.status_code == 200
    move_task_to_reviewing(client, task_id)

    list_response = client.get(
        f"/api/tasks/{task_id}/expense-disputes",
        params={"actor_id": "admin-2"},
        headers=auth_headers(secondary_admin_token),
    )
    assert list_response.status_code == 200
    assert list_response.json()["administrator_id"] == "admin-2"

    resolve_response = client.post(
        f"/api/tasks/{task_id}/expense-disputes/{split_id}/resolve",
        json={"administrator_id": "admin-2"},
        headers=auth_headers(secondary_admin_token),
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "pending"


def test_resolving_dispute_returns_split_to_pending_and_blocks_ready_to_export(tmp_path):
    client = make_client(tmp_path)
    task_id, _, split_id = create_disputed_split_fixture(client)
    move_task_to_reviewing(client, task_id)
    member_token = register_and_get_token(
        client,
        username="member2",
        role="member",
        actor_id="2250002",
        member_code="2250002",
    )

    response = client.post(
        f"/api/tasks/{task_id}/expense-disputes/{split_id}/resolve",
        json={"administrator_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["dispute_reason"] == "shared amount should be lower"

    audit_logs = list_split_audit_logs(tmp_path, split_id)
    assert len(audit_logs) == 2
    assert audit_logs[1].actor_id == "admin-1"
    assert audit_logs[1].action == "resolve_split_dispute"
    assert audit_logs[1].result is AuditLogResult.SUCCEEDED
    assert audit_logs[1].request_id.startswith("req_")
    assert audit_logs[1].detail["status"] == "pending"
    assert audit_logs[1].detail["previous_status"] == "disputed"
    assert audit_logs[1].detail["dispute_reason"] == "shared amount should be lower"

    expense_detail_response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        headers=auth_headers(member_token),
    )
    assert expense_detail_response.status_code == 200
    assert expense_detail_response.json()["items"][0]["confirmation"]["status"] == "pending"

    ready_to_export_response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": "ready_to_export"},
        headers=admin_auth_headers(client),
    )

    assert ready_to_export_response.status_code == 409
    assert ready_to_export_response.json()["detail"] == (
        "task review is incomplete: "
        f"member confirmations are still pending for splits: {split_id}"
    )
