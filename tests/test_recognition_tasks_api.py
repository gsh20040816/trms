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


def create_task(client: TestClient) -> str:
    task = client.post("/api/tasks", json=valid_task_payload()).json()
    client.patch(f"/api/tasks/{task['id']}/status", json={"target_status": "open"})
    return task["id"]


def upload_material(
    client: TestClient,
    task_id: str,
    *,
    filename: str = "ticket.pdf",
) -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": (filename, filename.encode(), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["items"][0]["id"]


def get_single_recognition_task(client: TestClient, material_id: str) -> dict:
    listed = client.get(f"/api/materials/{material_id}/recognition-tasks")

    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    return items[0]


def test_uploaded_material_auto_creates_placeholder_recognition_task_marks_ai_output_non_final(
    tmp_path,
):
    client = make_client(tmp_path)
    task_id = create_task(client)
    material_id = upload_material(client, task_id)

    body = get_single_recognition_task(client, material_id)
    listing = client.get(f"/api/materials/{material_id}/recognition-tasks")

    assert body["material_id"] == material_id
    assert body["status"] == "pending"
    assert body["is_final_fact"] is False
    assert body["failure"] is None
    assert body["raw_response"] is None
    assert body["recognized_fields"] == {}
    assert body["manual_corrections"] == []
    assert listing.json()["retry_count"] == 0
    assert listing.json()["latest_effective"] is None


def test_create_manual_recognition_task_adds_retry_attempt_for_material(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    material_id = upload_material(client, task_id)

    response = client.post(f"/api/materials/{material_id}/recognition-tasks")

    assert response.status_code == 201
    created = response.json()["item"]

    listed = client.get(f"/api/materials/{material_id}/recognition-tasks")

    assert listed.status_code == 200
    items = listed.json()["items"]
    assert listed.json()["retry_count"] == 1
    assert listed.json()["latest_effective"] is None
    assert len(items) == 2
    assert items[0]["status"] == "pending"
    assert items[1]["id"] == created["id"]
    assert items[1]["status"] == "pending"
    assert items[1]["is_final_fact"] is False
    assert items[1]["failure"] is None
    assert items[1]["raw_response"] is None
    assert items[1]["recognized_fields"] == {}
    assert items[1]["manual_corrections"] == []


def test_recognition_task_can_move_to_needs_confirmation_then_succeeded(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    material_id = upload_material(client, task_id)
    recognition_task_id = get_single_recognition_task(client, material_id)["id"]

    pending_to_confirmation = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        json={"target_status": "needs_confirmation"},
    )
    confirmation_to_success = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        json={"target_status": "succeeded"},
    )

    assert pending_to_confirmation.status_code == 200
    assert pending_to_confirmation.json()["item"]["status"] == "needs_confirmation"
    assert confirmation_to_success.status_code == 200
    assert confirmation_to_success.json()["item"]["status"] == "succeeded"


def test_recognition_task_can_move_to_failed(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    material_id = upload_material(client, task_id, filename="ticket-2.pdf")
    recognition_task_id = get_single_recognition_task(client, material_id)["id"]

    missing_failure_detail = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        json={"target_status": "failed"},
    )
    response = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        json={
            "target_status": "failed",
            "failure": {
                "stage": "ocr",
                "reason": "failed to extract text from scanned PDF",
            },
        },
    )

    assert missing_failure_detail.status_code == 422
    assert "failed recognition task requires failure detail" in str(
        missing_failure_detail.json()["detail"]
    )
    assert response.status_code == 200
    body = response.json()["item"]
    assert body["status"] == "failed"
    assert body["failure"] == {
        "stage": "ocr",
        "reason": "failed to extract text from scanned PDF",
    }

    listed = client.get(f"/api/materials/{material_id}/recognition-tasks")

    assert listed.status_code == 200
    assert listed.json()["items"][0]["status"] == "failed"
    assert listed.json()["items"][0]["failure"] == {
        "stage": "ocr",
        "reason": "failed to extract text from scanned PDF",
    }


def test_recognition_task_rejects_invalid_terminal_transition(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    material_id = upload_material(client, task_id)
    recognition_task_id = get_single_recognition_task(client, material_id)["id"]
    client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        json={"target_status": "succeeded"},
    )

    response = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        json={"target_status": "pending"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "recognition task cannot transition from succeeded to pending"
    )


