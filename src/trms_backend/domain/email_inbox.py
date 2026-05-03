from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from trms_backend.domain.email_bindings import normalize_email_address


class EmailInboxRecordStatus(StrEnum):
    READY_FOR_IMPORT = "ready_for_import"
    IGNORED = "ignored"


class EmailInboxRecordCreate(BaseModel):
    mailbox_uid: str = Field(min_length=1, max_length=255)
    message_id: str | None = Field(default=None, max_length=255)
    sender_email: str = Field(min_length=3, max_length=320)
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
        return normalize_email_address(value, field_name="sender_email")

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

    def get_by_mailbox_uid(self, mailbox_uid: str) -> EmailInboxRecord | None:
        raise NotImplementedError

    def list_ready_for_import(self, *, limit: int) -> list[EmailInboxRecord]:
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

    def get_by_mailbox_uid(self, mailbox_uid: str) -> EmailInboxRecord | None:
        normalized = mailbox_uid.strip()
        if not normalized:
            return None
        with self._lock:
            for record in self._records.values():
                if record.mailbox_uid == normalized:
                    return record
            return None

    def list_ready_for_import(self, *, limit: int) -> list[EmailInboxRecord]:
        with self._lock:
            records = [
                record
                for record in self._records.values()
                if record.status is EmailInboxRecordStatus.READY_FOR_IMPORT
            ]
            records.sort(key=lambda item: item.created_at)
            return records[:limit]
