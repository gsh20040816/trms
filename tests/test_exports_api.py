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


def create_export_job(
    client: TestClient,
    task_id: str,
    *,
    kind: str = "reimbursement_summary",
    format: str = "xlsx",
    parameters: dict | None = None,
) -> dict:
    response = client.post(
        f"/api/tasks/{task_id}/exports",
        json={
            "actor_id": "admin-1",
            "kind": kind,
            "format": format,
            "parameters": parameters or {},
        },
    )
    assert response.status_code == 201
    return response.json()


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


def test_create_and_list_export_jobs_persist_requested_parameters(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")

    created = create_export_job(
        client,
        task_id,
        parameters={"include_member_breakdown": True, "locale": "zh-CN"},
    )

    assert created["task_id"] == task_id
    assert created["requested_by"] == "admin-1"
    assert created["kind"] == "reimbursement_summary"
    assert created["format"] == "xlsx"
    assert created["status"] == "pending"
    assert created["parameters"] == {
        "include_member_breakdown": True,
        "locale": "zh-CN",
    }
    assert created["failure_reason"] is None
    assert created["created_at"]
    assert created["updated_at"]
    assert created["started_at"] is None
    assert created["finished_at"] is None

    listed = client.get(
        f"/api/tasks/{task_id}/exports",
        params={"actor_id": "admin-1"},
    )

    assert listed.status_code == 200
    assert listed.json() == [created]


def test_export_job_status_transitions_cover_running_succeeded_and_failed(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")

    first_job = create_export_job(client, task_id)

    running = client.patch(
        f"/api/tasks/exports/{first_job['id']}/status",
        json={"actor_id": "admin-1", "target_status": "running"},
    )
    assert running.status_code == 200
    assert running.json()["status"] == "running"
    assert running.json()["started_at"] is not None
    assert running.json()["finished_at"] is None

    succeeded = client.patch(
        f"/api/tasks/exports/{first_job['id']}/status",
        json={"actor_id": "admin-1", "target_status": "succeeded"},
    )
    assert succeeded.status_code == 200
    assert succeeded.json()["status"] == "succeeded"
    assert succeeded.json()["started_at"] is not None
    assert succeeded.json()["finished_at"] is not None
    assert succeeded.json()["failure_reason"] is None

    second_job = create_export_job(
        client,
        task_id,
        kind="merged_pdf",
        format="pdf",
    )
    failed = client.patch(
        f"/api/tasks/exports/{second_job['id']}/status",
        json={
            "actor_id": "admin-1",
            "target_status": "failed",
            "failure_reason": "failed to read encrypted material PDF",
        },
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    assert failed.json()["failure_reason"] == "failed to read encrypted material PDF"
    assert failed.json()["finished_at"] is not None


def test_create_export_job_requires_ready_to_export_or_completed_task(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="reviewing")

    response = client.post(
        f"/api/tasks/{task_id}/exports",
        json={
            "actor_id": "admin-1",
            "kind": "reimbursement_summary",
            "format": "xlsx",
            "parameters": {},
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "task is not ready for export: "
        "task must be ready_to_export or completed before real exports can be generated"
    )


def test_non_administrator_cannot_manage_export_jobs(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")
    export_job = create_export_job(client, task_id)

    create_response = client.post(
        f"/api/tasks/{task_id}/exports",
        json={
            "actor_id": "2250001",
            "kind": "reimbursement_summary",
            "format": "xlsx",
            "parameters": {},
        },
    )
    assert create_response.status_code == 403
    assert create_response.json()["detail"] == (
        "actor is not allowed to manage exports for this task"
    )

    list_response = client.get(
        f"/api/tasks/{task_id}/exports",
        params={"actor_id": "2250001"},
    )
    assert list_response.status_code == 403
    assert list_response.json()["detail"] == (
        "actor is not allowed to manage exports for this task"
    )

    update_response = client.patch(
        f"/api/tasks/exports/{export_job['id']}/status",
        json={"actor_id": "2250001", "target_status": "running"},
    )
    assert update_response.status_code == 403
    assert update_response.json()["detail"] == (
        "actor is not allowed to manage exports for this task"
    )
