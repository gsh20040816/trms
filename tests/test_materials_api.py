from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from trms_backend.domain.materials import MAX_MATERIAL_UPLOAD_SIZE_BYTES
from trms_backend.domain.tasks import (
    ReimbursementTask,
    TaskSubmissionDeadlinePassedError,
    ensure_task_accepts_member_submission,
)
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


def create_open_task(client: TestClient) -> str:
    created = client.post("/api/tasks", json=valid_task_payload()).json()
    client.patch(f"/api/tasks/{created['id']}/status", json={"target_status": "open"})
    return created["id"]


def assert_single_pending_recognition_task(client: TestClient, material_id: str) -> None:
    response = client.get(f"/api/materials/{material_id}/recognition-tasks")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["material_id"] == material_id
    assert items[0]["status"] == "pending"
    assert items[0]["is_final_fact"] is False
    assert items[0]["failure"] is None
    assert items[0]["raw_response"] is None
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
    assert_single_pending_recognition_task(client, material["id"])


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
    assert_single_pending_recognition_task(client, material["id"])


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

    listed = client.get(f"/api/tasks/{task_id}/materials")
    assert listed.status_code == 200
    assert listed.json()["items"] == []


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

    listed = client.get(f"/api/tasks/{task_id}/materials")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [material_id]


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

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "administrator is not allowed to claim materials for this task"
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

    assert response.status_code == 409
    assert response.json()["detail"] == "material is not pending assignment"


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
    task_id = client.post("/api/tasks", json=valid_task_payload()).json()["id"]

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

    listed = client.get(f"/api/tasks/{task_id}/materials")
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

    listed = client.get(f"/api/tasks/{task_id}/materials")
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
    task = client.get(f"/api/tasks/{task_id}").json()
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

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["loc"][-1] == "material_type"


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

    response = client.get(f"/api/tasks/{task_id}/materials")

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

    response = client.get("/api/tasks/missing/materials")

    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"
