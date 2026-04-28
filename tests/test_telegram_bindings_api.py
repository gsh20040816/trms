from fastapi.testclient import TestClient

from trms_backend.main import create_app

from test_tasks_api import admin_auth_headers, auth_headers, register_and_get_token


def make_client(tmp_path):
    return TestClient(create_app(f"sqlite:///{tmp_path}/test.db"))


def test_admin_can_upsert_telegram_binding_and_resolve_bound_identity(tmp_path):
    client = make_client(tmp_path)

    response = client.put(
        "/api/telegram-bindings/123456789",
        json={
            "member_id": " 2250001 ",
            "telegram_username": "@TongjiCoder",
        },
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    binding = response.json()["item"]
    assert binding["telegram_user_id"] == 123456789
    assert binding["member_id"] == "2250001"
    assert binding["telegram_username"] == "tongjicoder"

    fetch_response = client.get(
        "/api/telegram-bindings/123456789",
        headers=admin_auth_headers(client),
    )

    assert fetch_response.status_code == 200
    assert fetch_response.json()["item"]["member_id"] == "2250001"

    resolve_response = client.get(
        "/api/telegram-bindings/123456789/submission-identity",
        headers=admin_auth_headers(client),
    )

    assert resolve_response.status_code == 200
    assert resolve_response.json() == {
        "item": {
            "telegram_user_id": 123456789,
            "status": "bound",
            "member_id": "2250001",
        }
    }


def test_telegram_binding_routes_require_admin_management_role(tmp_path):
    client = make_client(tmp_path)
    member_token = register_and_get_token(
        client,
        username="member1",
        role="member",
        actor_id="2250001",
        member_code="2250001",
    )

    anonymous_response = client.put(
        "/api/telegram-bindings/123456789",
        json={"member_id": "2250001"},
    )
    assert anonymous_response.status_code == 401

    member_response = client.put(
        "/api/telegram-bindings/123456789",
        json={"member_id": "2250001"},
        headers=auth_headers(member_token),
    )
    assert member_response.status_code == 403
    assert member_response.json()["detail"] == (
        "actor is not allowed to manage telegram account bindings"
    )


def test_admin_can_resolve_unbound_telegram_account_to_pending_assignment(tmp_path):
    client = make_client(tmp_path)

    response = client.get(
        "/api/telegram-bindings/987654321/submission-identity",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json() == {
        "item": {
            "telegram_user_id": 987654321,
            "status": "pending_assignment",
            "member_id": None,
        }
    }


def test_binding_rejects_member_conflict(tmp_path):
    client = make_client(tmp_path)
    headers = admin_auth_headers(client)

    first_response = client.put(
        "/api/telegram-bindings/123456789",
        json={"member_id": "2250001"},
        headers=headers,
    )
    assert first_response.status_code == 200

    conflict_response = client.put(
        "/api/telegram-bindings/222333444",
        json={"member_id": "2250001"},
        headers=headers,
    )

    assert conflict_response.status_code == 409
    assert conflict_response.json()["detail"] == (
        "member is already bound to another telegram user: 2250001"
    )
