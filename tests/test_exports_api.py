import csv
from io import StringIO

from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_tasks_api import update_task_row, valid_invoice_payload, valid_task_payload


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


def upload_invoice_material(
    client: TestClient,
    task_id: str,
    *,
    submitter_id: str,
    filename: str,
) -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": submitter_id,
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": (filename, filename.encode(), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["items"][0]["id"]


def create_invoice_with_splits(
    client: TestClient,
    task_id: str,
    *,
    submitter_id: str,
    filename: str,
    invoice_overrides: dict | None = None,
    split_items: list[dict] | None = None,
) -> str:
    material_id = upload_invoice_material(
        client,
        task_id,
        submitter_id=submitter_id,
        filename=filename,
    )
    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=(valid_invoice_payload() | {"actor_id": submitter_id} | (invoice_overrides or {})),
    )
    assert response.status_code == 201
    invoice_id = response.json()["invoice"]["id"]
    response = client.put(
        f"/api/invoices/{invoice_id}/splits",
        json={
            "actor_id": submitter_id,
            "items": split_items or [{"member_id": submitter_id, "amount_cents": 12345}],
        },
    )
    assert response.status_code == 200
    return invoice_id


def confirm_split(
    client: TestClient,
    *,
    split_id: str,
    member_id: str,
) -> None:
    response = client.put(
        f"/api/splits/{split_id}/confirmation",
        json={"actor_id": member_id, "member_id": member_id, "status": "confirmed"},
    )
    assert response.status_code == 200


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
        "reimbursement summary/member details CSV export is available; export jobs and other persisted "
        "artifacts remain placeholders"
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
    assert supported_by_kind["reimbursement_summary"]["implemented"] is True
    assert supported_by_kind["reimbursement_summary"]["implemented_formats"] == ["csv"]
    assert supported_by_kind["member_details"]["formats"] == ["xlsx", "csv"]
    assert supported_by_kind["member_details"]["implemented"] is True
    assert supported_by_kind["member_details"]["implemented_formats"] == ["csv"]
    assert supported_by_kind["finance_draft"]["formats"] == ["xlsx", "json"]
    assert supported_by_kind["merged_pdf"]["formats"] == ["pdf"]
    assert all(
        item["implemented"] is False
        for item in body["supported_exports"]
        if item["kind"] not in {"reimbursement_summary", "member_details"}
    )
    assert all(
        item["implemented_formats"] == []
        for item in body["supported_exports"]
        if item["kind"] not in {"reimbursement_summary", "member_details"}
    )


def test_task_administrator_can_export_reimbursement_summary_csv(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")

    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="railway-a.pdf",
        split_items=[
            {"member_id": "2250001", "amount_cents": 6000},
            {"member_id": "2250002", "amount_cents": 6345},
        ],
    )
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250003",
        filename="registration.pdf",
        invoice_overrides={
            "invoice_number": "INV-002",
            "amount_cents": 20000,
            "expense_type": "registration",
            "seller_name": "比赛平台",
        },
        split_items=[{"member_id": "2250003", "amount_cents": 20000}],
    )
    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="railway-b.pdf",
        invoice_overrides={
            "invoice_number": "INV-003",
            "amount_cents": 1555,
        },
        split_items=[{"member_id": "2250001", "amount_cents": 1555}],
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/reimbursement-summary",
        params={"actor_id": "admin-1", "format": "csv"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="{task_id}-reimbursement-summary.csv"'
    )

    rows = list(csv.DictReader(StringIO(response.text)))
    assert rows == [
        {
            "expense_type": "registration",
            "total_amount_cents": "20000",
            "2250001": "0",
            "2250002": "0",
            "2250003": "20000",
        },
        {
            "expense_type": "railway",
            "total_amount_cents": "13900",
            "2250001": "7555",
            "2250002": "6345",
            "2250003": "0",
        },
        {
            "expense_type": "hotel",
            "total_amount_cents": "0",
            "2250001": "0",
            "2250002": "0",
            "2250003": "0",
        },
        {
            "expense_type": "grand_total",
            "total_amount_cents": "33900",
            "2250001": "7555",
            "2250002": "6345",
            "2250003": "20000",
        },
    ]


def test_task_administrator_can_export_member_details_csv_with_current_split_versions(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="open")

    first_invoice_id = create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250001",
        filename="railway-a.pdf",
        split_items=[
            {"member_id": "2250001", "amount_cents": 6000, "note": "initial-self"},
            {"member_id": "2250002", "amount_cents": 6345, "note": "initial-shared"},
        ],
    )
    initial_splits = client.get(f"/api/invoices/{first_invoice_id}/splits")
    assert initial_splits.status_code == 200
    split_ids = {item["member_id"]: item["id"] for item in initial_splits.json()["items"]}
    confirm_split(client, split_id=split_ids["2250001"], member_id="2250001")
    confirm_split(client, split_id=split_ids["2250002"], member_id="2250002")

    replace_response = client.put(
        f"/api/invoices/{first_invoice_id}/splits",
        json={
            "actor_id": "admin-1",
            "items": [
                {"member_id": "2250001", "amount_cents": 6100, "note": "final-self"},
                {"member_id": "2250002", "amount_cents": 6245, "note": "final-shared"},
            ],
        },
    )
    assert replace_response.status_code == 200

    create_invoice_with_splits(
        client,
        task_id,
        submitter_id="2250003",
        filename="registration.pdf",
        invoice_overrides={
            "invoice_number": "INV-002",
            "amount_cents": 20000,
            "expense_type": "registration",
            "seller_name": "比赛平台",
        },
        split_items=[
            {"member_id": "2250002", "amount_cents": 10000},
            {"member_id": "2250003", "amount_cents": 10000},
        ],
    )
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/member-details",
        params={"actor_id": "admin-1", "format": "csv"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="{task_id}-member-details.csv"'
    )

    rows = list(csv.DictReader(StringIO(response.text)))
    assert rows == [
        {
            "member_id": "2250001",
            "expense_type": "railway",
            "invoice_number": "INV-001",
            "invoice_amount_cents": "12345",
            "split_amount_cents": "6100",
            "split_version": "2",
            "confirmation_status": "pending",
            "split_note": "final-self",
        },
        {
            "member_id": "2250002",
            "expense_type": "railway",
            "invoice_number": "INV-001",
            "invoice_amount_cents": "12345",
            "split_amount_cents": "6245",
            "split_version": "2",
            "confirmation_status": "pending",
            "split_note": "final-shared",
        },
        {
            "member_id": "2250002",
            "expense_type": "registration",
            "invoice_number": "INV-002",
            "invoice_amount_cents": "20000",
            "split_amount_cents": "10000",
            "split_version": "1",
            "confirmation_status": "",
            "split_note": "",
        },
        {
            "member_id": "2250003",
            "expense_type": "registration",
            "invoice_number": "INV-002",
            "invoice_amount_cents": "20000",
            "split_amount_cents": "10000",
            "split_version": "1",
            "confirmation_status": "",
            "split_note": "",
        },
        {
            "member_id": "grand_total",
            "expense_type": "",
            "invoice_number": "",
            "invoice_amount_cents": "",
            "split_amount_cents": "32345",
            "split_version": "",
            "confirmation_status": "",
            "split_note": "",
        },
    ]


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


def test_non_administrator_cannot_export_reimbursement_summary(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)
    update_task_row(tmp_path, task_id, status="ready_to_export")

    response = client.get(
        f"/api/tasks/{task_id}/exports/reimbursement-summary",
        params={"actor_id": "2250001", "format": "csv"},
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
