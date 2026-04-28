from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_tasks_api import (
    admin_auth_headers,
    auth_headers,
    create_task as create_admin_task,
    register_and_get_token,
    valid_invoice_payload,
    valid_task_payload,
)


def make_client(tmp_path):
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def member_auth_headers(
    client: TestClient,
    *,
    username: str = "member1",
    actor_id: str = "2250001",
) -> dict[str, str]:
    return auth_headers(
        register_and_get_token(
            client,
            username=username,
            role="member",
            actor_id=actor_id,
            member_code=actor_id,
        )
    )


def main_flow_task_payload():
    return valid_task_payload() | {
        "competition_name": "Main flow E2E scaffold",
        "member_ids": ["2250001"],
        "fee_categories": ["railway"],
        "project_info": "Main flow integration scaffold",
        "reimburser_info": "Nightly admin",
    }


def build_fake_recognition_result():
    return {
        "raw_response": {
            "provider": "fake-llm",
            "document_type": "invoice",
        },
        "recognized_fields": {
            "invoice_number": {
                "value": "INV-MAIN-E2E-001",
                "source": "ai",
                "confidence": 0.99,
                "status": "recognized",
            },
            "buyer_name": {
                "value": "同济大学",
                "source": "ai",
                "confidence": 0.99,
                "status": "recognized",
            },
            "tax_number": {
                "value": "12100000425006117D",
                "source": "ai",
                "confidence": 0.98,
                "status": "recognized",
            },
            "amount_cents": {
                "value": 12345,
                "source": "ai",
                "confidence": 0.97,
                "status": "recognized",
            },
            "transaction_time": {
                "value": "2026-11-01T08:00:00+00:00",
                "source": "ai",
                "confidence": 0.96,
                "status": "recognized",
            },
            "expense_type": {
                "value": "railway",
                "source": "ai",
                "confidence": 0.95,
                "status": "recognized",
            },
        },
    }


