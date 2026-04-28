from fastapi.testclient import TestClient

from trms_backend.main import create_app


def make_client(tmp_path):
    return TestClient(create_app(f"sqlite:///{tmp_path}/test.db"))


def test_upsert_telegram_binding_and_resolve_bound_identity(tmp_path):
    client = make_client(tmp_path)

    response = client.put(
        "/api/telegram-bindings/123456789",
        json={
            "member_id": " 2250001 ",
            "telegram_username": "@TongjiCoder",
        },
    )

    assert response.status_code == 200
    binding = response.json()["item"]
    assert binding["telegram_user_id"] == 123456789
    assert binding["member_id"] == "2250001"
    assert binding["telegram_username"] == "tongjicoder"

    fetch_response = client.get("/api/telegram-bindings/123456789")

    assert fetch_response.status_code == 200
    assert fetch_response.json()["item"]["member_id"] == "2250001"

    resolve_response = client.get("/api/telegram-bindings/123456789/submission-identity")

    assert resolve_response.status_code == 200
    assert resolve_response.json() == {
        "item": {
            "telegram_user_id": 123456789,
            "status": "bound",
            "member_id": "2250001",
        }
    }


def test_unbound_telegram_account_resolves_to_pending_assignment(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/telegram-bindings/987654321/submission-identity")

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

    first_response = client.put(
        "/api/telegram-bindings/123456789",
        json={"member_id": "2250001"},
    )
    assert first_response.status_code == 200

    conflict_response = client.put(
        "/api/telegram-bindings/222333444",
        json={"member_id": "2250001"},
    )

    assert conflict_response.status_code == 409
    assert conflict_response.json()["detail"] == (
        "member is already bound to another telegram user: 2250001"
    )
