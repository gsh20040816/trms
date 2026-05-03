from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from trms_backend.domain.audit_logs import AuditLogResult
from trms_backend.domain.materials import MaterialStatus
from trms_backend.infrastructure.database import build_session_factory
from trms_backend.infrastructure.repositories import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyInvoiceRepository,
    SqlAlchemyMaterialRepository,
)
from trms_backend.domain.materials import MAX_MATERIAL_UPLOAD_SIZE_BYTES
from trms_backend.domain.tasks import (
    ReimbursementTask,
    TaskSubmissionDeadlinePassedError,
    ensure_task_accepts_member_submission,
)
from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from api_error_assertions import assert_api_error
from test_tasks_api import (
    admin_auth_headers,
    auth_headers,
    create_task,
    create_invoice,
    register_and_get_token,
    update_task_row,
)


def make_client(tmp_path):
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def create_open_task(client: TestClient) -> str:
    created = create_task(client)
    client.patch(
        f"/api/tasks/{created['id']}/status",
        json={"target_status": "open"},
        headers=admin_auth_headers(client),
    )
    return created["id"]


def list_material_audit_logs(tmp_path, material_id: str):
    repository = SqlAlchemyAuditLogRepository(
        build_session_factory(f"sqlite:///{tmp_path}/test.db")
    )
    return repository.list_by_object(object_type="material", object_id=material_id)


def get_material_record(tmp_path, material_id: str):
    repository = SqlAlchemyMaterialRepository(
        build_session_factory(f"sqlite:///{tmp_path}/test.db")
    )
    return repository.get(material_id)


def list_linked_invoice_ids_for_supporting_material(tmp_path, material_id: str) -> list[str]:
    repository = SqlAlchemyInvoiceRepository(
        build_session_factory(f"sqlite:///{tmp_path}/test.db")
    )
    return [invoice.id for invoice in repository.list_by_supporting_material(material_id)]


def assert_single_completed_recognition_task(client: TestClient, material_id: str) -> None:
    response = client.get(f"/api/materials/{material_id}/recognition-tasks")

    assert response.status_code == 200
    body = response.json()
    items = body["items"]
    assert len(items) == 1
    assert items[0]["material_id"] == material_id
    assert items[0]["status"] in {"failed", "needs_confirmation", "succeeded"}
    assert body["latest_effective"]["id"] == items[0]["id"]
    assert items[0]["is_final_fact"] is False
    assert items[0]["recognized_fields"] == {}


def test_submit_material_to_open_task(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )

    assert response.status_code == 201
    material = response.json()["items"][0]
    assert material["status"] == "assigned"
    assert material["task_id"] == task_id
    assert material["submitter_id"] == "2250001"
    assert material["task_id_hint"] is None
    assert material["submitter_id_hint"] is None
    assert material["channel"] == "web"
    assert material["material_type"] == "invoice"
    assert material["storage_key"].startswith(f"{task_id}/")
    assert material["original_filename"] == "ticket.pdf"
    assert material["size_bytes"] == len(b"fake-pdf-content")
    assert material["duplicate_of"] is None
    assert response.json()["recognition_dispatch"]["status"] == "executed"
    assert_single_completed_recognition_task(client, material["id"])

    audit_logs = list_material_audit_logs(tmp_path, material["id"])
    assert len(audit_logs) == 1
    assert audit_logs[0].actor_id == "2250001"
    assert audit_logs[0].action == "submit_material"
    assert audit_logs[0].result is AuditLogResult.SUCCEEDED
    assert audit_logs[0].task_id == task_id
    assert audit_logs[0].request_id.startswith("req_")
    assert audit_logs[0].detail == {
        "status": "assigned",
        "channel": "web",
        "material_type": "invoice",
        "task_id": task_id,
        "submitter_id": "2250001",
        "task_id_hint": None,
        "submitter_id_hint": None,
        "original_filename": "ticket.pdf",
        "duplicate_of": None,
    }


def test_submit_material_defaults_material_type_when_client_omits_it(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )

    assert response.status_code == 201
    material = response.json()["items"][0]
    assert material["material_type"] == "other_attachment"
    assert response.json()["recognition_dispatch"]["status"] == "executed"

    audit_logs = list_material_audit_logs(tmp_path, material["id"])
    assert len(audit_logs) == 1
    assert audit_logs[0].detail["material_type"] == "other_attachment"


