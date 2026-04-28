from __future__ import annotations

from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

import boto3
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import ClientError

from trms_backend.domain.materials import MaterialFileStorage, StoredMaterialFile
from trms_backend.runtime_config import (
    LocalFileStorageConfig,
    RuntimeConfig,
    S3FileStorageConfig,
)


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

    def read(self, *, storage_key: str) -> bytes:
        return self._resolve_storage_path(storage_key).read_bytes()

    def _build_storage_key(self, task_id: str, filename: str) -> Path:
        while True:
            candidate = Path(task_id) / f"{uuid4()}-{filename}"
            if not (self._root_dir / candidate).exists():
                return candidate

    def _resolve_storage_path(self, storage_key: str) -> Path:
        return self._root_dir / Path(storage_key)


class S3CompatibleMaterialFileStorage(MaterialFileStorage):
    def __init__(
        self,
        config: S3FileStorageConfig,
        *,
        client: Any | None = None,
    ) -> None:
        self._bucket = config.bucket
        self._key_prefix = config.key_prefix
        self._client = client or boto3.client(
            "s3",
            endpoint_url=config.endpoint,
            aws_access_key_id=config.access_key_id.get_secret_value(),
            aws_secret_access_key=config.secret_access_key.get_secret_value(),
            region_name=config.region,
            config=BotocoreConfig(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )

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
        put_object_kwargs: dict[str, Any] = {
            "Bucket": self._bucket,
            "Key": storage_key,
            "Body": content,
        }
        if content_type is not None:
            put_object_kwargs["ContentType"] = content_type
        self._client.put_object(**put_object_kwargs)
        return StoredMaterialFile(
            storage_key=storage_key,
            original_filename=safe_filename,
            content_type=content_type,
            size_bytes=len(content),
            sha256=sha256(content).hexdigest(),
        )

    def read(self, *, storage_key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=storage_key)
        except ClientError as error:
            error_code = str(error.response.get("Error", {}).get("Code", ""))
            http_status_code = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if error_code in {"404", "NoSuchKey", "NotFound"} or http_status_code == 404:
                raise FileNotFoundError(storage_key) from error
            raise
        body = response["Body"]
        try:
            return body.read()
        finally:
            close = getattr(body, "close", None)
            if callable(close):
                close()

    def _build_storage_key(self, task_id: str, filename: str) -> str:
        path_parts: list[str] = []
        if self._key_prefix is not None:
            path_parts.append(self._key_prefix)
        path_parts.extend([task_id, f"{uuid4()}-{filename}"])
        return PurePosixPath(*path_parts).as_posix()


def build_material_file_storage(config: RuntimeConfig) -> MaterialFileStorage:
    if isinstance(config.file_storage, LocalFileStorageConfig):
        return LocalMaterialFileStorage(config.file_storage.root_dir)
    if isinstance(config.file_storage, S3FileStorageConfig):
        return S3CompatibleMaterialFileStorage(config.file_storage)
    raise TypeError(f"unsupported file storage config: {type(config.file_storage)!r}")


def _normalize_filename(original_filename: str) -> str:
    normalized = original_filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1].strip()
    return normalized or "unnamed"