def test_low_confidence_fields_require_needs_confirmation_and_are_persisted(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    material_id = upload_material(client, task_id, filename="ticket-3.pdf")
    recognition_task_id = get_single_recognition_task(client, material_id)["id"]
    recognition_result = {
        "raw_response": {
            "provider": "placeholder-ai",
            "document_type": "invoice",
        },
        "recognized_fields": {
            "invoice_number": {
                "value": "INV-001",
                "source": "ai",
                "confidence": 0.98,
                "status": "recognized",
            },
            "buyer_name": {
                "value": "Tongji ACM Lab",
                "source": "ocr",
                "confidence": 0.42,
                "status": "needs_confirmation",
            },
        },
    }

    invalid_success = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        json={
            "target_status": "succeeded",
            "result": recognition_result,
        },
    )

    assert invalid_success.status_code == 422
    assert "low-confidence recognition fields require needs_confirmation status" in str(
        invalid_success.json()["detail"]
    )

    response = client.patch(
        f"/api/recognition-tasks/{recognition_task_id}/status",
        json={
            "target_status": "needs_confirmation",
            "result": recognition_result,
        },
    )

    assert response.status_code == 200
    body = response.json()["item"]
    assert body["status"] == "needs_confirmation"
    assert body["raw_response"] == recognition_result["raw_response"]
    assert body["recognized_fields"]["invoice_number"]["confidence"] == 0.98
    assert body["recognized_fields"]["buyer_name"]["source"] == "ocr"
    assert body["recognized_fields"]["buyer_name"]["status"] == "needs_confirmation"

    listed = client.get(f"/api/materials/{material_id}/recognition-tasks")

    assert listed.status_code == 200
    listed_body = listed.json()["items"][0]
    assert listed.json()["latest_effective"]["id"] == recognition_task_id
    assert listed_body["raw_response"] == recognition_result["raw_response"]
    assert listed_body["recognized_fields"]["buyer_name"]["confidence"] == 0.42
    assert listed_body["recognized_fields"]["buyer_name"]["status"] == "needs_confirmation"


def test_recognition_task_listing_returns_latest_effective_result_and_full_history(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    material_id = upload_material(client, task_id, filename="ticket-4.pdf")
    first_task_id = get_single_recognition_task(client, material_id)["id"]

    first_result = {
        "raw_response": {"provider": "placeholder-ai", "document_type": "invoice"},
        "recognized_fields": {
            "invoice_number": {
                "value": "INV-HISTORY-001",
                "source": "ai",
                "confidence": 0.97,
                "status": "recognized",
            }
        },
    }
    first_update = client.patch(
        f"/api/recognition-tasks/{first_task_id}/status",
        json={
            "target_status": "succeeded",
            "result": first_result,
        },
    )

    assert first_update.status_code == 200

    retry_create = client.post(f"/api/materials/{material_id}/recognition-tasks")

    assert retry_create.status_code == 201
    second_task_id = retry_create.json()["item"]["id"]

    listed_after_retry = client.get(f"/api/materials/{material_id}/recognition-tasks")

    assert listed_after_retry.status_code == 200
    retry_listing_body = listed_after_retry.json()
    assert retry_listing_body["retry_count"] == 1
    assert [item["id"] for item in retry_listing_body["items"]] == [first_task_id, second_task_id]
    assert retry_listing_body["latest_effective"]["id"] == first_task_id
    assert retry_listing_body["latest_effective"]["recognized_fields"]["invoice_number"]["value"] == (
        "INV-HISTORY-001"
    )

    second_update = client.patch(
        f"/api/recognition-tasks/{second_task_id}/status",
        json={
            "target_status": "failed",
            "failure": {
                "stage": "ai",
                "reason": "retry attempt timed out",
            },
        },
    )

    assert second_update.status_code == 200

    listed_after_failure = client.get(f"/api/materials/{material_id}/recognition-tasks")

    assert listed_after_failure.status_code == 200
    failed_listing_body = listed_after_failure.json()
    assert failed_listing_body["retry_count"] == 1
    assert [item["id"] for item in failed_listing_body["items"]] == [first_task_id, second_task_id]
    assert failed_listing_body["items"][0]["status"] == "succeeded"
    assert failed_listing_body["items"][1]["status"] == "failed"
    assert failed_listing_body["items"][0]["recognized_fields"]["invoice_number"]["value"] == (
        "INV-HISTORY-001"
    )
    assert failed_listing_body["latest_effective"]["id"] == second_task_id
    assert failed_listing_body["latest_effective"]["failure"] == {
        "stage": "ai",
        "reason": "retry attempt timed out",
    }
