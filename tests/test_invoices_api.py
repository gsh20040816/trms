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


def upload_supporting_material(
    client: TestClient,
    task_id: str,
    *,
    material_type: str = "payment_record",
    filename: str = "payment.png",
    content_type: str = "image/png",
) -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": material_type,
        },
        files={"files": (filename, filename.encode(), content_type)},
    )
    return response.json()["items"][0]["id"]


def valid_invoice_payload():
    return {
        "actor_id": "2250001",
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


def test_task_administrator_can_record_invoice_for_member_material(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload() | {"actor_id": "admin-1"},
    )

    assert response.status_code == 201
    assert response.json()["invoice"]["task_id"] == task_id


def test_create_invoice_rejects_actor_outside_submitter_and_administrator(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload() | {"actor_id": "outsider-1"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "only the material submitter or task administrator can record invoice fields"
    )


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


def test_create_invoice_updates_existing_material_invoice_instead_of_creating_duplicate(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)
    first_response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())
    first_invoice_id = first_response.json()["invoice"]["id"]

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {
            "amount_cents": 54321,
            "buyer_name": "错误抬头",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["invoice"]["id"] == first_invoice_id
    assert body["invoice"]["amount_cents"] == 54321
    assert validation_by_code(body, "invoice_title_match")["status"] == "failed"

    listed = client.get(f"/api/tasks/{task_id}/invoices")

    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1
    assert listed.json()["items"][0]["id"] == first_invoice_id
    assert listed.json()["items"][0]["amount_cents"] == 54321


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


def test_create_invoice_rejects_non_invoice_material(tmp_path):
    client = make_client(tmp_path)
    task = client.post("/api/tasks", json=valid_task_payload()).json()
    client.patch(f"/api/tasks/{task['id']}/status", json={"target_status": "open"})
    material_id = upload_supporting_material(client, task["id"], material_type="payment_record")

    response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    assert response.status_code == 409
    assert response.json()["detail"] == "invoice can only be created from invoice material"


def test_attach_supporting_material_allows_same_attachment_for_multiple_invoices(tmp_path):
    client = make_client(tmp_path)
    task_id, first_material_id = create_material(client)
    second_material_id = upload_material(client, task_id, "ticket-2.pdf")
    supporting_material_id = upload_supporting_material(client, task_id)
    first_invoice_id = client.post(
        f"/api/materials/{first_material_id}/invoice",
        json=valid_invoice_payload(),
    ).json()["invoice"]["id"]
    second_invoice_id = client.post(
        f"/api/materials/{second_material_id}/invoice",
        json=valid_invoice_payload() | {"invoice_number": "INV-002"},
    ).json()["invoice"]["id"]

    first_response = client.put(
        f"/api/invoices/{first_invoice_id}/supporting-materials/{supporting_material_id}"
    )
    second_response = client.put(
        f"/api/invoices/{second_invoice_id}/supporting-materials/{supporting_material_id}"
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    listed_first = client.get(f"/api/invoices/{first_invoice_id}/supporting-materials")
    listed_second = client.get(f"/api/invoices/{second_invoice_id}/supporting-materials")

    assert listed_first.status_code == 200
    assert listed_second.status_code == 200
    assert [item["id"] for item in listed_first.json()["items"]] == [supporting_material_id]
    assert [item["id"] for item in listed_second.json()["items"]] == [supporting_material_id]


def test_detach_supporting_material_removes_invoice_association(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)
    invoice_id = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload(),
    ).json()["invoice"]["id"]
    supporting_material_id = upload_supporting_material(client, task_id)
    client.put(f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}")

    response = client.delete(f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    listed = client.get(f"/api/invoices/{invoice_id}/supporting-materials")

    assert listed.status_code == 200
    assert listed.json()["items"] == []


def test_attach_supporting_material_rejects_invoice_type_material(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)
    invoice_id = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload(),
    ).json()["invoice"]["id"]
    another_invoice_material_id = upload_material(client, task_id, "ticket-2.pdf")

    response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{another_invoice_material_id}"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "supporting material must not be invoice type"
