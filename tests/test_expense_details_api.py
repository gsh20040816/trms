from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_invoices_api import valid_invoice_payload
from test_tasks_api import (
    admin_auth_headers,
    auth_headers,
    create_task as create_admin_task,
    register_and_get_token,
    valid_task_payload,
)


def make_client(tmp_path):
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
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


def create_task(client: TestClient, *, payload: dict | None = None) -> str:
    task_id = create_admin_task(client, payload=payload)["id"]
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


def mark_new_recognition_succeeded(client: TestClient, material_id: str) -> None:
    create_response = client.post(
        f"/api/materials/{material_id}/recognition-tasks",
        headers=admin_auth_headers(client),
    )
    assert create_response.status_code == 201
    recognition_task_id = create_response.json()["item"]["id"]
    update_response = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        headers=admin_auth_headers(client),
        json={
            "target_status": "succeeded",
            "result": {
                "raw_response": {"provider": "test-provider"},
                "recognized_fields": {
                    "buyer_name": {
                        "value": "同济大学",
                        "source": "manual",
                        "confidence": 1,
                        "status": "recognized",
                    },
                    "tax_number": {
                        "value": "12100000425006117D",
                        "source": "manual",
                        "confidence": 1,
                        "status": "recognized",
                    },
                },
            },
        },
    )
    assert update_response.status_code == 200


def create_split_fixture(
    client: TestClient,
    *,
    submitted: bool = True,
) -> tuple[str, str, dict[str, str]]:
    task_id = create_task(client)
    material_id = upload_invoice_material(client, task_id)
    mark_new_recognition_succeeded(client, material_id)
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
        json={"actor_id": "2250002", "member_id": "2250002", "status": "confirmed"},
    )
    assert response.status_code == 200
    response = client.put(
        f"/api/splits/{split_ids['2250001']}/confirmation",
        json={"actor_id": "2250001", "member_id": "2250001", "status": "confirmed"},
    )
    assert response.status_code == 200
    if submitted:
        response = client.post(
            f"/api/tasks/{task_id}/invoice-submissions",
            headers=member_auth_headers(client, username="member1", actor_id="2250001"),
            json={"invoice_ids": [invoice_id]},
        )
        assert response.status_code == 200

    return task_id, invoice_id, split_ids


def test_member_can_list_only_own_expense_details(tmp_path):
    client = make_client(tmp_path)
    task_id, invoice_id, _ = create_split_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        headers=member_auth_headers(client, username="member2", actor_id="2250002"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "member"
    assert body["actor_id"] == "2250002"
    assert body["total_amount_cents"] == 6345
    assert len(body["items"]) == 1
    assert body["items"][0]["member_id"] == "2250002"
    assert body["items"][0]["split_version"] == 1
    assert body["items"][0]["amount_cents"] == 6345
    assert body["items"][0]["invoice"]["id"] == invoice_id
    assert body["items"][0]["confirmation"]["status"] == "confirmed"
    assert body["items"][0]["confirmation"]["split_version"] == 1


def test_task_member_without_related_splits_gets_empty_expense_details(tmp_path):
    client = make_client(tmp_path)
    task_id, _, _ = create_split_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        headers=member_auth_headers(client, username="member3", actor_id="2250003"),
    )

    assert response.status_code == 200
    assert response.json() == {
        "actor_id": "2250003",
        "scope": "member",
        "total_amount_cents": 0,
        "items": [],
    }


def test_other_member_and_admin_do_not_see_unsubmitted_invoice_expense_details(tmp_path):
    client = make_client(tmp_path)
    task_id, _, _ = create_split_fixture(client, submitted=False)

    other_member_response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        headers=member_auth_headers(client, username="member2", actor_id="2250002"),
    )
    admin_response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        headers=admin_auth_headers(client),
    )
    submitter_response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert other_member_response.status_code == 200
    assert other_member_response.json()["total_amount_cents"] == 0
    assert other_member_response.json()["items"] == []
    assert admin_response.status_code == 200
    assert admin_response.json()["total_amount_cents"] == 0
    assert admin_response.json()["items"] == []
    assert submitter_response.status_code == 200
    assert submitter_response.json()["total_amount_cents"] == 6000


def test_member_role_still_sees_own_unsubmitted_expense_when_also_task_administrator(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(
        client,
        payload=valid_task_payload() | {"administrator_ids": ["admin-1", "2250001"]},
    )
    material_id = upload_invoice_material(client, task_id, submitter_id="2250001", filename="dual-role.pdf")
    mark_new_recognition_succeeded(client, material_id)
    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload(),
    )
    assert response.status_code == 201
    invoice_id = response.json()["invoice"]["id"]

    split_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 12345, "note": "self paid"},
            ],
        },
    )
    assert split_response.status_code == 200
    split_id = split_response.json()["items"][0]["id"]
    assert client.put(
        f"/api/splits/{split_id}/confirmation",
        json={"actor_id": "2250001", "member_id": "2250001", "status": "confirmed"},
    ).status_code == 200

    response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        headers=member_auth_headers(client, username="dualrole-member", actor_id="2250001"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "member"
    assert body["total_amount_cents"] == 12345
    assert len(body["items"]) == 1
    assert body["items"][0]["invoice"]["id"] == invoice_id
    assert body["items"][0]["amount_cents"] == 12345


def test_task_administrator_can_list_all_expense_details(tmp_path):
    client = make_client(tmp_path)
    task_id, invoice_id, split_ids = create_split_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "task"
    assert body["actor_id"] == "admin-1"
    assert body["total_amount_cents"] == 12345
    assert len(body["items"]) == 2
    items_by_split_id = {item["split_id"]: item for item in body["items"]}
    assert set(items_by_split_id) == set(split_ids.values())
    assert items_by_split_id[split_ids["2250001"]]["confirmation"]["status"] == "confirmed"
    assert items_by_split_id[split_ids["2250001"]]["invoice"]["id"] == invoice_id
    assert items_by_split_id[split_ids["2250002"]]["confirmation"]["status"] == "confirmed"


def test_anonymous_request_cannot_self_report_expense_details_actor_id(tmp_path):
    client = make_client(tmp_path)
    task_id, _, _ = create_split_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        params={"actor_id": "2250002"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid or missing bearer token"


def test_member_bearer_cannot_impersonate_other_member_for_expense_details(tmp_path):
    client = make_client(tmp_path)
    task_id, _, _ = create_split_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        params={"actor_id": "2250002"},
        headers=member_auth_headers(client, username="member1", actor_id="2250001"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "actor_id does not match the authenticated request identity: "
        "expected '2250001', got '2250002'"
    )


def test_non_member_cannot_list_task_expense_details(tmp_path):
    client = make_client(tmp_path)
    task_id, _, _ = create_split_fixture(client)

    response = client.get(
        f"/api/tasks/{task_id}/expense-details",
        headers=member_auth_headers(client, username="outsider", actor_id="outsider-1"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to view expense details for this task"
