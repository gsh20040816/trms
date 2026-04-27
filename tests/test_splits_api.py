from fastapi.testclient import TestClient

from trms_backend.main import create_app

from test_invoices_api import create_material, valid_invoice_payload


def make_client(tmp_path):
    return TestClient(create_app(f"sqlite:///{tmp_path}/test.db"))


def create_invoice(client: TestClient) -> str:
    _, material_id = create_material(client)
    response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())
    return response.json()["invoice"]["id"]


def test_replace_invoice_splits(tmp_path):
    client = make_client(tmp_path)
    invoice_id = create_invoice(client)

    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 6000},
                {"member_id": "2250002", "amount_cents": 6345, "note": "team shared"},
            ]
        },
    )

    assert response.status_code == 200
    assert [item["amount_cents"] for item in response.json()["items"]] == [6000, 6345]
    assert [item["version"] for item in response.json()["items"]] == [1, 1]


def test_replace_invoice_splits_rejects_amount_mismatch(tmp_path):
    client = make_client(tmp_path)
    invoice_id = create_invoice(client)

    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={"actor_id": "2250001", "items": [{"member_id": "2250001", "amount_cents": 100}]},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "split amount total must equal invoice amount"


def test_replace_invoice_splits_rejects_non_member(tmp_path):
    client = make_client(tmp_path)
    invoice_id = create_invoice(client)

    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [{"member_id": "not-in-task", "amount_cents": 12345}],
        },
    )

    assert response.status_code == 409
    assert "not-in-task" in response.json()["detail"]


def test_replace_invoice_splits_rejects_duplicate_member(tmp_path):
    client = make_client(tmp_path)
    invoice_id = create_invoice(client)

    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 6000},
                {"member_id": "2250001", "amount_cents": 6345},
            ]
        },
    )

    assert response.status_code == 422


def test_list_invoice_splits(tmp_path):
    client = make_client(tmp_path)
    invoice_id = create_invoice(client)
    client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={"actor_id": "2250001", "items": [{"member_id": "2250001", "amount_cents": 12345}]},
    )

    response = client.get(f"/api/invoices/{invoice_id}/splits")

    assert response.status_code == 200
    assert [item["member_id"] for item in response.json()["items"]] == ["2250001"]


def test_split_member_can_replace_invoice_splits(tmp_path):
    client = make_client(tmp_path)
    invoice_id = create_invoice(client)

    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250002",
            "items": [
                {"member_id": "2250002", "amount_cents": 6000},
                {"member_id": "2250003", "amount_cents": 6345},
            ],
        },
    )

    assert response.status_code == 200
    assert [item["member_id"] for item in response.json()["items"]] == ["2250002", "2250003"]


def test_task_administrator_can_replace_invoice_splits(tmp_path):
    client = make_client(tmp_path)
    invoice_id = create_invoice(client)

    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "admin-1",
            "items": [
                {"member_id": "2250002", "amount_cents": 6000},
                {"member_id": "2250003", "amount_cents": 6345},
            ],
        },
    )

    assert response.status_code == 200
    assert [item["member_id"] for item in response.json()["items"]] == ["2250002", "2250003"]


def test_unrelated_member_cannot_replace_invoice_splits(tmp_path):
    client = make_client(tmp_path)
    invoice_id = create_invoice(client)

    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "outsider-1",
            "items": [
                {"member_id": "2250002", "amount_cents": 6000},
                {"member_id": "2250003", "amount_cents": 6345},
            ],
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "only the invoice submitter, split member, or task administrator can submit splits"
    )


def test_replace_invoice_splits_resets_changed_member_confirmations_to_pending(tmp_path):
    client = make_client(tmp_path)
    invoice_id = create_invoice(client)

    initial_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 6000},
                {"member_id": "2250002", "amount_cents": 6345},
            ],
        },
    )
    assert initial_response.status_code == 200
    initial_split_ids = {item["member_id"]: item["id"] for item in initial_response.json()["items"]}

    for member_id, split_id in initial_split_ids.items():
        response = client.put(
            f"/api/splits/{split_id}/confirmation",
            json={"member_id": member_id, "status": "confirmed"},
        )
        assert response.status_code == 200

    replace_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "admin-1",
            "items": [
                {"member_id": "2250001", "amount_cents": 6100},
                {"member_id": "2250002", "amount_cents": 6245},
            ],
        },
    )

    assert replace_response.status_code == 200
    replaced_items = replace_response.json()["items"]
    assert {item["member_id"]: item["id"] for item in replaced_items} == initial_split_ids
    assert {item["member_id"]: item["version"] for item in replaced_items} == {
        "2250001": 2,
        "2250002": 2,
    }

    confirmation_response = client.get(f"/api/invoices/{invoice_id}/confirmations")

    assert confirmation_response.status_code == 200
    current_confirmations = {
        item["member_id"]: item
        for item in confirmation_response.json()["items"]
        if item["is_current"]
    }
    assert current_confirmations["2250001"]["status"] == "pending"
    assert current_confirmations["2250001"]["split_version"] == 2
    assert current_confirmations["2250002"]["status"] == "pending"
    assert current_confirmations["2250002"]["split_version"] == 2

    historical_confirmations = [
        item for item in confirmation_response.json()["items"] if not item["is_current"]
    ]
    assert {(item["member_id"], item["split_version"], item["status"]) for item in historical_confirmations} == {
        ("2250001", 1, "confirmed"),
        ("2250002", 1, "confirmed"),
    }


def test_replace_invoice_splits_keeps_unchanged_member_confirmation(tmp_path):
    client = make_client(tmp_path)
    invoice_id = create_invoice(client)

    initial_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "2250001",
            "items": [
                {"member_id": "2250001", "amount_cents": 6000},
                {"member_id": "2250002", "amount_cents": 6345},
            ],
        },
    )
    assert initial_response.status_code == 200
    initial_split_ids = {item["member_id"]: item["id"] for item in initial_response.json()["items"]}

    response = client.put(
        f"/api/splits/{initial_split_ids['2250001']}/confirmation",
        json={"member_id": "2250001", "status": "confirmed"},
    )
    assert response.status_code == 200

    replace_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": "admin-1",
            "items": [
                {"member_id": "2250001", "amount_cents": 6000},
                {"member_id": "2250003", "amount_cents": 6345},
            ],
        },
    )

    assert replace_response.status_code == 200
    replaced_items = replace_response.json()["items"]
    replaced_split_ids = {item["member_id"]: item["id"] for item in replaced_items}
    assert replaced_split_ids["2250001"] == initial_split_ids["2250001"]
    assert {item["member_id"]: item["version"] for item in replaced_items} == {
        "2250001": 1,
        "2250003": 1,
    }

    confirmation_response = client.get(f"/api/invoices/{invoice_id}/confirmations")

    assert confirmation_response.status_code == 200
    assert confirmation_response.json()["items"] == [
        {
            **response.json(),
            "confirmed_at": confirmation_response.json()["items"][0]["confirmed_at"],
            "updated_at": confirmation_response.json()["items"][0]["updated_at"],
        }
    ]
