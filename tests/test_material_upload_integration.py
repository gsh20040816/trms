from hashlib import sha256

import pytest
from fastapi.testclient import TestClient

from trms_backend.infrastructure.database import build_session_factory, session_scope
from trms_backend.infrastructure.models import MaterialRow
from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from test_tasks_api import admin_auth_headers, create_task

TRUSTED_TELEGRAM_TOKEN = "telegram-secret"
TRUSTED_EMAIL_TOKEN = "email-secret"


def make_client(tmp_path) -> TestClient:
    runtime_config = load_runtime_config(
        env={
            "DATABASE_URL": f"sqlite:///{tmp_path}/test.db",
            "TRMS_AUTH_TELEGRAM_INBOUND_TOKEN": TRUSTED_TELEGRAM_TOKEN,
            "TRMS_AUTH_EMAIL_INBOUND_TOKEN": TRUSTED_EMAIL_TOKEN,
            "TRMS_ASYNC_JOB_MODE": "worker",
        }
    )
    return TestClient(
        create_app(
            runtime_config=runtime_config,
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def create_open_task(client: TestClient) -> str:
    created = create_task(client)
    response = client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    assert response.status_code == 200
    return created["id"]


def create_open_task_with_mail_key(client: TestClient) -> tuple[str, str]:
    created = create_task(
        client,
        payload={
            "competition_name": "Integration Mail Task",
            "competition_location": "Shanghai",
            "competition_start_date": "2026-11-01",
            "competition_end_date": "2026-11-03",
            "deadline": "2026-12-01T00:00:00Z",
            "email_submission_key": "integration-mail-task",
            "member_ids": ["2250001", "2250002", "2250003"],
            "fee_categories": ["registration", "railway", "hotel"],
            "administrator_id": "admin-1",
            "invoice_title": "同济大学",
            "tax_number": "12100000425006117D",
        },
    )
    response = client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    assert response.status_code == 200
    return created["id"], created["email_submission_key"]


def get_material_row(tmp_path, material_id: str) -> MaterialRow:
    session_factory = build_session_factory(f"sqlite:///{tmp_path}/test.db")
    with session_scope(session_factory) as session:
        row = session.get(MaterialRow, material_id)
        assert row is not None
        return row


def assert_single_pending_recognition_task(client: TestClient, material_id: str) -> None:
    response = client.get(f"/api/materials/{material_id}/recognition-tasks")

    assert response.status_code == 200
    body = response.json()
    assert body["latest_effective"] is None
    assert len(body["items"]) == 1
    assert body["items"][0]["material_id"] == material_id
    assert body["items"][0]["status"] == "pending"


def submit_assigned_material(
    client: TestClient,
    *,
    task_id: str,
    email_submission_key: str | None = None,
    channel: str,
    filename: str,
    content: bytes,
):
    if channel in {"web", "cli"}:
        response = client.post(
            f"/api/tasks/{task_id}/materials",
            data={
                "submitter_id": "2250001",
                "channel": channel,
                "material_type": "invoice",
            },
            files={"files": (filename, content, "application/pdf")},
        )
        assert response.status_code == 201
        return response.json()["items"][0]

    if channel == "telegram":
        bind_response = client.put(
            "/api/telegram-bindings/123456789",
            json={"member_id": "2250001", "telegram_username": "@TongjiCoder"},
            headers=admin_auth_headers(client),
        )
        assert bind_response.status_code == 200
        response = client.post(
            "/api/telegram/materials",
            headers={"X-TRMS-Telegram-Inbound-Token": TRUSTED_TELEGRAM_TOKEN},
            data={
                "telegram_user_id": "123456789",
                "telegram_username": "@TongjiCoder",
                "task_id": task_id,
                "material_type": "invoice",
            },
            files={"files": (filename, content, "application/pdf")},
        )
        assert response.status_code == 201
        return response.json()["items"][0]

    if channel == "email":
        response = client.post(
            "/api/email/materials",
            headers={"X-TRMS-Email-Inbound-Token": TRUSTED_EMAIL_TOKEN},
            data={
                "sender_email": "member1@tongji.edu.cn",
                "resolved_member_id": "2250001",
                "subject": f"<{email_submission_key or task_id}>Fw: upload",
            },
            files={"files": (filename, content, "application/pdf")},
        )
        assert response.status_code == 201
        return response.json()["items"][0]

    raise AssertionError(f"unsupported test channel: {channel}")


@pytest.mark.parametrize("channel", ["web", "cli", "telegram", "email"])
def test_assigned_upload_channels_share_storage_and_recognition_contract(tmp_path, channel: str):
    client = make_client(tmp_path)
    task_id, email_submission_key = create_open_task_with_mail_key(client)
    content = f"{channel}-invoice-content".encode("utf-8")

    material = submit_assigned_material(
        client,
        task_id=task_id,
        email_submission_key=email_submission_key,
        channel=channel,
        filename=f"{channel}.pdf",
        content=content,
    )

    expected_sha256 = sha256(content).hexdigest()
    assert material["status"] == "assigned"
    assert material["task_id"] == task_id
    assert material["submitter_id"] == "2250001"
    assert material["channel"] == channel
    assert material["original_filename"] == f"{channel}.pdf"
    assert material["size_bytes"] == len(content)
    assert material["sha256"] == expected_sha256
    assert material["duplicate_of"] is None
    assert material["storage_key"].startswith(f"{task_id}/")

    row = get_material_row(tmp_path, material["id"])
    assert row.task_id == task_id
    assert row.submitter_id == "2250001"
    assert row.channel == channel
    assert row.original_filename == f"{channel}.pdf"
    assert row.size_bytes == len(content)
    assert row.sha256 == expected_sha256
    assert row.duplicate_of is None

    storage_path = tmp_path / "material-storage" / material["storage_key"]
    assert storage_path.read_bytes() == content
    assert_single_pending_recognition_task(client, material["id"])


def test_duplicate_detection_matches_same_hash_across_web_and_telegram_uploads(tmp_path):
    client = make_client(tmp_path)
    task_id, email_submission_key = create_open_task_with_mail_key(client)
    content = b"same-invoice-content"

    first = submit_assigned_material(
        client,
        task_id=task_id,
        email_submission_key=email_submission_key,
        channel="web",
        filename="web.pdf",
        content=content,
    )
    duplicate = submit_assigned_material(
        client,
        task_id=task_id,
        email_submission_key=email_submission_key,
        channel="telegram",
        filename="telegram-copy.pdf",
        content=content,
    )

    expected_sha256 = sha256(content).hexdigest()
    assert first["sha256"] == expected_sha256
    assert duplicate["sha256"] == expected_sha256
    assert duplicate["duplicate_of"] == first["id"]

    duplicate_row = get_material_row(tmp_path, duplicate["id"])
    assert duplicate_row.duplicate_of == first["id"]
    duplicate_storage_path = tmp_path / "material-storage" / duplicate["storage_key"]
    assert duplicate_storage_path.read_bytes() == content


def test_batch_upload_partial_success_persists_only_valid_files(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    valid_content = b"valid-pdf-content"

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "cli",
            "material_type": "invoice",
        },
        files=[
            ("files", ("valid.pdf", valid_content, "application/pdf")),
            ("files", ("notes.txt", b"plain-text", "text/plain")),
        ],
    )

    assert response.status_code == 207
    payload = response.json()
    assert payload["status"] == "partial_success"
    assert [item["original_filename"] for item in payload["items"]] == ["valid.pdf"]
    assert payload["failures"] == [
        {
            "original_filename": "notes.txt",
            "error_code": "unsupported_content_type",
            "detail": (
                "unsupported material content type: text/plain; supported content types: "
                "application/pdf, application/zip, image/jpeg, image/png, image/webp"
            ),
        }
    ]

    saved_material = payload["items"][0]
    expected_sha256 = sha256(valid_content).hexdigest()
    assert saved_material["sha256"] == expected_sha256

    saved_row = get_material_row(tmp_path, saved_material["id"])
    assert saved_row.original_filename == "valid.pdf"
    assert saved_row.sha256 == expected_sha256

    storage_path = tmp_path / "material-storage" / saved_material["storage_key"]
    assert storage_path.read_bytes() == valid_content

    listed = client.get(
        f"/api/tasks/{task_id}/materials",
        headers=admin_auth_headers(client),
    )
    assert listed.status_code == 200
    assert [item["original_filename"] for item in listed.json()["items"]] == ["valid.pdf"]
