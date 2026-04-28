from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_tasks_api import admin_auth_headers, create_task


def make_client(tmp_path):
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def create_open_task(client: TestClient) -> str:
    created = create_task(client)
    client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    return created["id"]


def assert_single_pending_recognition_task(client: TestClient, material_id: str) -> None:
    response = client.get(f"/api/materials/{material_id}/recognition-tasks")

    assert response.status_code == 200
    body = response.json()
    assert body["latest_effective"] is None
    assert len(body["items"]) == 1
    assert body["items"][0]["material_id"] == material_id
    assert body["items"][0]["status"] == "pending"


def test_telegram_material_submission_routes_bound_account_to_assigned_flow(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    bind_response = client.put(
        "/api/telegram-bindings/123456789",
        json={"member_id": "2250001", "telegram_username": "@TongjiCoder"},
    )
    assert bind_response.status_code == 200

    response = client.post(
        "/api/telegram/materials",
        data={
            "telegram_user_id": "123456789",
            "telegram_username": "@TongjiCoder",
            "task_id": task_id,
            "material_type": "invoice",
        },
        files={"files": ("invoice.pdf", b"telegram-pdf", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["submission_identity"] == {
        "telegram_user_id": 123456789,
        "status": "bound",
        "member_id": "2250001",
    }
    material = body["items"][0]
    assert material["status"] == "assigned"
    assert material["task_id"] == task_id
    assert material["submitter_id"] == "2250001"
    assert material["task_id_hint"] is None
    assert material["submitter_id_hint"] is None
    assert material["channel"] == "telegram"
    assert material["storage_key"].startswith(f"{task_id}/")
    assert_single_pending_recognition_task(client, material["id"])


def test_telegram_material_submission_routes_unbound_account_to_pending_assignment(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.post(
        "/api/telegram/materials",
        data={
            "telegram_user_id": "987654321",
            "telegram_username": "@NoBindingYet",
            "task_id": task_id,
            "material_type": "competition_notice",
        },
        files={"files": ("notice.pdf", b"telegram-notice", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["submission_identity"] == {
        "telegram_user_id": 987654321,
        "status": "pending_assignment",
        "member_id": None,
    }
    material = body["items"][0]
    assert material["status"] == "pending_assignment"
    assert material["task_id"] is None
    assert material["submitter_id"] is None
    assert material["task_id_hint"] == task_id
    assert material["submitter_id_hint"] == "telegram_user_id:987654321 (@nobindingyet)"
    assert material["channel"] == "telegram"
    assert material["storage_key"].startswith("_pending_assignment/")
    assert_single_pending_recognition_task(client, material["id"])


def test_telegram_material_submission_routes_bound_account_without_task_to_pending_assignment(
    tmp_path,
):
    client = make_client(tmp_path)
    bind_response = client.put(
        "/api/telegram-bindings/123456789",
        json={"member_id": "2250001"},
    )
    assert bind_response.status_code == 200

    response = client.post(
        "/api/telegram/materials",
        data={
            "telegram_user_id": "123456789",
            "material_type": "payment_record",
        },
        files={"files": ("payment.pdf", b"telegram-payment", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["submission_identity"] == {
        "telegram_user_id": 123456789,
        "status": "bound",
        "member_id": "2250001",
    }
    material = body["items"][0]
    assert material["status"] == "pending_assignment"
    assert material["task_id"] is None
    assert material["submitter_id"] is None
    assert material["task_id_hint"] is None
    assert material["submitter_id_hint"] == "2250001"
    assert material["channel"] == "telegram"
