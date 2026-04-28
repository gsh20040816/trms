from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_tasks_api import (
    create_task as create_admin_task,
    update_task_row,
    valid_invoice_payload,
    valid_task_payload,
)


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
    if response.status_code == 201:
        return response.json()["access_token"]

    assert response.status_code == 409
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": "correct-password",
        },
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def create_task(client: TestClient) -> str:
    return create_admin_task(client)["id"]


def open_task(client: TestClient, task_id: str) -> None:
    admin_token = register_and_get_token(
        client,
        username="taskadmin",
        role="admin",
        actor_id="admin-1",
        member_code=None,
    )
    response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": "open"},
        headers=auth_headers(admin_token),
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


def test_member_bearer_task_queries_filter_visible_tasks_and_reject_mismatched_ids(tmp_path):
    client = make_client(tmp_path)
    member_token = register_and_get_token(
        client,
        username="member1",
        role="member",
        actor_id="2250001",
        member_code="2250001",
    )
    visible_task_id = create_task(client)
    hidden_task_id = create_admin_task(
        client,
        payload=valid_task_payload() | {"member_ids": ["2250002", "2250003"]},
    )["id"]

    list_response = client.get(
        "/api/tasks",
        headers=auth_headers(member_token),
    )

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [visible_task_id]

    mismatch_response = client.get(
        "/api/tasks",
        headers=auth_headers(member_token),
        params={"member_id": "2250002"},
    )

    assert mismatch_response.status_code == 403
    assert mismatch_response.json()["detail"] == (
        "member_id does not match the authenticated request identity: "
        "expected '2250001', got '2250002'"
    )
    assert hidden_task_id != visible_task_id


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


def test_admin_bearer_task_management_routes_bind_to_owned_tasks(tmp_path):
    client = make_client(tmp_path)
    admin_token = register_and_get_token(
        client,
        username="admin1",
        role="admin",
        actor_id="admin-1",
        member_code=None,
    )
    outsider_admin_token = register_and_get_token(
        client,
        username="admin2",
        role="admin",
        actor_id="admin-2",
        member_code=None,
    )
    task_id = create_task(client)

    own_list_response = client.get(
        "/api/tasks",
        headers=auth_headers(admin_token),
    )
    assert own_list_response.status_code == 200
    assert [item["id"] for item in own_list_response.json()] == [task_id]

    outsider_list_response = client.get(
        "/api/tasks",
        headers=auth_headers(outsider_admin_token),
    )
    assert outsider_list_response.status_code == 200
    assert outsider_list_response.json() == []

    own_task_response = client.get(
        f"/api/tasks/{task_id}",
        headers=auth_headers(admin_token),
    )
    assert own_task_response.status_code == 200
    assert own_task_response.json()["id"] == task_id

    outsider_task_response = client.get(
        f"/api/tasks/{task_id}",
        headers=auth_headers(outsider_admin_token),
    )
    assert outsider_task_response.status_code == 403
    assert outsider_task_response.json()["detail"] == "actor is not allowed to view this task"

    own_members_response = client.get(
        f"/api/tasks/{task_id}/members",
        headers=auth_headers(admin_token),
    )
    assert own_members_response.status_code == 200
    assert own_members_response.json()["items"] == ["2250001", "2250002", "2250003"]

    outsider_members_response = client.get(
        f"/api/tasks/{task_id}/members",
        headers=auth_headers(outsider_admin_token),
    )
    assert outsider_members_response.status_code == 403
    assert outsider_members_response.json()["detail"] == (
        "actor is not allowed to view task members for this task"
    )

    update_members_response = client.put(
        f"/api/tasks/{task_id}/members",
        headers=auth_headers(admin_token),
        json={"member_ids": ["2250001", "2250002"]},
    )
    assert update_members_response.status_code == 200
    assert update_members_response.json()["items"] == ["2250001", "2250002"]

    outsider_update_members_response = client.put(
        f"/api/tasks/{task_id}/members",
        headers=auth_headers(outsider_admin_token),
        json={"member_ids": ["2250001"]},
    )
    assert outsider_update_members_response.status_code == 403
    assert outsider_update_members_response.json()["detail"] == (
        "actor is not allowed to manage task members for this task"
    )

    anonymous_update_members_response = client.put(
        f"/api/tasks/{task_id}/members",
        json={"member_ids": ["2250001"]},
    )
    assert anonymous_update_members_response.status_code == 401
    assert anonymous_update_members_response.json()["detail"] == "invalid or missing bearer token"

    own_status_response = client.patch(
        f"/api/tasks/{task_id}/status",
        headers=auth_headers(admin_token),
        json={"target_status": "open"},
    )
    assert own_status_response.status_code == 200
    assert own_status_response.json()["status"] == "open"

    outsider_status_response = client.patch(
        f"/api/tasks/{task_id}/status",
        headers=auth_headers(outsider_admin_token),
        json={"target_status": "closed"},
    )
    assert outsider_status_response.status_code == 403
    assert outsider_status_response.json()["detail"] == (
        "actor is not allowed to manage task status for this task"
    )

    anonymous_status_response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": "closed"},
    )
    assert anonymous_status_response.status_code == 401
    assert anonymous_status_response.json()["detail"] == "invalid or missing bearer token"


