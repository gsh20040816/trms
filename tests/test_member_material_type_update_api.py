from fastapi.testclient import TestClient

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from api_error_assertions import assert_api_error
from test_tasks_api import (
    auth_headers,
    create_invoice,
    create_task,
    move_open_task_to_reviewing,
    open_task,
    register_and_get_token,
)


def make_client(tmp_path) -> TestClient:
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def register_member_token(client: TestClient, *, username: str, actor_id: str) -> str:
    return register_and_get_token(
        client,
        username=username,
        role="member",
        actor_id=actor_id,
        member_code=actor_id,
    )


def upload_material(
    client: TestClient,
    *,
    task_id: str,
    access_token: str,
    material_type: str,
    filename: str,
) -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        headers=auth_headers(access_token),
        data={
            "channel": "web",
            "material_type": material_type,
        },
        files={"files": (filename, b"fake-pdf-content", "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["items"][0]["id"]


def test_member_can_update_own_material_type(tmp_path):
    client = make_client(tmp_path)
    member_token = register_member_token(client, username="member1", actor_id="2250001")
    task_id = create_task(client)["id"]
    open_task(client, task_id)
    material_id = upload_material(
        client,
        task_id=task_id,
        access_token=member_token,
        material_type="other_attachment",
        filename="payment.pdf",
    )

    response = client.patch(
        f"/api/materials/{material_id}/material-type",
        headers=auth_headers(member_token),
        json={"material_type": "payment_record"},
    )

    assert response.status_code == 200
    assert response.json()["item"]["id"] == material_id
    assert response.json()["item"]["material_type"] == "payment_record"


def test_member_material_type_update_rejects_unrelated_member(tmp_path):
    client = make_client(tmp_path)
    owner_token = register_member_token(client, username="owner", actor_id="2250001")
    outsider_token = register_member_token(client, username="outsider", actor_id="2250002")
    task_id = create_task(client)["id"]
    open_task(client, task_id)
    material_id = upload_material(
        client,
        task_id=task_id,
        access_token=owner_token,
        material_type="other_attachment",
        filename="proof.pdf",
    )

    response = client.patch(
        f"/api/materials/{material_id}/material-type",
        headers=auth_headers(outsider_token),
        json={"material_type": "payment_record"},
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="only the material submitter can update material type",
    )


def test_member_material_type_update_rejects_invalid_type(tmp_path):
    client = make_client(tmp_path)
    member_token = register_member_token(client, username="member1", actor_id="2250001")
    task_id = create_task(client)["id"]
    open_task(client, task_id)
    material_id = upload_material(
        client,
        task_id=task_id,
        access_token=member_token,
        material_type="other_attachment",
        filename="proof.pdf",
    )

    response = client.patch(
        f"/api/materials/{material_id}/material-type",
        headers=auth_headers(member_token),
        json={"material_type": "receipt"},
    )

    assert_api_error(
        response,
        status_code=422,
        code="validation_error",
    )


def test_member_material_type_update_rejects_non_open_task(tmp_path):
    client = make_client(tmp_path)
    member_token = register_member_token(client, username="member1", actor_id="2250001")
    task_id = create_task(client)["id"]
    open_task(client, task_id)
    material_id = upload_material(
        client,
        task_id=task_id,
        access_token=member_token,
        material_type="other_attachment",
        filename="proof.pdf",
    )
    move_open_task_to_reviewing(client, task_id)

    response = client.patch(
        f"/api/materials/{material_id}/material-type",
        headers=auth_headers(member_token),
        json={"material_type": "payment_record"},
    )

    assert_api_error(
        response,
        status_code=409,
        code="conflict",
        detail="members can only update material type while the task is open",
    )


def test_member_material_type_update_refreshes_invoice_validations(tmp_path):
    client = make_client(tmp_path)
    member_token = register_member_token(client, username="member1", actor_id="2250001")
    task_id = create_task(client)["id"]
    open_task(client, task_id)

    invoice_material_id = upload_material(
        client,
        task_id=task_id,
        access_token=member_token,
        material_type="invoice",
        filename="invoice.pdf",
    )
    invoice_id = create_invoice(client, invoice_material_id, amount_cents=123456)
    supporting_material_id = upload_material(
        client,
        task_id=task_id,
        access_token=member_token,
        material_type="other_attachment",
        filename="payment.pdf",
    )
    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}",
        headers=auth_headers(member_token),
    )
    assert attach_response.status_code == 200

    before_response = client.get(
        f"/api/invoices/{invoice_id}/validations",
        headers=auth_headers(member_token),
    )
    assert before_response.status_code == 200
    before_payment_record_validation = next(
        item
        for item in before_response.json()["items"]
        if item["rule_code"] == "invoice_payment_record_required"
    )
    assert before_payment_record_validation["status"] == "failed"

    update_response = client.patch(
        f"/api/materials/{supporting_material_id}/material-type",
        headers=auth_headers(member_token),
        json={"material_type": "payment_record"},
    )
    assert update_response.status_code == 200

    after_response = client.get(
        f"/api/invoices/{invoice_id}/validations",
        headers=auth_headers(member_token),
    )
    assert after_response.status_code == 200
    after_payment_record_validation = next(
        item
        for item in after_response.json()["items"]
        if item["rule_code"] == "invoice_payment_record_required"
    )
    payment_amount_validation = next(
        item
        for item in after_response.json()["items"]
        if item["rule_code"] == "invoice_payment_record_amount_match"
    )
    assert after_payment_record_validation["status"] == "passed"
    assert after_payment_record_validation["evidence"]["payment_record_material_ids"] == [
        supporting_material_id
    ]
    assert payment_amount_validation["status"] == "pending"
