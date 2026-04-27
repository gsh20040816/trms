from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_tasks_api import valid_task_payload


def make_client(tmp_path):
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def create_material(client: TestClient) -> tuple[str, str]:
    task = client.post("/api/tasks", json=valid_task_payload()).json()
    client.patch(f"/api/tasks/{task['id']}/status", json={"target_status": "open"})
    return task["id"], upload_material(client, task["id"])


def upload_material(client: TestClient, task_id: str, filename: str = "ticket.pdf") -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": (filename, filename.encode(), "application/pdf")},
    )
    return response.json()["items"][0]["id"]


def valid_invoice_payload():
    return {
        "invoice_number": "INV-001",
        "issue_date": "2026-11-04",
        "transaction_time": "2026-11-01T08:00:00Z",
        "buyer_name": "同济大学",
        "tax_number": "12100000425006117D",
        "seller_name": "铁路服务商",
        "amount_cents": 12345,
        "expense_type": "railway",
    }


def validation_by_code(response_body, rule_code: str):
    return next(item for item in response_body["validations"] if item["rule_code"] == rule_code)


def test_create_invoice_and_pass_basic_validations(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)

    response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["invoice"]["task_id"] == task_id
    assert body["invoice"]["material_id"] == material_id
    assert body["invoice"]["amount_cents"] == 12345
    assert validation_by_code(body, "invoice_title_match")["status"] == "passed"
    assert validation_by_code(body, "invoice_tax_number_match")["status"] == "passed"
    assert validation_by_code(body, "invoice_number_unique")["status"] == "passed"


def test_create_invoice_reports_title_and_tax_mismatch(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)
    payload = valid_invoice_payload() | {
        "buyer_name": "错误抬头",
        "tax_number": "WRONG-TAX-NUMBER",
    }

    response = client.post(f"/api/materials/{material_id}/invoice", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert validation_by_code(body, "invoice_title_match")["status"] == "failed"
    assert validation_by_code(body, "invoice_tax_number_match")["status"] == "failed"


def test_create_invoice_reports_duplicate_invoice_number(tmp_path):
    client = make_client(tmp_path)
    task_id, first_material_id = create_material(client)
    second_material_id = upload_material(client, task_id, "ticket-2.pdf")
    client.post(f"/api/materials/{first_material_id}/invoice", json=valid_invoice_payload())

    response = client.post(f"/api/materials/{second_material_id}/invoice", json=valid_invoice_payload())

    assert response.status_code == 201
    duplicate = validation_by_code(response.json(), "invoice_number_unique")
    assert duplicate["status"] == "failed"
    assert "重复" in duplicate["message"]


def test_create_invoice_rejects_expense_type_not_allowed_by_task(tmp_path):
    client = make_client(tmp_path)
    task_payload = valid_task_payload() | {"fee_categories": ["registration", "hotel"]}
    task = client.post("/api/tasks", json=task_payload).json()
    client.patch(f"/api/tasks/{task['id']}/status", json={"target_status": "open"})
    material_id = upload_material(client, task["id"])

    response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "invoice expense type railway is not allowed for task; "
        "allowed fee categories: registration, hotel"
    )


def test_list_invoices_by_task(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)
    client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    response = client.get(f"/api/tasks/{task_id}/invoices")

    assert response.status_code == 200
    assert [item["invoice_number"] for item in response.json()["items"]] == ["INV-001"]


def test_create_invoice_rejects_missing_material(tmp_path):
    client = make_client(tmp_path)

    response = client.post("/api/materials/missing/invoice", json=valid_invoice_payload())

    assert response.status_code == 404
    assert response.json()["detail"] == "material not found"
