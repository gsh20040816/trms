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


def manual_corrections_by_field(recognition_task: dict, field_name: str) -> list[dict]:
    return [
        item
        for item in recognition_task["manual_corrections"]
        if item["field_name"] == field_name
    ]


def test_create_invoice_and_pass_basic_validations(tmp_path):
    client = make_client(tmp_path)
    task_id, material_id = create_material(client)

    response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["invoice"]["task_id"] == task_id
    assert body["invoice"]["material_id"] == material_id
    assert body["invoice"]["amount_cents"] == 12345
    title_validation = validation_by_code(body, "invoice_title_match")
    tax_validation = validation_by_code(body, "invoice_tax_number_match")
    duplicate_validation = validation_by_code(body, "invoice_number_unique")

    assert title_validation["target_type"] == "invoice"
    assert title_validation["target_id"] == body["invoice"]["id"]
    assert title_validation["severity"] == "blocker"
    assert title_validation["status"] == "passed"
    assert title_validation["evidence"] == {
        "expected_buyer_name": "同济大学",
        "actual_buyer_name": "同济大学",
    }
    assert tax_validation["status"] == "passed"
    assert tax_validation["evidence"] == {
        "expected_tax_number": "12100000425006117D",
        "actual_tax_number": "12100000425006117D",
    }
    assert duplicate_validation["status"] == "passed"
    assert duplicate_validation["evidence"] == {
        "invoice_number": "INV-001",
        "duplicate_invoice_id": None,
    }


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
    assert validation_by_code(body, "invoice_title_match")["evidence"] == {
        "expected_buyer_name": "同济大学",
        "actual_buyer_name": "错误抬头",
    }
    assert validation_by_code(body, "invoice_tax_number_match")["status"] == "failed"
    assert validation_by_code(body, "invoice_tax_number_match")["evidence"] == {
        "expected_tax_number": "12100000425006117D",
        "actual_tax_number": "WRONG-TAX-NUMBER",
    }


def test_create_invoice_marks_missing_recognized_title_and_tax_as_pending(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)
    recognition_task_id = client.get(f"/api/materials/{material_id}/recognition-tasks").json()["items"][0][
        "id"
    ]

    recognition_update = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        json={
            "target_status": "succeeded",
            "result": {
                "raw_response": {
                    "provider": "placeholder-ai",
                    "document_type": "invoice",
                },
                "recognized_fields": {
                    "invoice_number": {
                        "value": "INV-001",
                        "source": "ai",
                        "confidence": 0.99,
                        "status": "recognized",
                    }
                },
            },
        },
    )

    assert recognition_update.status_code == 200

    response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    assert response.status_code == 201
    body = response.json()
    assert validation_by_code(body, "invoice_title_match")["status"] == "pending"
    assert validation_by_code(body, "invoice_title_match")["evidence"] == {
        "expected_buyer_name": "同济大学",
        "actual_buyer_name": "同济大学",
        "recognized_buyer_name": None,
        "recognition_task_status": "succeeded",
        "recognition_status": "missing",
    }
    assert validation_by_code(body, "invoice_tax_number_match")["status"] == "pending"
    assert validation_by_code(body, "invoice_tax_number_match")["evidence"] == {
        "expected_tax_number": "12100000425006117D",
        "actual_tax_number": "12100000425006117D",
        "recognized_tax_number": None,
        "recognition_task_status": "succeeded",
        "recognition_status": "missing",
    }


def test_create_invoice_keeps_failed_when_manual_title_and_tax_mismatch_after_missing_recognition(
    tmp_path,
):
    client = make_client(tmp_path)
    _, material_id = create_material(client)
    recognition_task_id = client.get(f"/api/materials/{material_id}/recognition-tasks").json()["items"][0][
        "id"
    ]

    recognition_update = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        json={
            "target_status": "failed",
            "failure": {
                "stage": "ocr",
                "reason": "buyer name and tax number were not recognized",
            },
        },
    )

    assert recognition_update.status_code == 200

    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {
            "buyer_name": "错误抬头",
            "tax_number": "WRONG-TAX-NUMBER",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert validation_by_code(body, "invoice_title_match")["status"] == "failed"
    assert validation_by_code(body, "invoice_title_match")["evidence"] == {
        "expected_buyer_name": "同济大学",
        "actual_buyer_name": "错误抬头",
        "recognized_buyer_name": None,
        "recognition_task_status": "failed",
        "recognition_status": "missing",
    }
    assert validation_by_code(body, "invoice_tax_number_match")["status"] == "failed"
    assert validation_by_code(body, "invoice_tax_number_match")["evidence"] == {
        "expected_tax_number": "12100000425006117D",
        "actual_tax_number": "WRONG-TAX-NUMBER",
        "recognized_tax_number": None,
        "recognition_task_status": "failed",
        "recognition_status": "missing",
    }


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
    assert duplicate["evidence"]["invoice_number"] == "INV-001"
    assert duplicate["evidence"]["duplicate_invoice_id"] is not None


def test_list_invoice_validations_returns_structured_evidence(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)

    create_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload() | {"buyer_name": "错误抬头"},
    )

    assert create_response.status_code == 201
    invoice_id = create_response.json()["invoice"]["id"]

    response = client.get(f"/api/invoices/{invoice_id}/validations")

    assert response.status_code == 200
    title_validation = next(
        item for item in response.json()["items"] if item["rule_code"] == "invoice_title_match"
    )
    assert title_validation["target_type"] == "invoice"
    assert title_validation["target_id"] == invoice_id
    assert title_validation["severity"] == "blocker"
    assert title_validation["status"] == "failed"
    assert title_validation["evidence"] == {
        "expected_buyer_name": "同济大学",
        "actual_buyer_name": "错误抬头",
    }


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


