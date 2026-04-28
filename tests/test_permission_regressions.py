from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from api_error_assertions import assert_api_error
from test_tasks_api import (
    admin_auth_headers,
    auth_headers,
    create_task as create_admin_task,
    register_and_get_token,
    update_task_row,
    valid_invoice_payload,
)


def make_client(tmp_path):
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def member_auth_headers(
    client: TestClient,
    *,
    username: str,
    actor_id: str,
) -> dict[str, str]:
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
    task_id = create_admin_task(client)["id"]
    response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    assert response.status_code == 200
    return task_id


def create_permission_fixture(tmp_path) -> tuple[TestClient, str, str, str, str]:
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    material_response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("invoice.pdf", b"fake-pdf-content", "application/pdf")},
    )
    assert material_response.status_code == 201
    material_id = material_response.json()["items"][0]["id"]

    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload(),
    )
    assert invoice_response.status_code == 201
    invoice_id = invoice_response.json()["invoice"]["id"]

    split_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 6000, "note": "self paid"},
                {"member_id": "2250002", "amount_cents": 6345, "note": "team shared"},
            ],
        },
    )
    assert split_response.status_code == 200

    update_task_row(tmp_path, task_id, status="ready_to_export")
    export_response = client.post(
        f"/api/tasks/{task_id}/exports",
        headers=admin_auth_headers(client),
        json={
            "kind": "reimbursement_summary",
            "format": "csv",
            "parameters": {},
        },
    )
    assert export_response.status_code == 201
    export_job_id = export_response.json()["id"]

    return client, task_id, material_id, invoice_id, export_job_id


def test_task_member_cannot_view_other_members_material_content(tmp_path):
    client, _, material_id, _, _ = create_permission_fixture(tmp_path)

    response = client.get(
        f"/api/materials/{material_id}/content",
        headers=member_auth_headers(client, username="member2", actor_id="2250002"),
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to view this material content",
    )


def test_outsider_member_cannot_view_unrelated_expense_details(tmp_path):
    client, task_id, _, _, _ = create_permission_fixture(tmp_path)

    response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        headers=member_auth_headers(client, username="outsider", actor_id="outsider-1"),
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to view expense details for this task",
    )


def test_outsider_member_cannot_view_unrelated_invoice_confirmations(tmp_path):
    client, _, _, invoice_id, _ = create_permission_fixture(tmp_path)

    response = client.get(
        f"/api/invoices/{invoice_id}/confirmations",
        headers=member_auth_headers(client, username="outsider", actor_id="outsider-1"),
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to view confirmations for this task",
    )


def test_task_member_cannot_download_task_export_artifact(tmp_path):
    client, _, _, _, export_job_id = create_permission_fixture(tmp_path)

    response = client.get(
        f"/api/tasks/exports/{export_job_id}/artifact",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to manage exports for this task",
    )


def test_task_member_cannot_enter_review_summary_path(tmp_path):
    client, task_id, _, _, _ = create_permission_fixture(tmp_path)

    response = client.get(
        f"/api/tasks/{task_id}/review-summary",
        params={"actor_id": "2250001"},
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to view review summary for this task",
    )