def test_admin_bearer_review_routes_reject_anonymous_or_unrelated_admin(tmp_path):
    client = make_client(tmp_path)
    register_and_get_token(
        client,
        username="admin1",
        role="admin",
        actor_id="admin-1",
        member_code=None,
    )
    outsider_admin_token = register_and_get_token(
        client,
        username="admin2",
        role="admin",
        actor_id="admin-2",
        member_code=None,
    )
    task_id = create_task(client)

    outsider_summary_response = client.get(
        f"/api/tasks/{task_id}/review-summary",
        headers=auth_headers(outsider_admin_token),
    )
    assert outsider_summary_response.status_code == 403
    assert outsider_summary_response.json()["detail"] == (
        "actor is not allowed to view review summary for this task"
    )

    anonymous_summary_response = client.get(f"/api/tasks/{task_id}/review-summary")
    assert anonymous_summary_response.status_code == 401
    assert anonymous_summary_response.json()["detail"] == "invalid or missing bearer token"

    anonymous_reminder_response = client.post(
        f"/api/tasks/{task_id}/material-reminders",
        json={
            "administrator_id": "admin-1",
            "member_id": "2250002",
            "content": "请补交支付记录",
        },
    )
    assert anonymous_reminder_response.status_code == 401
    assert anonymous_reminder_response.json()["detail"] == "invalid or missing bearer token"

    outsider_reminder_response = client.post(
        f"/api/tasks/{task_id}/material-reminders",
        headers=auth_headers(outsider_admin_token),
        json={
            "administrator_id": "admin-2",
            "member_id": "2250002",
            "content": "请补交支付记录",
        },
    )
    assert outsider_reminder_response.status_code == 403
    assert outsider_reminder_response.json()["detail"] == (
        "actor is not allowed to manage material reminders for this task"
    )


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


