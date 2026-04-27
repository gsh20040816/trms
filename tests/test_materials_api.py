from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from trms_backend.domain.tasks import (
    ReimbursementTask,
    TaskSubmissionDeadlinePassedError,
    ensure_task_accepts_member_submission,
)
from trms_backend.main import create_app

from test_tasks_api import update_task_row, valid_task_payload


def make_client(tmp_path):
    return TestClient(create_app(f"sqlite:///{tmp_path}/test.db"))


def create_open_task(client: TestClient) -> str:
    created = client.post("/api/tasks", json=valid_task_payload()).json()
    client.patch(f"/api/tasks/{created['id']}/status", json={"target_status": "open"})
    return created["id"]


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
    assert material["task_id"] == task_id
    assert material["submitter_id"] == "2250001"
    assert material["channel"] == "web"
    assert material["material_type"] == "invoice"
    assert material["original_filename"] == "ticket.pdf"
    assert material["size_bytes"] == len(b"fake-pdf-content")
    assert material["duplicate_of"] is None


def test_submit_material_accepts_supported_material_types(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)

    for material_type, filename in (
        ("invoice", "ticket.pdf"),
        ("payment_record", "payment.png"),
        ("competition_notice", "notice.pdf"),
        ("itinerary", "itinerary.pdf"),
        ("order_screenshot", "order.png"),
        ("other_attachment", "other.zip"),
    ):
        response = client.post(
            f"/api/tasks/{task_id}/materials",
            data={
                "submitter_id": "2250001",
                "channel": "web",
                "material_type": material_type,
            },
            files={"files": (filename, material_type.encode(), "application/octet-stream")},
        )

        assert response.status_code == 201
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


def test_submit_material_marks_duplicate_file_in_same_task(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    files = {"files": ("ticket.pdf", b"same-content", "application/pdf")}
    first = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "cli",
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
    assert duplicate["duplicate_of"] == first["id"]


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
