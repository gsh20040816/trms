from fastapi.testclient import TestClient

from trms_backend.main import create_app

from test_tasks_api import valid_task_payload


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
        data={"submitter_id": "2250001", "channel": "web"},
        files={"files": ("ticket.pdf", b"fake-pdf-content", "application/pdf")},
    )

    assert response.status_code == 201
    material = response.json()["items"][0]
    assert material["task_id"] == task_id
    assert material["submitter_id"] == "2250001"
    assert material["channel"] == "web"
    assert material["original_filename"] == "ticket.pdf"
    assert material["size_bytes"] == len(b"fake-pdf-content")
    assert material["duplicate_of"] is None


def test_submit_material_rejects_draft_task(tmp_path):
    client = make_client(tmp_path)
    task_id = client.post("/api/tasks", json=valid_task_payload()).json()["id"]

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={"submitter_id": "2250001", "channel": "web"},
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
        data={"submitter_id": "2250001", "channel": "cli"},
        files=files,
    ).json()["items"][0]

    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={"submitter_id": "2250001", "channel": "cli"},
        files={"files": ("ticket-copy.pdf", b"same-content", "application/pdf")},
    )

    assert response.status_code == 201
    duplicate = response.json()["items"][0]
    assert duplicate["duplicate_of"] == first["id"]


def test_list_materials_by_task(tmp_path):
    client = make_client(tmp_path)
    task_id = create_open_task(client)
    client.post(
        f"/api/tasks/{task_id}/materials",
        data={"submitter_id": "2250001", "channel": "telegram"},
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


def test_list_materials_rejects_missing_task(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/tasks/missing/materials")

    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"
