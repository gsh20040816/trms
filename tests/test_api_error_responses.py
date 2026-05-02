from unittest.mock import patch

from fastapi.testclient import TestClient

from trms_backend.main import create_app

from api_error_assertions import assert_api_error
from test_auth_api import (
    make_client as make_auth_client,
    make_production_runtime_config,
    register_payload,
)
from test_materials_api import create_open_task
from test_tasks_api import (
    admin_auth_headers,
    auth_headers,
    create_task,
    register_and_get_token,
    valid_task_payload,
)


def make_client(tmp_path, runtime_config=None):
    if runtime_config is not None:
        if runtime_config.environment == "production":
            return make_auth_client(tmp_path, runtime_config=runtime_config)
        return TestClient(create_app(runtime_config=runtime_config))
    return TestClient(create_app(f"sqlite:///{tmp_path}/test.db"))


def test_bootstrap_admin_rejects_member_role_with_standard_400_error(tmp_path):
    runtime_config = make_production_runtime_config(
        tmp_path,
        TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN="bootstrap-secret",
    )
    client = make_client(tmp_path, runtime_config=runtime_config)

    response = client.post(
        "/api/auth/bootstrap-admin",
        headers={"X-TRMS-Bootstrap-Token": "bootstrap-secret"},
        json=register_payload(
            username="member-bootstrap",
            role="member",
            display_name="普通成员",
            actor_id="2250009",
            member_code="MEM-009",
        ),
    )

    payload = assert_api_error(
        response,
        status_code=400,
        code="bad_request",
    )
    assert "bootstrap endpoint only supports 'system_admin'" in payload["detail"]


def test_request_validation_error_uses_standard_error_payload(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "receipt",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )

    payload = assert_api_error(
        response,
        status_code=422,
        code="validation_error",
    )
    assert payload["detail"][0]["loc"][-1] == "material_type"


def test_request_id_header_is_propagated_on_error_response(tmp_path):
    client = make_client(tmp_path)

    response = client.get(
        "/api/tasks/missing",
        headers={"X-Request-ID": "client-request-123", **admin_auth_headers(client)},
    )

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "client-request-123"
    assert response.json()["request_id"] == "client-request-123"


def test_unhandled_error_logs_request_id_and_returns_standard_500_payload(tmp_path):
    app = create_app(f"sqlite:///{tmp_path}/test.db")

    @app.get("/boom")
    def boom():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    with patch("trms_backend.api.error_responses.LOGGER.exception") as log_exception:
        response = client.get("/boom", headers={"X-Request-ID": "client-request-500"})

    assert response.status_code == 500
    payload = response.json()
    assert payload == {
        "code": "internal_server_error",
        "message": "internal server error",
        "request_id": "client-request-500",
        "detail": "internal server error",
    }
    assert response.headers["X-Request-ID"] == "client-request-500"
    log_exception.assert_called_once()
    assert log_exception.call_args.args == (
        "unhandled request error method=%s route=%s request_id=%s",
        "GET",
        "/boom",
        "client-request-500",
    )
    assert log_exception.call_args.kwargs["extra"]["request_id"] == "client-request-500"


def test_not_found_route_uses_standard_error_payload(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/tasks/missing", headers=admin_auth_headers(client))

    assert_api_error(
        response,
        status_code=404,
        code="not_found",
        detail="task not found",
    )


def test_conflict_error_uses_standard_error_payload(tmp_path):
    client = make_client(tmp_path)

    assert client.post("/api/auth/register", json=register_payload()).status_code == 201
    response = client.post("/api/auth/register", json=register_payload())

    assert_api_error(
        response,
        status_code=409,
        code="conflict",
        detail="username already exists: member1",
    )


def test_forbidden_error_uses_standard_error_payload(tmp_path):
    client = make_client(tmp_path)
    task = create_task(client)
    outsider_headers = auth_headers(
        register_and_get_token(
            client,
            username="admin2",
            role="admin",
            actor_id="admin-2",
            member_code=None,
        )
    )

    response = client.post(
        f"/api/tasks/{task['id']}/material-reminders",
        json={
            "administrator_id": "admin-2",
            "member_id": "2250002",
            "content": "请补材料",
        },
        headers=outsider_headers,
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to manage material reminders for this task",
    )
