from datetime import UTC, datetime

from fastapi.testclient import TestClient

from trms_backend.domain.global_invoice_config import GlobalInvoiceConfig
from trms_backend.main import create_app


def make_client(tmp_path, global_invoice_config: GlobalInvoiceConfig | None = None):
    return TestClient(create_app(f"sqlite:///{tmp_path}/test.db", global_invoice_config))


def valid_task_payload():
    return {
        "competition_name": "ICPC Asia Regional",
        "competition_location": "Shanghai",
        "competition_start_date": "2026-11-01",
        "competition_end_date": "2026-11-03",
        "deadline": "2026-12-01T00:00:00Z",
        "member_ids": ["2250001", "2250002", "2250003"],
        "fee_categories": ["registration", "railway", "hotel"],
        "administrator_id": "admin-1",
        "project_info": "ACM competition project",
        "reimburser_info": "Lab reimbursement owner",
        "invoice_title": "同济大学",
        "tax_number": "12100000425006117D",
    }


def test_health_check(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_get_task(tmp_path):
    client = make_client(tmp_path)

    created = client.post("/api/tasks", json=valid_task_payload())

    assert created.status_code == 201
    body = created.json()
    assert body["id"]
    assert body["status"] == "draft"
    assert body["competition_name"] == "ICPC Asia Regional"
    assert body["invoice_title"] == "同济大学"

    fetched = client.get(f"/api/tasks/{body['id']}")

    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_create_task_inherits_global_invoice_config(tmp_path):
    client = make_client(
        tmp_path,
        GlobalInvoiceConfig(
            invoice_title="同济大学电子与信息工程学院",
            tax_number="GLOBAL-TAX-NUMBER",
        ),
    )
    payload = valid_task_payload()
    payload.pop("invoice_title")
    payload.pop("tax_number")

    response = client.post("/api/tasks", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["invoice_title"] == "同济大学电子与信息工程学院"
    assert body["tax_number"] == "GLOBAL-TAX-NUMBER"


def test_create_task_allows_task_level_invoice_override(tmp_path):
    client = make_client(
        tmp_path,
        GlobalInvoiceConfig(
            invoice_title="默认抬头",
            tax_number="DEFAULT-TAX",
        ),
    )
    payload = valid_task_payload() | {
        "invoice_title": "比赛专用抬头",
        "tax_number": "TASK-TAX-NUMBER",
    }

    response = client.post("/api/tasks", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["invoice_title"] == "比赛专用抬头"
    assert body["tax_number"] == "TASK-TAX-NUMBER"


def test_create_task_rejects_missing_invoice_config_without_global_default(tmp_path):
    client = make_client(tmp_path)
    payload = valid_task_payload()
    payload.pop("invoice_title")
    payload.pop("tax_number")

    response = client.post("/api/tasks", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "missing invoice configuration fields: invoice_title, tax_number"
    )


def test_list_tasks_returns_created_tasks(tmp_path):
    client = make_client(tmp_path)
    first = valid_task_payload()
    second = valid_task_payload() | {"competition_name": "CCPC Final"}

    client.post("/api/tasks", json=first)
    client.post("/api/tasks", json=second)

    response = client.get("/api/tasks")

    assert response.status_code == 200
    assert [task["competition_name"] for task in response.json()] == [
        "ICPC Asia Regional",
        "CCPC Final",
    ]


def test_rejects_empty_member_list(tmp_path):
    client = make_client(tmp_path)
    payload = valid_task_payload() | {"member_ids": []}

    response = client.post("/api/tasks", json=payload)

    assert response.status_code == 422


def test_rejects_end_date_before_start_date(tmp_path):
    client = make_client(tmp_path)
    payload = valid_task_payload() | {
        "competition_start_date": "2026-11-03",
        "competition_end_date": "2026-11-01",
    }

    response = client.post("/api/tasks", json=payload)

    assert response.status_code == 422


def test_rejects_past_deadline(tmp_path):
    client = make_client(tmp_path)
    past_deadline = datetime(2025, 1, 1, tzinfo=UTC).isoformat()
    payload = valid_task_payload() | {"deadline": past_deadline}

    response = client.post("/api/tasks", json=payload)

    assert response.status_code == 422


def test_get_missing_task_returns_404(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/tasks/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"


def test_update_task_status_allows_valid_transition(tmp_path):
    client = make_client(tmp_path)
    created = client.post("/api/tasks", json=valid_task_payload()).json()

    response = client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "open"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "open"


def test_update_task_status_rejects_invalid_transition(tmp_path):
    client = make_client(tmp_path)
    created = client.post("/api/tasks", json=valid_task_payload()).json()

    response = client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "completed"},
    )

    assert response.status_code == 409
    assert "cannot transition task" in response.json()["detail"]


def test_update_missing_task_status_returns_404(tmp_path):
    client = make_client(tmp_path)

    response = client.patch(
        "/api/tasks/missing/status",
        json={"target_status": "open"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"


def test_task_persists_across_app_instances(tmp_path):
    database_url = f"sqlite:///{tmp_path}/test.db"
    first_client = TestClient(create_app(database_url))
    task = first_client.post("/api/tasks", json=valid_task_payload()).json()

    second_client = TestClient(create_app(database_url))
    response = second_client.get(f"/api/tasks/{task['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == task["id"]