def test_submit_supporting_material_does_not_auto_link_before_recognized_amount_is_available(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    invoice_material_id = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    ).json()["items"][0]["id"]
    invoice_id = create_invoice(client, invoice_material_id)

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "payment_record",
        },
        files={"files": ("payment.png", b"payment-proof", "image/png")},
    )

    assert response.status_code == 201
    supporting_material_id = response.json()["items"][0]["id"]
    assert list_linked_invoice_ids_for_supporting_material(tmp_path, supporting_material_id) == []


def test_default_material_type_does_not_auto_link_before_recognition(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    invoice_material_id = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    ).json()["items"][0]["id"]
    create_invoice(client, invoice_material_id)

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
        },
        files={"files": ("unclassified.pdf", b"fake-pdf-content", "application/pdf")},
    )

    assert response.status_code == 201
    material_id = response.json()["items"][0]["id"]
    assert response.json()["items"][0]["material_type"] == "other_attachment"
    assert list_linked_invoice_ids_for_supporting_material(tmp_path, material_id) == []


def test_supporting_material_with_recognized_amount_only_auto_links_when_same_amount_invoice_is_unique(
    tmp_path,
):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    supporting_response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "competition_notice",
        },
        files={"files": ("50thICPC邀请函（武汉）.pdf", b"competition-notice", "application/pdf")},
    )
    assert supporting_response.status_code == 201
    supporting_material_id = supporting_response.json()["items"][0]["id"]

    invoice_material_one = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ride-1.pdf", b"ride-invoice-1", "application/pdf")},
    ).json()["items"][0]["id"]
    create_invoice(
        client,
        invoice_material_one,
        amount_cents=12345,
        expense_type="railway",
    )

    assert list_linked_invoice_ids_for_supporting_material(tmp_path, supporting_material_id) == []

    invoice_material_two = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ride-2.pdf", b"ride-invoice-2", "application/pdf")},
    ).json()["items"][0]["id"]
    create_invoice(
        client,
        invoice_material_two,
        amount_cents=8800,
        expense_type="railway",
    )

    assert list_linked_invoice_ids_for_supporting_material(tmp_path, supporting_material_id) == []


