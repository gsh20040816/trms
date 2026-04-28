from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from threading import RLock
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

SUPPORTED_MATERIAL_UPLOAD_CONTENT_TYPES = (
    "application/pdf",
    "application/zip",
    "image/jpeg",
    "image/png",
    "image/webp",
)
MAX_MATERIAL_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024


class SubmissionChannel(StrEnum):
    WEB = "web"
    CLI = "cli"
    TELEGRAM = "telegram"
    EMAIL = "email"


class MaterialType(StrEnum):
    INVOICE = "invoice"
    PAYMENT_RECORD = "payment_record"
    COMPETITION_NOTICE = "competition_notice"
    ITINERARY = "itinerary"
    ORDER_SCREENSHOT = "order_screenshot"
    OTHER_ATTACHMENT = "other_attachment"


class MaterialStatus(StrEnum):
    ASSIGNED = "assigned"
    PENDING_ASSIGNMENT = "pending_assignment"
    DELETED = "deleted"


class MaterialCreate(BaseModel):
    status: MaterialStatus
    task_id: str | None = None
    submitter_id: str | None = None
    task_id_hint: str | None = None
    submitter_id_hint: str | None = None
    channel: SubmissionChannel
    material_type: MaterialType
    storage_key: str = Field(min_length=1)
    original_filename: str = Field(min_length=1)
    content_type: str | None = None
    size_bytes: int = Field(ge=0)
    sha256: str = Field(min_length=64, max_length=64)

    @field_validator("task_id", "submitter_id", "task_id_hint", "submitter_id_hint")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_assignment_state(self) -> MaterialCreate:
        if self.status is MaterialStatus.ASSIGNED:
            if self.task_id is None or self.submitter_id is None:
                raise ValueError("assigned material requires task_id and submitter_id")
            return self
        if self.task_id is not None or self.submitter_id is not None:
            raise ValueError(
                "pending_assignment material must not expose resolved task_id or submitter_id"
            )
        return self


class MaterialRecord(BaseModel):
    id: str
    status: MaterialStatus
    task_id: str | None
    submitter_id: str | None
    task_id_hint: str | None
    submitter_id_hint: str | None
    channel: SubmissionChannel
    material_type: MaterialType
    storage_key: str
    original_filename: str
    content_type: str | None
    size_bytes: int
    sha256: str
    duplicate_of: str | None
    claimed_by: str | None
    claimed_at: datetime | None
    created_at: datetime


class StoredMaterialFile(BaseModel):
    storage_key: str = Field(min_length=1)
    original_filename: str = Field(min_length=1)
    content_type: str | None = None
    size_bytes: int = Field(ge=0)
    sha256: str = Field(min_length=64, max_length=64)


class MaterialUploadValidationError(ValueError):
    """Raised when an uploaded material file violates input constraints."""


class MaterialUploadMissingFilenameError(MaterialUploadValidationError):
    def __init__(self) -> None:
        super().__init__("uploaded file must have a filename")


class MaterialUploadEmptyFileError(MaterialUploadValidationError):
    def __init__(self, filename: str) -> None:
        super().__init__(f"uploaded file is empty: {filename}")


class MaterialUploadUnsupportedContentTypeError(MaterialUploadValidationError):
    def __init__(self, content_type: str | None) -> None:
        supported = ", ".join(SUPPORTED_MATERIAL_UPLOAD_CONTENT_TYPES)
        super().__init__(
            f"unsupported material content type: {content_type or '<missing>'}; "
            f"supported content types: {supported}"
        )


class MaterialUploadTooLargeError(MaterialUploadValidationError):
    def __init__(self, *, filename: str, size_bytes: int) -> None:
        super().__init__(
            f"uploaded file exceeds size limit: {filename} ({size_bytes} bytes > "
            f"{MAX_MATERIAL_UPLOAD_SIZE_BYTES} bytes)"
        )


class MaterialRepository(Protocol):
    def create(self, data: MaterialCreate) -> MaterialRecord:
        raise NotImplementedError

    def list_pending_assignment_by_task_hint(self, task_id: str) -> list[MaterialRecord]:
        raise NotImplementedError

    def claim_pending_assignment(
        self,
        *,
        material_id: str,
        task_id: str,
        submitter_id: str,
        claimed_by: str,
    ) -> MaterialRecord | None:
        raise NotImplementedError

    def mark_deleted(self, material_id: str) -> MaterialRecord | None:
        raise NotImplementedError

    def get(self, material_id: str) -> MaterialRecord | None:
        raise NotImplementedError

    def list_by_task(self, task_id: str) -> list[MaterialRecord]:
        raise NotImplementedError


