from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_tasks_api import update_task_row, valid_invoice_payload, valid_task_payload


def make_client(tmp_path) -> TestClient:
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def register_and_get_token(
    client: TestClient,
    *,
    username: str,
    role: str,
    actor_id: str,
    member_code: str | None,
) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "correct-password",
            "role": role,
            "display_name": username,
            "actor_id": actor_id,
            "member_code": member_code,
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def create_task(client: TestClient) -> str:
    response = client.post("/api/tasks", json=valid_task_payload())
    assert response.status_code == 201
    return response.json()["id"]


def open_task(client: TestClient, task_id: str) -> None:
    response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": "open"},
    )
    assert response.status_code == 200


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_member_bearer_upload_uses_authenticated_actor_id(tmp_path):
    client = make_client(tmp_path)
    member_token = register_and_get_token(
        client,
        username="member1",
        role="member",
        actor_id="2250001",
        member_code="2250001",
    )
    task_id = create_task(client)
    open_task(client, task_id)

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        headers=auth_headers(member_token),
        data={
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["items"][0]["submitter_id"] == "2250001"


def test_admin_bearer_review_summary_and_material_reminders_do_not_require_actor_fields(tmp_path):
    client = make_client(tmp_path)
    admin_token = register_and_get_token(
        client,
        username="admin1",
        role="admin",
        actor_id="admin-1",
        member_code=None,
    )
    task_id = create_task(client)

    summary_response = client.get(
        f"/api/tasks/{task_id}/review-summary",
        headers=auth_headers(admin_token),
    )

    assert summary_response.status_code == 200
    assert summary_response.json()["administrator_id"] == "admin-1"

    create_response = client.post(
        f"/api/tasks/{task_id}/material-reminders",
        headers=auth_headers(admin_token),
        json={
            "member_id": "2250002",
            "content": "请补交支付记录",
        },
    )

    assert create_response.status_code == 201
    assert create_response.json()["administrator_id"] == "admin-1"
    assert create_response.json()["member_id"] == "2250002"

    list_response = client.get(
        f"/api/tasks/{task_id}/material-reminders",
        headers=auth_headers(admin_token),
    )

    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1
    assert list_response.json()["items"][0]["administrator_id"] == "admin-1"


def test_bearer_invoice_split_confirmation_and_expense_details_use_authenticated_actor_id(tmp_path):
    client = make_client(tmp_path)
    admin_token = register_and_get_token(
        client,
        username="admin1",
        role="admin",
        actor_id="admin-1",
        member_code=None,
    )
    member_token = register_and_get_token(
        client,
        username="member1",
        role="member",
        actor_id="2250001",
        member_code="2250001",
    )
    task_id = create_task(client)
    open_task(client, task_id)

    upload_response = client.post(
        f"/api/tasks/{task_id}/materials",
        headers=auth_headers(member_token),
        data={
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )
    assert upload_response.status_code == 201
    material_id = upload_response.json()["items"][0]["id"]

    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        headers=auth_headers(admin_token),
        json={key: value for key, value in valid_invoice_payload().items() if key != "actor_id"},
    )
    assert invoice_response.status_code == 201
    invoice_id = invoice_response.json()["invoice"]["id"]

    split_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        headers=auth_headers(admin_token),
        json={
            "items": [{"member_id": "2250001", "amount_cents": 12345}],
        },
    )
    assert split_response.status_code == 200
    split_id = split_response.json()["items"][0]["id"]

    confirmation_response = client.put(
        f"/api/splits/{split_id}/confirmation",
        headers=auth_headers(member_token),
        json={"status": "confirmed"},
    )

    assert confirmation_response.status_code == 200
    assert confirmation_response.json()["member_id"] == "2250001"

    expense_details_response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        headers=auth_headers(member_token),
    )

    assert expense_details_response.status_code == 200
    assert expense_details_response.json()["actor_id"] == "2250001"
    assert len(expense_details_response.json()["items"]) == 1


def test_admin_bearer_export_routes_do_not_require_actor_id(tmp_path):
    client = make_client(tmp_path)
    admin_token = register_and_get_token(
        client,
        username="admin1",
        role="admin",
        actor_id="admin-1",
        member_code=None,
    )
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")

    capabilities_response = client.get(
        f"/api/tasks/{task_id}/exports/capabilities",
        headers=auth_headers(admin_token),
    )

    assert capabilities_response.status_code == 200
    assert capabilities_response.json()["administrator_id"] == "admin-1"

    create_response = client.post(
        f"/api/tasks/{task_id}/exports",
        headers=auth_headers(admin_token),
        json={
            "kind": "reimbursement_summary",
            "format": "csv",
            "parameters": {},
        },
    )

    assert create_response.status_code == 201
    assert create_response.json()["requested_by"] == "admin-1"

    list_response = client.get(
        f"/api/tasks/{task_id}/exports",
        headers=auth_headers(admin_token),
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["requested_by"] == "admin-1"