def test_submit_pending_assignment_material_without_resolved_identity(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/materials/pending-assignment",
        data={
            "channel": "telegram",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )

    assert response.status_code == 201
    material = response.json()["items"][0]
    assert material["status"] == "pending_assignment"
    assert material["task_id"] is None
    assert material["submitter_id"] is None
    assert material["task_id_hint"] is None
    assert material["submitter_id_hint"] is None
    assert material["channel"] == "telegram"
    assert material["storage_key"].startswith("_pending_assignment/")
    assert response.json()["recognition_dispatch"]["status"] == "executed"
    assert_single_completed_recognition_task(client, material["id"])


def test_pending_assignment_material_stays_hidden_from_task_material_list(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.post(
        "/api/materials/pending-assignment",
        data={
            "task_id_hint": task_id,
            "submitter_id_hint": "2250999",
            "channel": "email",
            "material_type": "other_attachment",
        },
        files={"files": ("notice.pdf", b"fake-pdf-content", "application/pdf")},
    )

    assert response.status_code == 201
    material = response.json()["items"][0]
    assert material["status"] == "pending_assignment"
    assert material["task_id"] is None
    assert material["submitter_id"] is None
    assert material["task_id_hint"] == task_id
    assert material["submitter_id_hint"] == "2250999"

    listed = client.get(
        f"/api/tasks/{task_id}/materials",
        headers=admin_auth_headers(client),
    )
    assert listed.status_code == 200
    assert listed.json()["items"] == []


def test_administrator_can_preview_assigned_material_content(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    created = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )
    material = created.json()["items"][0]

    response = client.get(
        f"/api/materials/{material['id']}/content",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.content == b"fake-pdf-content"
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"] == 'inline; filename="ticket.pdf"'


def test_administrator_can_preview_assigned_material_content_with_unicode_filename(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    created = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("高德打车电子发票.pdf", b"fake-pdf-content", "application/pdf")},
    )
    material = created.json()["items"][0]

    response = client.get(
        f"/api/materials/{material['id']}/content",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.content == b"fake-pdf-content"
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"] == (
        "inline; filename=\"pdf\"; "
        "filename*=UTF-8''%E9%AB%98%E5%BE%B7%E6%89%93%E8%BD%A6%E7%94%B5%E5%AD%90%E5%8F%91%E7%A5%A8.pdf"
    )


def test_member_cannot_preview_other_members_material_content(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    created = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )
    material_id = created.json()["items"][0]["id"]

    other_member_headers = auth_headers(
        register_and_get_token(
            client,
            username="member2",
            role="member",
            actor_id="2250002",
            member_code="2250002",
        )
    )
    response = client.get(
        f"/api/materials/{material_id}/content",
        headers=other_member_headers,
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to view this material content",
    )


def test_administrator_can_claim_pending_assignment_material(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    created = client.post(
        "/api/materials/pending-assignment",
        data={
            "task_id_hint": task_id,
            "submitter_id_hint": "2250001",
            "channel": "email",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )
    material_id = created.json()["items"][0]["id"]

    response = client.post(
        f"/api/materials/{material_id}/claim",
        data={
            "administrator_id": "admin-1",
            "task_id": task_id,
            "submitter_id": "2250001",
        },
    )

    assert response.status_code == 200
    material = response.json()["item"]
    assert material["status"] == "assigned"
    assert material["task_id"] == task_id
    assert material["submitter_id"] == "2250001"
    assert material["task_id_hint"] == task_id
    assert material["submitter_id_hint"] == "2250001"
    assert material["claimed_by"] == "admin-1"
    assert material["claimed_at"] is not None

    listed = client.get(
        f"/api/tasks/{task_id}/materials",
        headers=admin_auth_headers(client),
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [material_id]

    audit_logs = list_material_audit_logs(tmp_path, material_id)
    assert len(audit_logs) == 2
    assert [item.action for item in audit_logs] == [
        "submit_material",
        "claim_pending_assignment",
    ]
    assert audit_logs[1].actor_id == "admin-1"
    assert audit_logs[1].result is AuditLogResult.SUCCEEDED
    assert audit_logs[1].task_id == task_id
    assert audit_logs[1].request_id.startswith("req_")
    assert audit_logs[1].detail == {
        "task_id": task_id,
        "submitter_id": "2250001",
        "claimed_status": "assigned",
        "task_id_hint": task_id,
        "submitter_id_hint": "2250001",
        "channel": "email",
        "material_type": "invoice",
    }


def test_claim_pending_assignment_material_rejects_non_administrator(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    created = client.post(
        "/api/materials/pending-assignment",
        data={
            "channel": "telegram",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )
    material_id = created.json()["items"][0]["id"]

    response = client.post(
        f"/api/materials/{material_id}/claim",
        data={
            "administrator_id": "2250001",
            "task_id": task_id,
            "submitter_id": "2250001",
        },
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="administrator is not allowed to claim materials for this task",
    )


def test_claim_pending_assignment_material_rejects_assigned_material(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    assigned_material = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    ).json()["items"][0]

    response = client.post(
        f"/api/materials/{assigned_material['id']}/claim",
        data={
            "administrator_id": "admin-1",
            "task_id": task_id,
            "submitter_id": "2250001",
        },
    )

    assert_api_error(
        response,
        status_code=409,
        code="conflict",
        detail="material is not pending assignment",
    )


def test_task_administrator_can_mark_material_deleted_without_removing_file(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    created = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )
    assert created.status_code == 201
    material = created.json()["items"][0]
    storage_path = tmp_path / "material-storage" / material["storage_key"]

    response = client.post(
        f"/api/materials/{material['id']}/deletion-mark",
        json={"administrator_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["item"]["status"] == "deleted"
    listed = client.get(
        f"/api/tasks/{task_id}/materials",
        headers=admin_auth_headers(client),
    )
    assert listed.status_code == 200
    assert listed.json()["items"] == []
    stored = get_material_record(tmp_path, material["id"])
    assert stored is not None
    assert stored.status is MaterialStatus.DELETED
    assert storage_path.read_bytes() == b"fake-pdf-content"

    audit_logs = list_material_audit_logs(tmp_path, material["id"])
    assert len(audit_logs) == 2
    assert [item.action for item in audit_logs] == [
        "submit_material",
        "mark_material_deleted",
    ]
    assert audit_logs[1].actor_id == "admin-1"
    assert audit_logs[1].result is AuditLogResult.SUCCEEDED
    assert audit_logs[1].task_id == task_id
    assert audit_logs[1].request_id.startswith("req_")
    assert audit_logs[1].detail == {
        "deleted_status": "deleted",
        "submitter_id": "2250001",
        "channel": "web",
        "material_type": "invoice",
        "original_filename": "ticket.pdf",
    }


def test_member_cannot_mark_material_deleted(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    material_id = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    ).json()["items"][0]["id"]

    member_headers = auth_headers(
        register_and_get_token(
            client,
            username="member1",
            role="member",
            actor_id="2250001",
            member_code="2250001",
        )
    )
    response = client.post(
        f"/api/materials/{material_id}/deletion-mark",
        json={"administrator_id": "2250001"},
        headers=member_headers,
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail="actor is not allowed to delete materials for this task",
    )

    audit_logs = list_material_audit_logs(tmp_path, material_id)
    assert len(audit_logs) == 2
    assert audit_logs[1].action == "mark_material_deleted"
    assert audit_logs[1].actor_id == "2250001"
    assert audit_logs[1].result is AuditLogResult.REJECTED
    assert audit_logs[1].task_id == task_id
    assert audit_logs[1].detail == {
        "failure_reason": "actor is not allowed to delete materials for this task",
    }


def test_mark_deleted_requires_authenticated_request(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    material_id = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    ).json()["items"][0]["id"]

    response = client.post(
        f"/api/materials/{material_id}/deletion-mark",
        json={"administrator_id": "admin-1"},
    )

    assert_api_error(
        response,
        status_code=401,
        code="unauthorized",
        detail="invalid or missing bearer token",
    )


def test_cannot_mark_primary_invoice_material_deleted(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    material_id = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    ).json()["items"][0]["id"]
    create_invoice(client, material_id)

    response = client.post(
        f"/api/materials/{material_id}/deletion-mark",
        json={"administrator_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert_api_error(
        response,
        status_code=409,
        code="conflict",
        detail="material is referenced by an invoice and cannot be marked deleted",
    )

    audit_logs = list_material_audit_logs(tmp_path, material_id)
    assert len(audit_logs) == 2
    assert audit_logs[1].action == "mark_material_deleted"
    assert audit_logs[1].actor_id == "admin-1"
    assert audit_logs[1].result is AuditLogResult.REJECTED
    assert audit_logs[1].task_id == task_id
    assert audit_logs[1].detail == {
        "failure_reason": "material is referenced by an invoice and cannot be marked deleted",
        "current_status": "assigned",
    }


def test_mark_deleted_rejects_mismatched_authenticated_administrator_id_with_audit(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    material_id = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    ).json()["items"][0]["id"]

    response = client.post(
        f"/api/materials/{material_id}/deletion-mark",
        json={"administrator_id": "admin-2"},
        headers=admin_auth_headers(client),
    )

    assert_api_error(
        response,
        status_code=403,
        code="forbidden",
        detail=(
            "administrator_id does not match the authenticated request identity: "
            "expected 'admin-1', got 'admin-2'"
        ),
    )

    audit_logs = list_material_audit_logs(tmp_path, material_id)
    assert len(audit_logs) == 2
    assert audit_logs[1].action == "mark_material_deleted"
    assert audit_logs[1].actor_id == "admin-1"
    assert audit_logs[1].result is AuditLogResult.REJECTED
    assert audit_logs[1].task_id is None
    assert audit_logs[1].detail == {
        "failure_reason": (
            "administrator_id does not match the authenticated request identity: "
            "expected 'admin-1', got 'admin-2'"
        ),
        "requested_administrator_id": "admin-2",
    }


def test_cannot_mark_supporting_material_deleted_when_linked_to_invoice(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    invoice_material_id = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"invoice-content", "application/pdf")},
    ).json()["items"][0]["id"]
    supporting_material_id = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "payment_record",
        },
        files={"files": ("payment.png", b"payment-content", "image/png")},
    ).json()["items"][0]["id"]
    invoice_id = create_invoice(client, invoice_material_id)
    attach_response = client.put(
        f"/api/invoices/{invoice_id}/supporting-materials/{supporting_material_id}",
        headers=admin_auth_headers(client),
    )
    assert attach_response.status_code == 200

    response = client.post(
        f"/api/materials/{supporting_material_id}/deletion-mark",
        json={"administrator_id": "admin-1"},
        headers=admin_auth_headers(client),
    )

    assert_api_error(
        response,
        status_code=409,
        code="conflict",
        detail="material is referenced by supporting invoice links and cannot be marked deleted",
    )


def test_submit_material_accepts_supported_material_types(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    for material_type, filename, content_type in (
        ("invoice", "ticket.pdf", "application/pdf"),
        ("payment_record", "payment.png", "image/png"),
        ("competition_notice", "notice.pdf", "application/pdf"),
        ("itinerary", "itinerary.pdf", "application/pdf"),
        ("order_screenshot", "order.png", "image/png"),
        ("other_attachment", "other.zip", "application/zip"),
    ):
        response = client.post(
            f"/api/tasks/{task_id}/materials",
            data={
                "submitter_id": "2250001",
                "channel": "web",
                "material_type": material_type,
            },
            files={"files": (filename, material_type.encode(), content_type)},
        )

        assert response.status_code == 201
        assert response.json()["status"] == "success"
        material = response.json()["items"][0]
        assert material["submitter_id"] == "2250001"
        assert material["material_type"] == material_type


def test_submit_material_allows_member_across_all_channels(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    for channel in ("web", "cli", "telegram", "email"):
        response = client.post(
            f"/api/tasks/{task_id}/materials",
            data={
                "submitter_id": "2250001",
                "channel": channel,
                "material_type": "invoice",
            },
            files={"files": (f"{channel}.pdf", channel.encode(), "application/pdf")},
        )

        assert response.status_code == 201
        assert response.json()["status"] == "success"
        material = response.json()["items"][0]
        assert material["submitter_id"] == "2250001"
        assert material["channel"] == channel


def test_submit_material_rejects_non_member_across_all_channels(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    for channel in ("web", "cli", "telegram", "email"):
        response = client.post(
            f"/api/tasks/{task_id}/materials",
            data={
                "submitter_id": "2250999",
                "channel": channel,
                "material_type": "invoice",
            },
            files={"files": (f"{channel}.pdf", channel.encode(), "application/pdf")},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "submitter is not a member of the task: 2250999"


def test_submit_material_rejects_draft_task(tmp_path):
    client = make_client(tmp_path)
    task_id = create_task(client)["id"]

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "task is not open for material submission"


def test_submit_material_marks_duplicate_file_across_channels_in_same_task(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    files = {"files": ("ticket.pdf", b"same-content", "application/pdf")}
    first = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files=files,
    ).json()["items"][0]

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "cli",
            "material_type": "invoice",
        },
        files={"files": ("ticket-copy.pdf", b"same-content", "application/pdf")},
    )

    assert response.status_code == 201
    duplicate = response.json()["items"][0]
    assert first["channel"] == "web"
    assert duplicate["channel"] == "cli"
    assert duplicate["duplicate_of"] == first["id"]


def test_submit_material_returns_partial_success_for_batch_upload(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "cli",
            "material_type": "invoice",
        },
        files=[
            ("files", ("ticket.pdf", b"fake-pdf-content", "application/pdf")),
            ("files", ("notes.txt", b"plain-text", "text/plain")),
        ],
    )

    assert response.status_code == 207
    payload = response.json()
    assert payload["status"] == "partial_success"
    assert [item["original_filename"] for item in payload["items"]] == ["ticket.pdf"]
    assert payload["failures"] == [
        {
            "original_filename": "notes.txt",
            "error_code": "unsupported_content_type",
            "detail": (
                "unsupported material content type: text/plain; supported content types: "
                "application/pdf, application/zip, image/jpeg, image/png, image/webp"
            ),
        }
    ]

    listed = client.get(
        f"/api/tasks/{task_id}/materials",
        headers=admin_auth_headers(client),
    )
    assert listed.status_code == 200
    assert [item["original_filename"] for item in listed.json()["items"]] == ["ticket.pdf"]


def test_submit_material_returns_failed_batch_result_when_all_files_fail(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "cli",
            "material_type": "invoice",
        },
        files=[
            ("files", ("   ", b"fake-pdf-content", "application/pdf")),
            ("files", ("notes.txt", b"plain-text", "text/plain")),
        ],
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["items"] == []
    assert payload["failures"] == [
        {
            "original_filename": "   ",
            "error_code": "missing_filename",
            "detail": "uploaded file must have a filename",
        },
        {
            "original_filename": "notes.txt",
            "error_code": "unsupported_content_type",
            "detail": (
                "unsupported material content type: text/plain; supported content types: "
                "application/pdf, application/zip, image/jpeg, image/png, image/webp"
            ),
        },
    ]

    listed = client.get(
        f"/api/tasks/{task_id}/materials",
        headers=admin_auth_headers(client),
    )
    assert listed.status_code == 200
    assert listed.json()["items"] == []


def test_submit_material_rejects_task_after_deadline(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    update_task_row(
        tmp_path,
        task_id,
        deadline=datetime.now(UTC) - timedelta(seconds=1),
    )

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "task deadline has passed for member material submission"


def test_member_submission_deadline_boundary_rejects_equal_now(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    task = client.get(
        f"/api/tasks/{task_id}",
        headers=admin_auth_headers(client),
    ).json()
    deadline = datetime(2026, 12, 1, tzinfo=UTC)
    task["deadline"] = deadline.isoformat()
    reimbursement_task = ReimbursementTask.model_validate(task)

    try:
        ensure_task_accepts_member_submission(reimbursement_task, now=deadline)
    except TaskSubmissionDeadlinePassedError as error:
        assert str(error) == "task deadline has passed for member material submission"
    else:
        raise AssertionError("expected deadline-equality submission rejection")


def test_submit_material_rejects_invalid_material_type(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "receipt",
        },
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )

    payload = assert_api_error(
        response,
        status_code=422,
        code="validation_error",
    )
    assert payload["detail"][0]["loc"][-1] == "material_type"


def test_submit_material_rejects_missing_filename(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("   ", b"fake-pdf-content", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "uploaded file must have a filename"


def test_submit_material_rejects_empty_file(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "uploaded file is empty: ticket.pdf"


def test_submit_material_rejects_unsupported_content_type(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("notes.txt", b"plain-text", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["detail"].startswith("unsupported material content type: text/plain;")


def test_submit_material_rejects_eml_outside_email_channel(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "other_attachment",
        },
        files={"files": ("forwarded.eml", b"raw-email", "message/rfc822")},
    )

    assert response.status_code == 415
    assert response.json()["detail"].startswith(
        "unsupported material content type: message/rfc822;"
    )


def test_submit_material_rejects_file_exceeding_size_limit(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={
            "files": (
                "oversized.pdf",
                b"x" * (MAX_MATERIAL_UPLOAD_SIZE_BYTES + 1),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"].startswith("uploaded file exceeds size limit: oversized.pdf")


def test_list_materials_by_task(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "telegram",
            "material_type": "invoice",
        },
        files=[
            ("files", ("ticket.pdf", b"ticket", "application/pdf")),
            ("files", ("payment.png", b"payment", "image/png")),
        ],
    )

    response = client.get(
        f"/api/tasks/{task_id}/materials",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 200
    assert [item["original_filename"] for item in response.json()["items"]] == [
        "ticket.pdf",
        "payment.png",
    ]
    assert [item["material_type"] for item in response.json()["items"]] == [
        "invoice",
        "invoice",
    ]


def test_list_materials_rejects_missing_task(tmp_path):
    client = make_client(tmp_path)

    response = client.get(
        "/api/tasks/missing/materials",
        headers=admin_auth_headers(client),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"
