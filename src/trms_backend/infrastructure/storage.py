from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from trms_backend.domain.materials import MaterialFileStorage, StoredMaterialFile


class LocalMaterialFileStorage(MaterialFileStorage):
    def __init__(self, root_dir: str | Path) -> None:
        self._root_dir = Path(root_dir)

    def save(
        self,
        *,
        task_id: str,
        original_filename: str,
        content_type: str | None,
        content: bytes,
    ) -> StoredMaterialFile:
        safe_filename = _normalize_filename(original_filename)
        storage_key = self._build_storage_key(task_id, safe_filename)
        storage_path = self._root_dir / storage_key
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(content)
        return StoredMaterialFile(
            storage_key=storage_key.as_posix(),
            original_filename=safe_filename,
            content_type=content_type,
            size_bytes=len(content),
            sha256=sha256(content).hexdigest(),
        )

    def _build_storage_key(self, task_id: str, filename: str) -> Path:
        while True:
            candidate = Path(task_id) / f"{uuid4()}-{filename}"
            if not (self._root_dir / candidate).exists():
                return candidate


def _normalize_filename(original_filename: str) -> str:
    normalized = original_filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1].strip()
    return normalized or "unnamed"
