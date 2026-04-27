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
            "items": [
                {"member_id": "2250001", "amount_cents": 6000},
                {"member_id": "2250002", "amount_cents": 6345, "note": "team shared"},
            ]
        },
    )

    assert response.status_code == 200
    assert [item["amount_cents"] for item in response.json()["items"]] == [6000, 6345]


def test_replace_invoice_splits_rejects_amount_mismatch(tmp_path):
    client = make_client(tmp_path)
    invoice_id = create_invoice(client)

    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={"items": [{"member_id": "2250001", "amount_cents": 100}]},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "split amount total must equal invoice amount"


def test_replace_invoice_splits_rejects_non_member(tmp_path):
    client = make_client(tmp_path)
    invoice_id = create_invoice(client)

    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={"items": [{"member_id": "not-in-task", "amount_cents": 12345}]},
    )

    assert response.status_code == 409
    assert "not-in-task" in response.json()["detail"]


def test_replace_invoice_splits_rejects_duplicate_member(tmp_path):
    client = make_client(tmp_path)
    invoice_id = create_invoice(client)

    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
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
        json={"items": [{"member_id": "2250001", "amount_cents": 12345}]},
    )

    response = client.get(f"/api/invoices/{invoice_id}/splits")

    assert response.status_code == 200
    assert [item["member_id"] for item in response.json()["items"]] == ["2250001"]

