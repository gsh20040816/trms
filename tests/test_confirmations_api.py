from fastapi.testclient import TestClient

from trms_backend.main import create_app

from test_splits_api import create_invoice


def make_client(tmp_path):
    return TestClient(create_app(f"sqlite:///{tmp_path}/test.db"))


def create_split(client: TestClient) -> tuple[str, str]:
    invoice_id = create_invoice(client)
    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={"actor_id": "2250001", "items": [{"member_id": "2250001", "amount_cents": 12345}]},
    )
    return invoice_id, response.json()["items"][0]["id"]


def test_confirm_own_split(tmp_path):
    client = make_client(tmp_path)
    _, split_id = create_split(client)

    response = client.put(
        f"/api/splits/{split_id}/confirmation",
        json={"actor_id": "2250001", "member_id": "2250001", "status": "confirmed"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    assert response.json()["member_id"] == "2250001"
    assert response.json()["split_version"] == 1
    assert response.json()["is_current"] is True


def test_dispute_own_split(tmp_path):
    client = make_client(tmp_path)
    _, split_id = create_split(client)

    response = client.put(
        f"/api/splits/{split_id}/confirmation",
        json={
            "actor_id": "2250001",
            "member_id": "2250001",
            "status": "disputed",
            "dispute_reason": "amount is wrong",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "disputed"
    assert response.json()["dispute_reason"] == "amount is wrong"
    assert response.json()["split_version"] == 1
    assert response.json()["is_current"] is True


def test_dispute_requires_reason(tmp_path):
    client = make_client(tmp_path)
    _, split_id = create_split(client)

    response = client.put(
        f"/api/splits/{split_id}/confirmation",
        json={"actor_id": "2250001", "member_id": "2250001", "status": "disputed"},
    )

    assert response.status_code == 422


def test_member_cannot_submit_pending_confirmation_status(tmp_path):
    client = make_client(tmp_path)
    _, split_id = create_split(client)

    response = client.put(
        f"/api/splits/{split_id}/confirmation",
        json={"actor_id": "2250001", "member_id": "2250001", "status": "pending"},
    )

    assert response.status_code == 422


def test_member_cannot_confirm_other_member_split(tmp_path):
    client = make_client(tmp_path)
    _, split_id = create_split(client)

    response = client.put(
        f"/api/splits/{split_id}/confirmation",
        json={"actor_id": "2250002", "member_id": "2250002", "status": "confirmed"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "member can only confirm own split"


def test_administrator_cannot_confirm_split_for_member_by_default(tmp_path):
    client = make_client(tmp_path)
    _, split_id = create_split(client)

    response = client.put(
        f"/api/splits/{split_id}/confirmation",
        json={"actor_id": "admin-1", "member_id": "2250001", "status": "confirmed"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "proxy confirmation is not allowed"


def test_list_invoice_confirmations(tmp_path):
    client = make_client(tmp_path)
    invoice_id, split_id = create_split(client)
    confirmation_response = client.put(
        f"/api/splits/{split_id}/confirmation",
        json={"actor_id": "2250001", "member_id": "2250001", "status": "confirmed"},
    )

    response = client.get(f"/api/invoices/{invoice_id}/confirmations")

    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            **confirmation_response.json(),
            "confirmed_at": response.json()["items"][0]["confirmed_at"],
            "updated_at": response.json()["items"][0]["updated_at"],
        }
    ]