def test_member_bearer_material_queries_only_expose_own_records(tmp_path):
    client = make_client(tmp_path)
    admin_token = register_and_get_token(
        client,
        username="admin1",
        role="admin",
        actor_id="admin-1",
        member_code=None,
    )
    member_one_token = register_and_get_token(
        client,
        username="member1",
        role="member",
        actor_id="2250001",
        member_code="2250001",
    )
    member_two_token = register_and_get_token(
        client,
        username="member2",
        role="member",
        actor_id="2250002",
        member_code="2250002",
    )
    task_id = create_task(client)
    open_task(client, task_id)

    member_one_upload = client.post(
        f"/api/tasks/{task_id}/materials",
        headers=auth_headers(member_one_token),
        data={"channel": "web", "material_type": "invoice"},
        files={"files": ("member-one.pdf", b"fake-pdf-content", "application/pdf")},
    )
    assert member_one_upload.status_code == 201
    member_one_material_id = member_one_upload.json()["items"][0]["id"]

    member_two_upload = client.post(
        f"/api/tasks/{task_id}/materials",
        headers=auth_headers(member_two_token),
        data={"channel": "web", "material_type": "invoice"},
        files={"files": ("member-two.pdf", b"fake-pdf-content", "application/pdf")},
    )
    assert member_two_upload.status_code == 201
    member_two_material_id = member_two_upload.json()["items"][0]["id"]

    mismatch_upload = client.post(
        f"/api/tasks/{task_id}/materials",
        headers=auth_headers(member_one_token),
        data={
            "submitter_id": "2250002",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("mismatch.pdf", b"fake-pdf-content", "application/pdf")},
    )
    assert mismatch_upload.status_code == 403
    assert mismatch_upload.json()["detail"] == (
        "submitter_id does not match the authenticated request identity: "
        "expected '2250001', got '2250002'"
    )

    member_one_invoice_response = client.post(
        f"/api/materials/{member_one_material_id}/invoice",
        headers=auth_headers(admin_token),
        json={key: value for key, value in valid_invoice_payload().items() if key != "actor_id"},
    )
    assert member_one_invoice_response.status_code == 201
    member_one_invoice_id = member_one_invoice_response.json()["invoice"]["id"]

    member_two_invoice_response = client.post(
        f"/api/materials/{member_two_material_id}/invoice",
        headers=auth_headers(admin_token),
        json={
            **{key: value for key, value in valid_invoice_payload().items() if key != "actor_id"},
            "invoice_number": "INV-002",
        },
    )
    assert member_two_invoice_response.status_code == 201
    member_two_invoice_id = member_two_invoice_response.json()["invoice"]["id"]

    materials_response = client.get(
        f"/api/tasks/{task_id}/materials",
        headers=auth_headers(member_one_token),
    )
    assert materials_response.status_code == 200
    assert [item["id"] for item in materials_response.json()["items"]] == [member_one_material_id]

    invoices_response = client.get(
        f"/api/tasks/{task_id}/invoices",
        headers=auth_headers(member_one_token),
    )
    assert invoices_response.status_code == 200
    assert [item["id"] for item in invoices_response.json()["items"]] == [member_one_invoice_id]

    member_status_response = client.get(
        f"/api/tasks/{task_id}/member-status",
        headers=auth_headers(member_one_token),
    )
    assert member_status_response.status_code == 200
    assert member_status_response.json()["actor_id"] == "2250001"
    assert [item["material_id"] for item in member_status_response.json()["materials"]] == [
        member_one_material_id
    ]

    mismatch_member_status = client.get(
        f"/api/tasks/{task_id}/member-status",
        headers=auth_headers(member_one_token),
        params={"actor_id": "2250002"},
    )
    assert mismatch_member_status.status_code == 403
    assert mismatch_member_status.json()["detail"] == (
        "actor_id does not match the authenticated request identity: "
        "expected '2250001', got '2250002'"
    )

    own_recognition_response = client.get(
        f"/api/materials/{member_one_material_id}/recognition-tasks",
        headers=auth_headers(member_one_token),
    )
    assert own_recognition_response.status_code == 200

    other_recognition_response = client.get(
        f"/api/materials/{member_two_material_id}/recognition-tasks",
        headers=auth_headers(member_one_token),
    )
    assert other_recognition_response.status_code == 403
    assert other_recognition_response.json()["detail"] == (
        "actor is not allowed to view recognition tasks for this material"
    )

    other_validation_response = client.get(
        f"/api/invoices/{member_two_invoice_id}/validations",
        headers=auth_headers(member_one_token),
    )
    assert other_validation_response.status_code == 403
    assert other_validation_response.json()["detail"] == (
        "actor is not allowed to view invoice validations for this task"
    )


