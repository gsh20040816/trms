from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

class EmailInboxRecordStatus(StrEnum):
    READY_FOR_IMPORT = "ready_for_import"
    IGNORED = "ignored"
    IMPORTED = "imported"
    PARTIALLY_IMPORTED = "partially_imported"
    IMPORT_FAILED = "import_failed"


class EmailInboxRecordCreate(BaseModel):
    mailbox_uid: str = Field(min_length=1, max_length=255)
    message_id: str | None = Field(default=None, max_length=255)
    sender_email: str = Field(min_length=1, max_length=320)
    subject: str = Field(min_length=1, max_length=998)
    raw_storage_key: str = Field(min_length=1, max_length=512)
    received_at: datetime | None = None
    status: EmailInboxRecordStatus
    result_code: str | None = Field(default=None, max_length=64)
    resolved_member_id: str | None = Field(default=None, max_length=128)
    submitted_task_key: str | None = Field(default=None, max_length=64)
    resolved_task_id: str | None = Field(default=None, max_length=36)

    @field_validator("mailbox_uid", "message_id", "subject", "result_code", "resolved_member_id")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("sender_email")
    @classmethod
    def normalize_sender_email(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("sender_email must not be empty")
        return normalized

    @field_validator("submitted_task_key", "resolved_task_id")
    @classmethod
    def normalize_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EmailInboxRecord(BaseModel):
    id: str
    mailbox_uid: str
    message_id: str | None
    sender_email: str
    subject: str
    raw_storage_key: str
    received_at: datetime | None
    status: EmailInboxRecordStatus
    result_code: str | None
    resolved_member_id: str | None
    submitted_task_key: str | None
    resolved_task_id: str | None
    created_at: datetime


class EmailInboxRecordRepository(Protocol):
    def create(self, data: EmailInboxRecordCreate) -> EmailInboxRecord:
        raise NotImplementedError

    def get(self, record_id: str) -> EmailInboxRecord | None:
        raise NotImplementedError

    def get_by_mailbox_uid(self, mailbox_uid: str) -> EmailInboxRecord | None:
        raise NotImplementedError

    def get_max_mailbox_uid(self) -> str | None:
        raise NotImplementedError

    def list_ready_for_import(self, *, limit: int) -> list[EmailInboxRecord]:
        raise NotImplementedError

    def update_result(
        self,
        record_id: str,
        *,
        status: EmailInboxRecordStatus,
        result_code: str,
    ) -> EmailInboxRecord | None:
        raise NotImplementedError


class InMemoryEmailInboxRecordRepository:
    def __init__(self) -> None:
        self._records: dict[str, EmailInboxRecord] = {}
        self._lock = RLock()

    def create(self, data: EmailInboxRecordCreate) -> EmailInboxRecord:
        with self._lock:
            record = EmailInboxRecord(
                id=str(uuid4()),
                created_at=datetime.now(UTC),
                **data.model_dump(),
            )
            self._records[record.id] = record
            return record

    def get(self, record_id: str) -> EmailInboxRecord | None:
        with self._lock:
            return self._records.get(record_id)

    def get_by_mailbox_uid(self, mailbox_uid: str) -> EmailInboxRecord | None:
        normalized = mailbox_uid.strip()
        if not normalized:
            return None
        with self._lock:
            for record in self._records.values():
                if record.mailbox_uid == normalized:
                    return record
            return None

    def get_max_mailbox_uid(self) -> str | None:
        with self._lock:
            if not self._records:
                return None
            return max(self._records.values(), key=lambda item: _mailbox_uid_sort_key(item.mailbox_uid)).mailbox_uid

    def list_ready_for_import(self, *, limit: int) -> list[EmailInboxRecord]:
        with self._lock:
            records = [
                record
                for record in self._records.values()
                if record.status is EmailInboxRecordStatus.READY_FOR_IMPORT
            ]
            records.sort(key=lambda item: item.created_at)
            return records[:limit]

    def update_result(
        self,
        record_id: str,
        *,
        status: EmailInboxRecordStatus,
        result_code: str,
    ) -> EmailInboxRecord | None:
        with self._lock:
            record = self._records.get(record_id)
            if record is None:
                return None
            updated = record.model_copy(
                update={
                    "status": status,
                    "result_code": result_code,
                }
            )
            self._records[record_id] = updated
            return updated


def _mailbox_uid_sort_key(value: str) -> tuple[int, str]:
    normalized = value.strip()
    if normalized.isdigit():
        return (0, f"{int(normalized):020d}")
    return (1, normalized)
