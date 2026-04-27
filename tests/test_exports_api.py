from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_tasks_api import update_task_row, valid_task_payload


def make_client(tmp_path):
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def create_task(client: TestClient) -> str:
    response = client.post("/api/tasks", json=valid_task_payload())
    assert response.status_code == 201
    return response.json()["id"]


def test_task_administrator_can_get_export_capabilities_when_task_is_ready(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/capabilities",
        params={"actor_id": "admin-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["administrator_id"] == "admin-1"
    assert body["current_task_status"] == "ready_to_export"
    assert body["export_allowed"] is True
    assert body["blocking_reasons"] == []
    assert body["execution_mode"] == "async_placeholder"
    assert body["note"] == (
        "export module boundary is established; real export jobs and files are not "
        "generated yet"
    )
    supported_by_kind = {item["kind"]: item for item in body["supported_exports"]}
    assert set(supported_by_kind) == {
        "reimbursement_summary",
        "member_details",
        "invoice_details",
        "missing_materials",
        "finance_draft",
        "merged_pdf",
    }
    assert supported_by_kind["reimbursement_summary"]["formats"] == ["xlsx", "csv"]
    assert supported_by_kind["finance_draft"]["formats"] == ["xlsx", "json"]
    assert supported_by_kind["merged_pdf"]["formats"] == ["pdf"]
    assert all(item["implemented"] is False for item in body["supported_exports"])


def test_export_capabilities_report_blocking_reason_before_final_confirmation(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="reviewing")

    response = client.get(
        f"/api/tasks/{task_id}/exports/capabilities",
        params={"actor_id": "admin-1"},
    )

    assert response.status_code == 200
    assert response.json()["export_allowed"] is False
    assert response.json()["blocking_reasons"] == [
        "task must be ready_to_export or completed before real exports can be generated"
    ]


def test_non_administrator_cannot_get_export_capabilities(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)

    response = client.get(
        f"/api/tasks/{task_id}/exports/capabilities",
        params={"actor_id": "2250001"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "actor is not allowed to manage exports for this task"
