import re

from fastapi.testclient import TestClient

from trms_backend.application.outbound_email import OutboundEmailMessage
from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from test_tasks_api import auth_headers, register_and_get_token


class RecordingOutboundEmailSender:
    def __init__(self) -> None:
        self.messages: list[OutboundEmailMessage] = []

    def send(self, message: OutboundEmailMessage) -> None:
        self.messages.append(message)


def make_client(tmp_path, *, outbound_email_sender=None):
    runtime_config = load_runtime_config(
        env={
            "TRMS_ENV": "test",
            "DATABASE_URL": f"sqlite:///{tmp_path}/test.db",
        }
    )
    return TestClient(
        create_app(
            runtime_config=runtime_config,
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
            outbound_email_sender=outbound_email_sender,
        )
    )


def extract_latest_code(sender: RecordingOutboundEmailSender) -> str:
    assert sender.messages
    match = re.search(r"验证码：(\d{6})", sender.messages[-1].text_body)
    assert match is not None
    return match.group(1)


def member_headers(client: TestClient, *, username: str, actor_id: str) -> dict[str, str]:
    token = register_and_get_token(
        client,
        username=username,
        role="member",
        actor_id=actor_id,
        member_code=actor_id,
    )
    return auth_headers(token)


def test_member_can_bind_multiple_emails_with_verification_code(tmp_path):
    sender = RecordingOutboundEmailSender()
    client = make_client(tmp_path, outbound_email_sender=sender)
    headers = member_headers(client, username="member1", actor_id="2250001")

    first_request = client.post(
        "/api/email-bindings/verification-code",
        json={"email": "member1@tongji.edu.cn"},
        headers=headers,
    )
    assert first_request.status_code == 202
    assert sender.messages[-1].to_email == "member1@tongji.edu.cn"

    first_verify = client.post(
        "/api/email-bindings/verify",
        json={
            "email": "member1@tongji.edu.cn",
            "code": extract_latest_code(sender),
        },
        headers=headers,
    )
    assert first_verify.status_code == 200
    assert first_verify.json()["item"]["member_id"] == "2250001"

    second_request = client.post(
        "/api/email-bindings/verification-code",
        json={"email": "backup.member1@tongji.edu.cn"},
        headers=headers,
    )
    assert second_request.status_code == 202

    second_verify = client.post(
        "/api/email-bindings/verify",
        json={
            "email": "backup.member1@tongji.edu.cn",
            "code": extract_latest_code(sender),
        },
        headers=headers,
    )
    assert second_verify.status_code == 200

    list_response = client.get("/api/email-bindings", headers=headers)
    assert list_response.status_code == 200
    assert [item["email"] for item in list_response.json()["items"]] == [
        "member1@tongji.edu.cn",
        "backup.member1@tongji.edu.cn",
    ]


def test_email_binding_rejects_wrong_verification_code(tmp_path):
    sender = RecordingOutboundEmailSender()
    client = make_client(tmp_path, outbound_email_sender=sender)
    headers = member_headers(client, username="member1", actor_id="2250001")

    request_response = client.post(
        "/api/email-bindings/verification-code",
        json={"email": "member1@tongji.edu.cn"},
        headers=headers,
    )
    assert request_response.status_code == 202

    verify_response = client.post(
        "/api/email-bindings/verify",
        json={"email": "member1@tongji.edu.cn", "code": "000000"},
        headers=headers,
    )
    assert verify_response.status_code == 422
    assert verify_response.json()["detail"] == "email verification code is invalid"


def test_email_binding_rejects_conflict_with_another_member(tmp_path):
    sender = RecordingOutboundEmailSender()
    client = make_client(tmp_path, outbound_email_sender=sender)
    first_headers = member_headers(client, username="member1", actor_id="2250001")
    second_headers = member_headers(client, username="member2", actor_id="2250002")

    first_request = client.post(
        "/api/email-bindings/verification-code",
        json={"email": "shared@tongji.edu.cn"},
        headers=first_headers,
    )
    assert first_request.status_code == 202
    first_verify = client.post(
        "/api/email-bindings/verify",
        json={"email": "shared@tongji.edu.cn", "code": extract_latest_code(sender)},
        headers=first_headers,
    )
    assert first_verify.status_code == 200

    second_request = client.post(
        "/api/email-bindings/verification-code",
        json={"email": "shared@tongji.edu.cn"},
        headers=second_headers,
    )
    assert second_request.status_code == 409
    assert second_request.json()["detail"] == (
        "email is already bound to another member: shared@tongji.edu.cn"
    )


def test_email_binding_routes_require_member_role(tmp_path):
    sender = RecordingOutboundEmailSender()
    client = make_client(tmp_path, outbound_email_sender=sender)
    admin_token = register_and_get_token(
        client,
        username="admin1",
        role="admin",
        actor_id="admin-1",
        member_code=None,
    )

    response = client.post(
        "/api/email-bindings/verification-code",
        json={"email": "admin@example.edu"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to manage email bindings"


def test_email_binding_request_requires_configured_sender(tmp_path):
    client = make_client(tmp_path)
    headers = member_headers(client, username="member1", actor_id="2250001")

    response = client.post(
        "/api/email-bindings/verification-code",
        json={"email": "member1@tongji.edu.cn"},
        headers=headers,
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "outbound email is not configured"
