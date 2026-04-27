from hashlib import sha256

from trms_backend.infrastructure.database import build_session_factory, session_scope
from trms_backend.infrastructure.models import MaterialRow
from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from fastapi.testclient import TestClient

from test_tasks_api import valid_task_payload


def test_local_material_storage_uses_distinct_keys_for_same_filename(tmp_path):
    storage_root = tmp_path / "material-storage"
    storage = LocalMaterialFileStorage(storage_root)

    first = storage.save(
        task_id="task-1",
        original_filename="ticket.pdf",
        content_type="application/pdf",
        content=b"first-version",
    )
    second = storage.save(
        task_id="task-1",
        original_filename="ticket.pdf",
        content_type="application/pdf",
        content=b"second-version",
    )

    assert first.storage_key != second.storage_key
    assert (storage_root / first.storage_key).read_bytes() == b"first-version"
    assert (storage_root / second.storage_key).read_bytes() == b"second-version"


def test_local_material_storage_records_file_metadata(tmp_path):
    storage_root = tmp_path / "material-storage"
    storage = LocalMaterialFileStorage(storage_root)

    stored_file = storage.save(
        task_id="task-1",
        original_filename="../nested/payment.png",
        content_type="image/png",
        content=b"png-bytes",
    )

    assert stored_file.original_filename == "payment.png"
    assert stored_file.content_type == "image/png"
    assert stored_file.size_bytes == len(b"png-bytes")
    assert stored_file.sha256 == sha256(b"png-bytes").hexdigest()
    assert (storage_root / stored_file.storage_key).read_bytes() == b"png-bytes"


def test_material_record_persists_storage_key_for_saved_file(tmp_path):
    client = TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )
    task = client.post("/api/tasks", json=valid_task_payload()).json()
    client.patch(f"/api/tasks/{task['id']}/status", json={"target_status": "open"})

    response = client.post(
        f"/api/tasks/{task['id']}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": ("ticket.pdf", b"stored-content", "application/pdf")},
    )

    assert response.status_code == 201
    material = response.json()["items"][0]
    session_factory = build_session_factory(f"sqlite:///{tmp_path}/test.db")
    with session_scope(session_factory) as session:
        row = session.get(MaterialRow, material["id"])
        assert row is not None
        assert row.storage_key == material["storage_key"]

    storage_root = tmp_path / "material-storage"
    assert (storage_root / material["storage_key"]).read_bytes() == b"stored-content"