def test_manual_invoice_correction_updates_recognition_fields_and_keeps_diff_history(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)
    recognition_task_id = client.get(f"/api/materials/{material_id}/recognition-tasks").json()["items"][0][
        "id"
    ]
    recognition_result = {
        "raw_response": {
            "provider": "placeholder-ai",
            "document_type": "invoice",
        },
        "recognized_fields": {
            "invoice_number": {
                "value": "INV-AI-001",
                "source": "ai",
                "confidence": 0.83,
                "status": "recognized",
            },
            "buyer_name": {
                "value": "Tongji ACM Lab",
                "source": "ocr",
                "confidence": 0.41,
                "status": "needs_confirmation",
            },
            "tax_number": {
                "value": "WRONG-TAX-NUMBER",
                "source": "ocr",
                "confidence": 0.38,
                "status": "needs_confirmation",
            },
        },
    }
    client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        json={
            "target_status": "needs_confirmation",
            "result": recognition_result,
        },
    )

    first_response = client.post(f"/api/materials/{material_id}/invoice", json=valid_invoice_payload())

    assert first_response.status_code == 201
    assert validation_by_code(first_response.json(), "invoice_title_match")["status"] == "passed"
    assert validation_by_code(first_response.json(), "invoice_tax_number_match")["status"] == "passed"

    second_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload() | {"buyer_name": "错误抬头"},
    )

    assert second_response.status_code == 201
    assert validation_by_code(second_response.json(), "invoice_title_match")["status"] == "failed"

    recognition_task = client.get(f"/api/materials/{material_id}/recognition-tasks").json()["items"][0]

    assert recognition_task["recognized_fields"]["buyer_name"]["value"] == "错误抬头"
    assert recognition_task["recognized_fields"]["buyer_name"]["source"] == "manual"
    assert recognition_task["recognized_fields"]["buyer_name"]["updated_at"] is not None
    assert recognition_task["recognized_fields"]["tax_number"]["value"] == "12100000425006117D"
    assert recognition_task["recognized_fields"]["tax_number"]["source"] == "manual"

    buyer_name_corrections = manual_corrections_by_field(recognition_task, "buyer_name")
    tax_number_corrections = manual_corrections_by_field(recognition_task, "tax_number")

    assert len(buyer_name_corrections) == 2
    assert len(tax_number_corrections) == 1
    assert buyer_name_corrections[0]["before"]["value"] == "Tongji ACM Lab"
    assert buyer_name_corrections[0]["before"]["source"] == "ocr"
    assert buyer_name_corrections[0]["after"]["value"] == "同济大学"
    assert buyer_name_corrections[0]["after"]["source"] == "manual"
    assert buyer_name_corrections[0]["revalidation_status"] == "triggered"
    assert buyer_name_corrections[0]["corrected_at"] is not None
    assert buyer_name_corrections[1]["before"]["value"] == "同济大学"
    assert buyer_name_corrections[1]["before"]["source"] == "manual"
    assert buyer_name_corrections[1]["after"]["value"] == "错误抬头"
    assert tax_number_corrections[0]["before"]["value"] == "WRONG-TAX-NUMBER"
    assert tax_number_corrections[0]["after"]["value"] == "12100000425006117D"


def test_manual_invoice_correction_on_retry_keeps_older_recognition_history_unchanged(tmp_path):
    client = make_client(tmp_path)
    _, material_id = create_material(client)
    first_recognition_task_id = client.get(f"/api/materials/{material_id}/recognition-tasks").json()[
        "items"
    ][0]["id"]
    first_result = {
        "raw_response": {
            "provider": "placeholder-ai",
            "document_type": "invoice",
        },
        "recognized_fields": {
            "buyer_name": {
                "value": "Tongji ACM Lab",
                "source": "ocr",
                "confidence": 0.44,
                "status": "needs_confirmation",
            }
        },
    }
    first_update = client.patch(
        f"/api/recognition-tasks/{first_recognition_task_id}/status",
        json={
            "target_status": "needs_confirmation",
            "result": first_result,
        },
    )

    assert first_update.status_code == 200

    retry_create = client.post(f"/api/materials/{material_id}/recognition-tasks")

    assert retry_create.status_code == 201
    retry_task_id = retry_create.json()["item"]["id"]

    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload(),
    )

    assert invoice_response.status_code == 201

    listed = client.get(f"/api/materials/{material_id}/recognition-tasks")

    assert listed.status_code == 200
    body = listed.json()
    assert [item["id"] for item in body["items"]] == [first_recognition_task_id, retry_task_id]
    assert body["items"][0]["recognized_fields"]["buyer_name"]["value"] == "Tongji ACM Lab"
    assert body["items"][0]["recognized_fields"]["buyer_name"]["source"] == "ocr"
    assert body["items"][0]["manual_corrections"] == []
    assert body["items"][1]["status"] == "needs_confirmation"
    assert body["items"][1]["recognized_fields"]["buyer_name"]["value"] == "同济大学"
    assert body["items"][1]["recognized_fields"]["buyer_name"]["source"] == "manual"
    assert body["items"][1]["manual_corrections"] != []
    assert body["latest_effective"]["id"] == retry_task_id


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
