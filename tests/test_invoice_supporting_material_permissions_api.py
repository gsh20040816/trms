from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app
from trms_backend.runtime_config import load_runtime_config

from test_tasks_api import (
    admin_auth_headers,
    auth_headers,
    create_task,
    register_and_get_token,
    valid_task_payload,
)


def make_client(tmp_path):
    runtime_config = load_runtime_config(
        environment="test",
        database_url=f"sqlite:///{tmp_path}/test.db",
        material_storage_dir=tmp_path / "material-storage",
        cors_allowed_origins="http://127.0.0.1:5173",
        public_api_base_url="http://127.0.0.1:8000/api",
        api_host="127.0.0.1",
        api_port=8000,
        async_job_mode="worker",
    )
    return TestClient(
        create_app(
            runtime_config=runtime_config,
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def member_auth_headers(client: TestClient, *, username: str, actor_id: str) -> dict[str, str]:
    return auth_headers(
        register_and_get_token(
            client,
            username=username,
            role="member",
            actor_id=actor_id,
            member_code=actor_id,
        )
    )


def create_open_task(client: TestClient, *, member_ids: list[str] | None = None) -> str:
    task = create_task(
        client,
        payload=valid_task_payload()
        | {"member_ids": member_ids or ["2250001", "2250002", "2250003"]},
    )
    response = client.patch(
        f"/api/tasks/{task['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    assert response.status_code == 200
    return task["id"]


def upload_material(
    client: TestClient,
    task_id: str,
    *,
    submitter_id: str,
    material_type: str,
    filename: str,
    content_type: str = "application/pdf",
) -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": submitter_id,
            "channel": "web",
            "material_type": material_type,
        },
        files={"files": (filename, filename.encode(), content_type)},
    )
    assert response.status_code == 201
    return response.json()["items"][0]["id"]


def create_invoice(
    client: TestClient,
    material_id: str,
    *,
    actor_id: str,
    invoice_number: str,
) -> str:
    response = client.post(
        f"/api/materials/{material_id}/invoice",
        json={
            "actor_id": actor_id,
            "invoice_number": invoice_number,
            "issue_date": "2026-11-04",
            "transaction_time": "2026-11-01T08:00:00Z",
            "buyer_name": "同济大学",
            "tax_number": "12100000425006117D",
            "seller_name": "服务商",
            "amount_cents": 12345,
            "expense_type": "railway",
        },
    )
    assert response.status_code == 201
    return response.json()["invoice"]["id"]


def test_member_bearer_can_attach_and_detach_own_supporting_material(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    member_headers = member_auth_headers(client, username="member1", actor_id="2250001")

    invoice_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="invoice.pdf",
    )
    supporting_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="payment_record",
        filename="payment.png",
        content_type="image/png",
    )
    invoice_id = create_invoice(
        client,
        invoice_material_id,
        actor_id="2250001",
        invoice_number="INV-001",
    )

    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}",
        headers=member_headers,
    )
    assert attach_response.status_code == 200

    listed_response = client.get(
        f"/api/invoices/{invoice_id}/supporting-materials",
        headers=member_headers,
    )
    assert listed_response.status_code == 200
    assert [item["id"] for item in listed_response.json()["items"]] == [supporting_material_id]

    detach_response = client.delete(
        f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}",
        headers=member_headers,
    )
    assert detach_response.status_code == 200
    assert detach_response.json()["status"] == "deleted"


def test_anonymous_supporting_material_write_requests_require_bearer_token(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    member_headers = member_auth_headers(client, username="member1", actor_id="2250001")

    invoice_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="invoice.pdf",
    )
    supporting_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="payment_record",
        filename="payment.png",
        content_type="image/png",
    )
    invoice_id = create_invoice(
        client,
        invoice_material_id,
        actor_id="2250001",
        invoice_number="INV-001",
    )

    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}"
    )
    assert attach_response.status_code == 401
    assert attach_response.json()["detail"] == "invalid or missing bearer token"

    assert (
        client.put(
            f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}",
            headers=member_headers,
        ).status_code
        == 200
    )
    detach_response = client.delete(
        f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}"
    )
    assert detach_response.status_code == 401
    assert detach_response.json()["detail"] == "invalid or missing bearer token"


def test_unrelated_member_cannot_attach_or_detach_other_members_supporting_materials(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    owner_headers = member_auth_headers(client, username="member1", actor_id="2250001")
    other_member_headers = member_auth_headers(client, username="member2", actor_id="2250002")

    invoice_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="invoice.pdf",
    )
    supporting_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="payment_record",
        filename="payment.png",
        content_type="image/png",
    )
    invoice_id = create_invoice(
        client,
        invoice_material_id,
        actor_id="2250001",
        invoice_number="INV-001",
    )

    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}",
        headers=other_member_headers,
    )
    assert attach_response.status_code == 403
    assert attach_response.json()["detail"] == (
        "actor is not allowed to manage supporting materials for this task"
    )

    assert (
        client.put(
            f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}",
            headers=owner_headers,
        ).status_code
        == 200
    )
    detach_response = client.delete(
        f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}",
        headers=other_member_headers,
    )
    assert detach_response.status_code == 403
    assert detach_response.json()["detail"] == (
        "actor is not allowed to manage supporting materials for this task"
    )


def test_member_cannot_attach_supporting_material_from_another_task(tmp_path):
    client = make_client(tmp_path)
    first_task_id = create_open_task(client)
    second_task_id = create_open_task(client)
    member_headers = member_auth_headers(client, username="member1", actor_id="2250001")

    invoice_material_id = upload_material(
        client,
        first_task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="invoice.pdf",
    )
    cross_task_supporting_material_id = upload_material(
        client,
        second_task_id,
        submitter_id="2250001",
        material_type="payment_record",
        filename="payment.png",
        content_type="image/png",
    )
    invoice_id = create_invoice(
        client,
        invoice_material_id,
        actor_id="2250001",
        invoice_number="INV-001",
    )

    response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{cross_task_supporting_material_id}",
        headers=member_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "supporting material belongs to a different task"


def test_task_administrator_can_attach_and_detach_any_task_member_supporting_material(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    admin_headers = admin_auth_headers(client)

    invoice_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250001",
        material_type="invoice",
        filename="invoice.pdf",
    )
    supporting_material_id = upload_material(
        client,
        task_id,
        submitter_id="2250002",
        material_type="payment_record",
        filename="payment.png",
        content_type="image/png",
    )
    invoice_id = create_invoice(
        client,
        invoice_material_id,
        actor_id="2250001",
        invoice_number="INV-001",
    )

    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}",
        headers=admin_headers,
    )
    assert attach_response.status_code == 200

    detach_response = client.delete(
        f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}",
        headers=admin_headers,
    )
    assert detach_response.status_code == 200
    assert detach_response.json()["status"] == "deleted"