class MaterialFileStorage(Protocol):
    def save(
        self,
        *,
        task_id: str,
        original_filename: str,
        content_type: str | None,
        content: bytes,
    ) -> StoredMaterialFile:
        raise NotImplementedError

    def read(self, *, storage_key: str) -> bytes:
        raise NotImplementedError


def validate_material_upload(
    *,
    original_filename: str | None,
    content_type: str | None,
    content: bytes,
) -> None:
    filename = (original_filename or "").strip()
    if not filename:
        raise MaterialUploadMissingFilenameError()

    size_bytes = len(content)
    if size_bytes == 0:
        raise MaterialUploadEmptyFileError(filename)
    if size_bytes > MAX_MATERIAL_UPLOAD_SIZE_BYTES:
        raise MaterialUploadTooLargeError(filename=filename, size_bytes=size_bytes)

    normalized_content_type = _normalize_content_type(content_type)
    if normalized_content_type not in SUPPORTED_MATERIAL_UPLOAD_CONTENT_TYPES:
        raise MaterialUploadUnsupportedContentTypeError(content_type)


class InMemoryMaterialRepository:
    def __init__(self) -> None:
        self._materials: dict[str, MaterialRecord] = {}
        self._lock = RLock()

    def create(self, data: MaterialCreate) -> MaterialRecord:
        with self._lock:
            duplicate_of = self._find_duplicate_material_id(data)
            material = MaterialRecord(
                id=str(uuid4()),
                created_at=datetime.now(timezone.utc),
                duplicate_of=duplicate_of,
                claimed_by=None,
                claimed_at=None,
                **data.model_dump(),
            )
            self._materials[material.id] = material
            return material

    def list_pending_assignment_by_task_hint(self, task_id: str) -> list[MaterialRecord]:
        with self._lock:
            materials = [
                material
                for material in self._materials.values()
                if material.status is MaterialStatus.PENDING_ASSIGNMENT
                and material.task_id_hint == task_id
            ]
            return sorted(materials, key=lambda material: material.created_at)

    def claim_pending_assignment(
        self,
        *,
        material_id: str,
        task_id: str,
        submitter_id: str,
        claimed_by: str,
    ) -> MaterialRecord | None:
        with self._lock:
            material = self._materials.get(material_id)
            if material is None or material.status is not MaterialStatus.PENDING_ASSIGNMENT:
                return None

            claimed_at = datetime.now(timezone.utc)
            updated = material.model_copy(
                update={
                    "status": MaterialStatus.ASSIGNED,
                    "task_id": task_id,
                    "submitter_id": submitter_id,
                    "duplicate_of": self._find_duplicate_material_id_for_assignment(
                        task_id=task_id,
                        sha256=material.sha256,
                    ),
                    "claimed_by": claimed_by,
                    "claimed_at": claimed_at,
                }
            )
            self._materials[material_id] = updated
            return updated

    def mark_deleted(self, material_id: str) -> MaterialRecord | None:
        with self._lock:
            material = self._materials.get(material_id)
            if material is None or material.status is not MaterialStatus.ASSIGNED:
                return None

            updated = material.model_copy(update={"status": MaterialStatus.DELETED})
            self._materials[material_id] = updated
            return updated

    def list_by_task(self, task_id: str) -> list[MaterialRecord]:
        with self._lock:
            materials = [
                material
                for material in self._materials.values()
                if material.status is MaterialStatus.ASSIGNED and material.task_id == task_id
            ]
            return sorted(materials, key=lambda material: material.created_at)

    def get(self, material_id: str) -> MaterialRecord | None:
        with self._lock:
            return self._materials.get(material_id)

    def _find_duplicate_material_id(self, data: MaterialCreate) -> str | None:
        if data.status is not MaterialStatus.ASSIGNED or data.task_id is None:
            return None
        return self._find_duplicate_material_id_for_assignment(
            task_id=data.task_id,
            sha256=data.sha256,
        )

    def _find_duplicate_material_id_for_assignment(
        self,
        *,
        task_id: str,
        sha256: str,
    ) -> str | None:
        for material in self._materials.values():
            if (
                material.status is MaterialStatus.ASSIGNED
                and material.task_id == task_id
                and material.sha256 == sha256
            ):
                return material.id
        return None


def _normalize_content_type(content_type: str | None) -> str:
    return (content_type or "").split(";", maxsplit=1)[0].strip().lower()
