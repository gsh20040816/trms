from hashlib import sha256

from trms_backend.infrastructure.storage import LocalMaterialFileStorage


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
