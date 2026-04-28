from fastapi.testclient import TestClient

from trms_backend.application.metrics import InMemoryMetricsCollector
from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_invoices_api import valid_invoice_payload
from test_tasks_api import admin_auth_headers, update_task_row, valid_task_payload


def make_client(tmp_path, metrics_collector: InMemoryMetricsCollector) -> TestClient:
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
            metrics_collector=metrics_collector,
        )
    )


def test_metrics_collector_tracks_upload_validation_and_export_boundaries(tmp_path):
    metrics_collector = InMemoryMetricsCollector()
    client = make_client(tmp_path, metrics_collector)

    task_response = client.post("/api/tasks", json=valid_task_payload())
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]
    client.patch(
        f"/api/tasks/{task_id}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )

    upload_response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"invoice-content", "application/pdf")},
    )
    assert upload_response.status_code == 201
    material_id = upload_response.json()["items"][0]["id"]

    invoice_response = client.post(
        f"/api/materials/{material_id}/invoice",
        json=valid_invoice_payload()
        | {
            "buyer_name": "错误抬头",
            "tax_number": "INVALID-TAX",
        },
    )
    assert invoice_response.status_code == 201

    update_task_row(tmp_path, task_id, status="ready_to_export")

    export_response = client.post(
        f"/api/tasks/{task_id}/exports",
        json={
            "actor_id": "admin-1",
            "kind": "reimbursement_summary",
            "format": "csv",
            "parameters": {},
        },
        headers=admin_auth_headers(client),
    )
    assert export_response.status_code == 201

    snapshot = metrics_collector.snapshot()
    assert snapshot["uploads"]["total"] == 1
    assert snapshot["uploads"]["success_rate"] == 1.0
    assert snapshot["recognition_tasks"]["by_status"] == {"pending": 1}
    assert snapshot["validation_results"]["failed_rule_counts"] == {
        "invoice_tax_number_match": 1,
        "invoice_title_match": 1,
    }
    assert snapshot["export_jobs"]["by_status"] == {"pending": 1}
    assert snapshot["export_jobs"]["by_kind"] == {
        "reimbursement_summary": {"pending": 1}
    }
