from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from threading import RLock
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field


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


class MaterialCreate(BaseModel):
    task_id: str = Field(min_length=1)
    submitter_id: str = Field(min_length=1)
    channel: SubmissionChannel
    material_type: MaterialType
    original_filename: str = Field(min_length=1)
    content_type: str | None = None
    size_bytes: int = Field(ge=0)
    sha256: str = Field(min_length=64, max_length=64)


class MaterialRecord(BaseModel):
    id: str
    task_id: str
    submitter_id: str
    channel: SubmissionChannel
    material_type: MaterialType
    original_filename: str
    content_type: str | None
    size_bytes: int
    sha256: str
    duplicate_of: str | None
    created_at: datetime


class StoredMaterialFile(BaseModel):
    storage_key: str = Field(min_length=1)
    original_filename: str = Field(min_length=1)
    content_type: str | None = None
    size_bytes: int = Field(ge=0)
    sha256: str = Field(min_length=64, max_length=64)


class MaterialRepository(Protocol):
    def create(self, data: MaterialCreate) -> MaterialRecord:
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


class InMemoryMaterialRepository:
    def __init__(self) -> None:
        self._materials: dict[str, MaterialRecord] = {}
        self._lock = RLock()

    def create(self, data: MaterialCreate) -> MaterialRecord:
        with self._lock:
            duplicate_of = self._find_duplicate_material_id(data.task_id, data.sha256)
            material = MaterialRecord(
                id=str(uuid4()),
                created_at=datetime.now(timezone.utc),
                duplicate_of=duplicate_of,
                **data.model_dump(),
            )
            self._materials[material.id] = material
            return material

    def list_by_task(self, task_id: str) -> list[MaterialRecord]:
        with self._lock:
            materials = [
                material for material in self._materials.values() if material.task_id == task_id
            ]
            return sorted(materials, key=lambda material: material.created_at)

    def get(self, material_id: str) -> MaterialRecord | None:
        with self._lock:
            return self._materials.get(material_id)

    def _find_duplicate_material_id(self, task_id: str, sha256: str) -> str | None:
        for material in self._materials.values():
            if material.task_id == task_id and material.sha256 == sha256:
                return material.id
        return None
