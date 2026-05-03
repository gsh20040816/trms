import re

from fastapi.testclient import TestClient

from trms_backend.application.outbound_email import OutboundEmailMessage
from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from test_tasks_api import admin_auth_headers, auth_headers, create_task, register_and_get_token

TRUSTED_EMAIL_TOKEN = "email-secret"


class RecordingOutboundEmailSender:
    def __init__(self) -> None:
        self.messages: list[OutboundEmailMessage] = []

    def send(self, message: OutboundEmailMessage) -> None:
        self.messages.append(message)


def _extract_latest_code(sender: RecordingOutboundEmailSender) -> str:
    assert sender.messages
    match = re.search(r"验证码：(\d{6})", sender.messages[-1].text_body)
    assert match is not None
    return match.group(1)


def make_client(tmp_path, *, trusted_inbound_token: str | None = None, outbound_email_sender=None):
    runtime_config = load_runtime_config(
        env={
            "DATABASE_URL": f"sqlite:///{tmp_path}/test.db",
            **(
                {"TRMS_AUTH_EMAIL_INBOUND_TOKEN": trusted_inbound_token}
                if trusted_inbound_token is not None
                else {}
            ),
        }
    )
    return TestClient(
        create_app(
            runtime_config=runtime_config,
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
            outbound_email_sender=outbound_email_sender,
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


def create_open_task_with_mail_key(client: TestClient) -> tuple[str, str]:
    created = create_task(
        client,
        payload={
            "competition_name": "ICPC Mail Task",
            "competition_location": "Shanghai",
            "competition_start_date": "2026-11-01",
            "competition_end_date": "2026-11-03",
            "deadline": "2026-12-01T00:00:00Z",
            "email_submission_key": "icpc-mail-task",
            "member_ids": ["2250001", "2250002", "2250003"],
            "fee_categories": ["registration", "railway", "hotel"],
            "administrator_id": "admin-1",
            "invoice_title": "同济大学",
            "tax_number": "12100000425006117D",
        },
    )
    client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    return created["id"], created["email_submission_key"]


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


def assert_single_pending_recognition_task(client: TestClient, material_id: str) -> None:
    response = client.get(f"/api/materials/{material_id}/recognition-tasks")

    assert response.status_code == 200
    body = response.json()
    assert body["latest_effective"] is None
    assert len(body["items"]) == 1
    assert body["items"][0]["material_id"] == material_id
    assert body["items"][0]["status"] == "pending"


def test_email_material_submission_routes_trusted_resolved_member_to_assigned_flow(tmp_path):
    client = make_client(tmp_path, trusted_inbound_token=TRUSTED_EMAIL_TOKEN)
    task_id, task_key = create_open_task_with_mail_key(client)

    response = client.post(
        "/api/email/materials",
        headers={"X-TRMS-Email-Inbound-Token": TRUSTED_EMAIL_TOKEN},
        data={
            "sender_email": "Member1@Tongji.edu.cn",
            "resolved_member_id": "2250001",
            "subject": f"[TRMS] task:{task_key}",
            "body": "material_type: invoice\nsubmitter_id: 2250999\nnote: train ticket\n",
        },
        files={"files": ("invoice.pdf", b"email-pdf", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["parsed_email"] == {
        "sender_email": "member1@tongji.edu.cn",
        "task_id": task_id,
        "submitted_task_key": task_key,
        "material_type": "invoice",
        "metadata_submitter_id": "2250999",
        "note": "train ticket",
    }
    material = body["items"][0]
    assert material["status"] == "assigned"
    assert material["task_id"] == task_id
    assert material["submitter_id"] == "2250001"
    assert material["task_id_hint"] is None
    assert material["submitter_id_hint"] is None
    assert material["channel"] == "email"
    assert material["storage_key"].startswith(f"{task_id}/")
    assert_single_pending_recognition_task(client, material["id"])


def test_email_material_submission_without_trusted_header_keeps_claimed_member_pending_assignment(
    tmp_path,
):
    client = make_client(tmp_path, trusted_inbound_token=TRUSTED_EMAIL_TOKEN)
    _task_id, task_key = create_open_task_with_mail_key(client)

    response = client.post(
        "/api/email/materials",
        data={
            "sender_email": "member1@tongji.edu.cn",
            "resolved_member_id": "2250001",
            "subject": f"[TRMS] task:{task_key}",
            "body": "material_type: invoice\nsubmitter_id: 2250999\n",
        },
        files={"files": ("invoice.pdf", b"email-pdf", "application/pdf")},
    )

    assert response.status_code == 201
    material = response.json()["items"][0]
    assert material["status"] == "pending_assignment"
    assert material["task_id"] is None
    assert material["submitter_id"] is None
    assert material["task_id_hint"] == task_key
    assert material["submitter_id_hint"] == "email:member1@tongji.edu.cn (submitter_id:2250999)"
    assert material["channel"] == "email"
    assert material["storage_key"].startswith("_pending_assignment/")
    assert_single_pending_recognition_task(client, material["id"])


def test_email_material_submission_rejects_invalid_trusted_header(tmp_path):
    client = make_client(tmp_path, trusted_inbound_token=TRUSTED_EMAIL_TOKEN)
    _task_id, task_key = create_open_task_with_mail_key(client)

    response = client.post(
        "/api/email/materials",
        headers={"X-TRMS-Email-Inbound-Token": "wrong-token"},
        data={
            "sender_email": "member1@tongji.edu.cn",
            "resolved_member_id": "2250001",
            "subject": f"[TRMS] task:{task_key}",
            "body": "material_type: invoice\n",
        },
        files={"files": ("invoice.pdf", b"email-pdf", "application/pdf")},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid email inbound token"


def test_email_material_submission_routes_unresolved_sender_to_pending_assignment(tmp_path):
    client = make_client(tmp_path)
    _task_id, task_key = create_open_task_with_mail_key(client)

    response = client.post(
        "/api/email/materials",
        data={
            "sender_email": "member2@tongji.edu.cn",
            "subject": f"[TRMS] task:{task_key}",
            "body": "material_type: competition_notice\nsubmitter_id: 2250002\n",
        },
        files={"files": ("notice.pdf", b"email-notice", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    material = body["items"][0]
    assert material["status"] == "pending_assignment"
    assert material["task_id"] is None
    assert material["submitter_id"] is None
    assert material["task_id_hint"] == task_key
    assert material["submitter_id_hint"] == "email:member2@tongji.edu.cn (submitter_id:2250002)"
    assert material["channel"] == "email"
    assert material["storage_key"].startswith("_pending_assignment/")
    assert_single_pending_recognition_task(client, material["id"])


def test_email_material_submission_uses_bound_sender_email_without_trusted_header(tmp_path):
    sender = RecordingOutboundEmailSender()
    client = make_client(tmp_path, outbound_email_sender=sender)
    task_id, task_key = create_open_task_with_mail_key(client)
    member_headers = member_auth_headers(client, username="member1", actor_id="2250001")

    verification_request = client.post(
        "/api/email-bindings/verification-code",
        json={"email": "member1@tongji.edu.cn"},
        headers=member_headers,
    )
    assert verification_request.status_code == 202

    verification_confirm = client.post(
        "/api/email-bindings/verify",
        json={
            "email": "member1@tongji.edu.cn",
            "code": _extract_latest_code(sender),
        },
        headers=member_headers,
    )
    assert verification_confirm.status_code == 200

    response = client.post(
        "/api/email/materials",
        data={
            "sender_email": "Member1@Tongji.edu.cn",
            "subject": f"[TRMS] task:{task_key}",
            "body": "material_type: invoice\n",
        },
        files={"files": ("invoice.pdf", b"email-pdf", "application/pdf")},
    )

    assert response.status_code == 201
    material = response.json()["items"][0]
    assert material["status"] == "assigned"
    assert material["task_id"] == task_id
    assert material["submitter_id"] == "2250001"
    assert material["channel"] == "email"


def test_email_material_submission_routes_unknown_task_to_pending_assignment(tmp_path):
    client = make_client(tmp_path, trusted_inbound_token=TRUSTED_EMAIL_TOKEN)

    response = client.post(
        "/api/email/materials",
        headers={"X-TRMS-Email-Inbound-Token": TRUSTED_EMAIL_TOKEN},
        data={
            "sender_email": "member1@tongji.edu.cn",
            "resolved_member_id": "2250001",
            "subject": "[TRMS] task:missing-task",
            "body": "material_type: invoice\n",
        },
        files={"files": ("invoice.pdf", b"email-pdf", "application/pdf")},
    )

    assert response.status_code == 201
    material = response.json()["items"][0]
    assert material["status"] == "pending_assignment"
    assert material["task_id"] is None
    assert material["submitter_id"] is None
    assert material["task_id_hint"] == "missing-task"
    assert material["submitter_id_hint"] == "2250001"
    assert material["channel"] == "email"


def test_email_material_submission_rejects_subject_without_trms_prefix(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/email/materials",
        data={
            "sender_email": "member1@tongji.edu.cn",
            "subject": "task:task-1",
            "body": "material_type: invoice\n",
        },
        files={"files": ("invoice.pdf", b"email-pdf", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json() == {
        "status": "failed",
        "error_code": "invalid_subject_prefix",
        "detail": "email subject must start with [TRMS]",
    }


def test_email_material_submission_rejects_task_id_mismatch(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/email/materials",
        data={
            "sender_email": "member1@tongji.edu.cn",
            "subject": "[TRMS] task:task-1",
            "body": "material_type: invoice\ntask_id: task-2\n",
        },
        files={"files": ("invoice.pdf", b"email-pdf", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json() == {
        "status": "failed",
        "error_code": "task_id_mismatch",
        "detail": "metadata task_id does not match subject task_id",
    }


def test_email_material_submission_reports_missing_attachment_filename_as_partial_failure(tmp_path):
    client = make_client(tmp_path, trusted_inbound_token=TRUSTED_EMAIL_TOKEN)
    _task_id, task_key = create_open_task_with_mail_key(client)

    response = client.post(
        "/api/email/materials",
        headers={"X-TRMS-Email-Inbound-Token": TRUSTED_EMAIL_TOKEN},
        data={
            "sender_email": "member1@tongji.edu.cn",
            "resolved_member_id": "2250001",
            "subject": f"[TRMS] task:{task_key}",
            "body": "material_type: invoice\n",
        },
        files=[
            ("files", ("invoice.pdf", b"email-pdf", "application/pdf")),
            ("files", ("   ", b"email-no-name", "application/pdf")),
        ],
    )

    assert response.status_code == 207
    payload = response.json()
    assert payload["status"] == "partial_success"
    assert [item["original_filename"] for item in payload["items"]] == ["invoice.pdf"]
    assert payload["failures"] == [
        {
            "original_filename": "   ",
            "error_code": "attachment_missing_filename",
            "detail": "uploaded file must have a filename",
        }
    ]


def test_email_material_submission_keeps_legacy_task_id_subject_compatible(tmp_path):
    client = make_client(tmp_path, trusted_inbound_token=TRUSTED_EMAIL_TOKEN)
    task_id = create_open_task(client)

    response = client.post(
        "/api/email/materials",
        headers={"X-TRMS-Email-Inbound-Token": TRUSTED_EMAIL_TOKEN},
        data={
            "sender_email": "member1@tongji.edu.cn",
            "resolved_member_id": "2250001",
            "subject": f"[TRMS] task:{task_id}",
            "body": "material_type: invoice\n",
        },
        files={"files": ("invoice.pdf", b"email-pdf", "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["parsed_email"]["task_id"] == task_id
    assert payload["parsed_email"]["submitted_task_key"] == task_id
    assert payload["items"][0]["task_id"] == task_id