def test_member_bearer_fee_and_confirmation_queries_only_expose_own_records(tmp_path):
    client = make_client(tmp_path)
    admin_token = register_and_get_token(
        client,
        username="admin1",
        role="admin",
        actor_id="admin-1",
        member_code=None,
    )
    member_one_token = register_and_get_token(
        client,
        username="member1",
        role="member",
        actor_id="2250001",
        member_code="2250001",
    )
    member_two_token = register_and_get_token(
        client,
        username="member2",
        role="member",
        actor_id="2250002",
        member_code="2250002",
    )
    task_id = create_task(client)
    open_task(client, task_id)

    invoice_material_response = client.post(
        f"/api/tasks/{task_id}/materials",
        headers=auth_headers(member_one_token),
        data={"channel": "web", "material_type": "invoice"},
        files={"files": ("shared.pdf", b"fake-pdf-content", "application/pdf")},
    )
    assert invoice_material_response.status_code == 201
    invoice_material_id = invoice_material_response.json()["items"][0]["id"]

    own_support_response = client.post(
        f"/api/tasks/{task_id}/materials",
        headers=auth_headers(member_one_token),
        data={"channel": "web", "material_type": "payment_record"},
        files={"files": ("own-support.pdf", b"fake-pdf-content", "application/pdf")},
    )
    assert own_support_response.status_code == 201
    own_support_material_id = own_support_response.json()["items"][0]["id"]

    other_support_response = client.post(
        f"/api/tasks/{task_id}/materials",
        headers=auth_headers(member_two_token),
        data={"channel": "web", "material_type": "payment_record"},
        files={"files": ("other-support.pdf", b"fake-pdf-content", "application/pdf")},
    )
    assert other_support_response.status_code == 201
    other_support_material_id = other_support_response.json()["items"][0]["id"]

    invoice_response = client.post(
        f"/api/materials/{invoice_material_id}/invoice",
        headers=auth_headers(admin_token),
        json={
            **{key: value for key, value in valid_invoice_payload().items() if key != "actor_id"},
            "amount_cents": 20000,
        },
    )
    assert invoice_response.status_code == 201
    invoice_id = invoice_response.json()["invoice"]["id"]

    assert client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{own_support_material_id}"
    ).status_code == 200
    assert client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{other_support_material_id}"
    ).status_code == 200

    split_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        headers=auth_headers(admin_token),
        json={
            "items": [
                {"member_id": "2250001", "amount_cents": 12000},
                {"member_id": "2250002", "amount_cents": 8000},
            ]
        },
    )
    assert split_response.status_code == 200
    split_ids = {item["member_id"]: item["id"] for item in split_response.json()["items"]}

    assert client.put(
        f"/api/splits/{split_ids['2250001']}/confirmation",
        headers=auth_headers(member_one_token),
        json={"status": "confirmed"},
    ).status_code == 200
    assert client.put(
        f"/api/splits/{split_ids['2250002']}/confirmation",
        headers=auth_headers(member_two_token),
        json={"status": "confirmed"},
    ).status_code == 200

    splits_response = client.get(
        f"/api/invoices/{invoice_id}/splits",
        headers=auth_headers(member_one_token),
    )
    assert splits_response.status_code == 200
    assert [item["member_id"] for item in splits_response.json()["items"]] == [
        "2250001",
        "2250002",
    ]

    confirmations_response = client.get(
        f"/api/invoices/{invoice_id}/confirmations",
        headers=auth_headers(member_one_token),
    )
    assert confirmations_response.status_code == 200
    assert [item["member_id"] for item in confirmations_response.json()["items"]] == [
        "2250001",
        "2250002",
    ]

    member_two_splits_response = client.get(
        f"/api/invoices/{invoice_id}/splits",
        headers=auth_headers(member_two_token),
    )
    assert member_two_splits_response.status_code == 200
    assert [item["member_id"] for item in member_two_splits_response.json()["items"]] == [
        "2250002"
    ]

    member_two_confirmations_response = client.get(
        f"/api/invoices/{invoice_id}/confirmations",
        headers=auth_headers(member_two_token),
    )
    assert member_two_confirmations_response.status_code == 200
    assert [item["member_id"] for item in member_two_confirmations_response.json()["items"]] == [
        "2250002"
    ]

    supporting_materials_response = client.get(
        f"/api/invoices/{invoice_id}/supporting-materials",
        headers=auth_headers(member_one_token),
    )
    assert supporting_materials_response.status_code == 200
    assert [item["id"] for item in supporting_materials_response.json()["items"]] == [
        own_support_material_id
    ]

    mismatch_confirmation = client.put(
        f"/api/splits/{split_ids['2250001']}/confirmation",
        headers=auth_headers(member_one_token),
        json={"actor_id": "2250002", "member_id": "2250001", "status": "confirmed"},
    )
    assert mismatch_confirmation.status_code == 403
    assert mismatch_confirmation.json()["detail"] == (
        "actor_id does not match the authenticated request identity: "
        "expected '2250001', got '2250002'"
    )


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