def move_task_status(
    client: TestClient,
    task_id: str,
    target_status: str,
    *,
    headers: dict[str, str],
):
    response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": target_status},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def list_recognition_tasks(
    client: TestClient,
    material_id: str,
    *,
    headers: dict[str, str],
):
    response = client.get(
        f"/api/materials/{material_id}/recognition-tasks",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_main_flow_e2e_scaffold_covers_submission_to_export_gate(tmp_path):
    client = make_client(tmp_path)
    admin_headers = admin_auth_headers(client)
    member_headers = member_auth_headers(client)

    created = create_admin_task(
        client,
        payload=main_flow_task_payload(),
        headers=admin_headers,
    )
    task_id = created["id"]
    assert created["status"] == "draft"

    opened = move_task_status(client, task_id, "open", headers=admin_headers)
    assert opened["status"] == "open"

    upload_response = client.post(
        f"/api/tasks/{task_id}/materials",
        headers=member_headers,
        data={
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )
    assert upload_response.status_code == 201
    material_id = upload_response.json()["items"][0]["id"]

    initial_recognition_listing = list_recognition_tasks(
        client,
        material_id,
        headers=member_headers,
    )
    assert initial_recognition_listing["latest_effective"] is None
    assert len(initial_recognition_listing["items"]) == 1
    assert initial_recognition_listing["items"][0]["status"] == "pending"
    recognition_task_id = initial_recognition_listing["items"][0]["id"]

    recognition_response = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        headers=admin_headers,
        json={
            "target_status": "succeeded",
            "result": build_fake_recognition_result(),
        },
    )
    assert recognition_response.status_code == 200
    assert recognition_response.json()["item"]["status"] == "succeeded"

    recognition_listing = list_recognition_tasks(
        client,
        material_id,
        headers=admin_headers,
    )
    assert recognition_listing["latest_effective"]["id"] == recognition_task_id
    assert recognition_listing["latest_effective"]["recognized_fields"]["buyer_name"]["value"] == (
        "同济大学"
    )

    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        headers=admin_headers,
        json=valid_invoice_payload()
        | {
            "actor_id": "admin-1",
            "invoice_number": "INV-MAIN-E2E-001",
        },
    )
    assert invoice_response.status_code == 201
    invoice_body = invoice_response.json()
    invoice_id = invoice_body["invoice"]["id"]
    validations_by_code = {
        item["rule_code"]: item for item in invoice_body["validations"]
    }
    assert validations_by_code["invoice_title_match"]["status"] == "passed"
    assert validations_by_code["invoice_tax_number_match"]["status"] == "passed"
    assert validations_by_code["invoice_number_unique"]["status"] == "passed"

    split_response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        headers=member_headers,
        json={
            "items": [
                {
                    "member_id": "2250001",
                    "amount_cents": 12345,
                    "note": "self paid",
                }
            ]
        },
    )
    assert split_response.status_code == 200
    split_id = split_response.json()["items"][0]["id"]

    expense_details_before_confirmation = client.get(
        f"/api/tasks/{task_id}/expense-details",
        headers=member_headers,
    )
    assert expense_details_before_confirmation.status_code == 200
    detail_body = expense_details_before_confirmation.json()
    assert detail_body["actor_id"] == "2250001"
    assert detail_body["total_amount_cents"] == 12345
    assert len(detail_body["items"]) == 1
    assert detail_body["items"][0]["split_id"] == split_id
    assert detail_body["items"][0]["confirmation"] is None

    review_summary_before_confirmation = client.get(
        f"/api/tasks/{task_id}/review-summary",
        headers=admin_headers,
    )
    assert review_summary_before_confirmation.status_code == 200
    review_body_before_confirmation = review_summary_before_confirmation.json()
    assert review_body_before_confirmation["counts"]["material_count"] == 1
    assert review_body_before_confirmation["counts"]["invoice_count"] == 1
    assert review_body_before_confirmation["counts"]["validation_count"] >= 3
    assert review_body_before_confirmation["counts"]["missing_confirmation_count"] == 1
    assert review_body_before_confirmation["counts"]["pending_confirmation_count"] == 0

    blocked_export_response = client.get(
        f"/api/tasks/{task_id}/exports/capabilities",
        headers=admin_headers,
    )
    assert blocked_export_response.status_code == 200
    blocked_export_body = blocked_export_response.json()
    assert blocked_export_body["current_task_status"] == "open"
    assert blocked_export_body["export_allowed"] is False
    assert blocked_export_body["blocking_reasons"] == [
        "task must be ready_to_export or completed before real exports can be generated"
    ]

    confirmation_response = client.put(
        f"/api/splits/{split_id}/confirmation",
        headers=member_headers,
        json={"status": "confirmed"},
    )
    assert confirmation_response.status_code == 200
    assert confirmation_response.json()["status"] == "confirmed"

    move_task_status(client, task_id, "closed", headers=admin_headers)
    reviewing = move_task_status(client, task_id, "reviewing", headers=admin_headers)
    assert reviewing["status"] == "reviewing"

    ready_to_export = move_task_status(
        client,
        task_id,
        "ready_to_export",
        headers=admin_headers,
    )
    assert ready_to_export["status"] == "ready_to_export"

    review_summary_after_confirmation = client.get(
        f"/api/tasks/{task_id}/review-summary",
        headers=admin_headers,
    )
    assert review_summary_after_confirmation.status_code == 200
    review_body_after_confirmation = review_summary_after_confirmation.json()
    assert review_body_after_confirmation["counts"]["confirmed_split_count"] == 1
    assert review_body_after_confirmation["counts"]["missing_confirmation_count"] == 0
    assert review_body_after_confirmation["counts"]["pending_confirmation_count"] == 0
    assert review_body_after_confirmation["invoices"][0]["splits"][0]["confirmation"]["status"] == (
        "confirmed"
    )

    export_capabilities_response = client.get(
        f"/api/tasks/{task_id}/exports/capabilities",
        headers=admin_headers,
    )
    assert export_capabilities_response.status_code == 200
    export_capabilities = export_capabilities_response.json()
    assert export_capabilities["current_task_status"] == "ready_to_export"
    assert export_capabilities["export_allowed"] is True
    assert export_capabilities["blocking_reasons"] == []

    supported_kinds = {item["kind"]: item for item in export_capabilities["supported_exports"]}
    assert set(supported_kinds) == {
        "reimbursement_summary",
        "member_details",
        "invoice_details",
        "missing_materials",
        "finance_draft",
        "merged_pdf",
    }
    assert supported_kinds["merged_pdf"]["implemented"] is True
    assert supported_kinds["merged_pdf"]["implemented_formats"] == ["pdf"]
