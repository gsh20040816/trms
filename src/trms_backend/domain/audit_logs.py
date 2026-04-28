from __future__ import annotations

from datetime import date, datetime, time, timezone
from enum import Enum, StrEnum
from pathlib import Path
import re
from threading import RLock
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


REDACTED_AUDIT_VALUE = "[REDACTED]"
TRUNCATED_AUDIT_VALUE_SUFFIX = "...[truncated]"
MAX_AUDIT_SUMMARY_LENGTH = 1024
MAX_AUDIT_DETAIL_TEXT_LENGTH = 256
_SENSITIVE_DETAIL_KEYWORDS = (
    "password",
    "secret",
    "token",
    "authorization",
    "cookie",
    "api_key",
    "access_key",
    "refresh_token",
)
_BULK_CONTENT_DETAIL_KEYWORDS = (
    "content",
    "body",
    "full_text",
    "document_text",
    "raw_response",
    "binary",
    "bytes",
    "base64",
)
_SENSITIVE_SUMMARY_PATTERN = re.compile(
    r"(?i)\b(password|secret|token|api[_-]?key|authorization|cookie|access[_-]?key|refresh[_-]?token)\s*=\s*([^\s,;]+)"
)


class AuditLogResult(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"


class AuditLogCreate(BaseModel):
    actor_id: str = Field(min_length=1, max_length=128)
    object_type: str = Field(min_length=1, max_length=64)
    object_id: str = Field(min_length=1, max_length=128)
    action: str = Field(min_length=1, max_length=64)
    result: AuditLogResult
    summary: str = Field(min_length=1, max_length=MAX_AUDIT_SUMMARY_LENGTH)
    detail: dict[str, Any] = Field(default_factory=dict)
    task_id: str | None = Field(default=None, max_length=36)
    request_id: str | None = Field(default=None, max_length=64)

    @field_validator("actor_id", "object_type", "object_id", "action")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @field_validator("task_id", "request_id")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def sanitize_payload(self) -> AuditLogCreate:
        self.summary = sanitize_audit_summary(self.summary)
        self.detail = sanitize_audit_detail(self.detail)
        return self


class AuditLogRecord(BaseModel):
    id: str
    actor_id: str
    object_type: str
    object_id: str
    action: str
    result: AuditLogResult
    summary: str
    detail: dict[str, Any]
    task_id: str | None
    request_id: str | None
    created_at: datetime


class AuditLogRepository(Protocol):
    def create(self, data: AuditLogCreate) -> AuditLogRecord:
        raise NotImplementedError

    def list_by_object(self, *, object_type: str, object_id: str) -> list[AuditLogRecord]:
        raise NotImplementedError


class InMemoryAuditLogRepository(AuditLogRepository):
    def __init__(self) -> None:
        self._audit_logs: dict[str, AuditLogRecord] = {}
        self._lock = RLock()

    def create(self, data: AuditLogCreate) -> AuditLogRecord:
        with self._lock:
            record = AuditLogRecord(
                id=str(uuid4()),
                created_at=datetime.now(timezone.utc),
                **data.model_dump(),
            )
            self._audit_logs[record.id] = record
            return record

    def list_by_object(self, *, object_type: str, object_id: str) -> list[AuditLogRecord]:
        normalized_object_type = object_type.strip()
        normalized_object_id = object_id.strip()
        if not normalized_object_type or not normalized_object_id:
            return []

        with self._lock:
            matched = [
                record
                for record in self._audit_logs.values()
                if record.object_type == normalized_object_type
                and record.object_id == normalized_object_id
            ]
            return sorted(matched, key=lambda record: record.created_at)


def sanitize_audit_summary(summary: str) -> str:
    normalized = summary.strip()
    if not normalized:
        raise ValueError("summary must not be blank")
    sanitized = _SENSITIVE_SUMMARY_PATTERN.sub(r"\1=[REDACTED]", normalized)
    return _truncate_text(sanitized, limit=MAX_AUDIT_SUMMARY_LENGTH)


def sanitize_audit_detail(detail: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _sanitize_audit_value(key, value)
        for key, value in detail.items()
    }


def _sanitize_audit_value(key: str, value: Any) -> Any:
    normalized_key = key.lower()
    if any(keyword in normalized_key for keyword in _SENSITIVE_DETAIL_KEYWORDS):
        return REDACTED_AUDIT_VALUE
    if any(keyword in normalized_key for keyword in _BULK_CONTENT_DETAIL_KEYWORDS):
        return REDACTED_AUDIT_VALUE
    return _normalize_audit_scalar(value)


def _normalize_audit_scalar(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _truncate_text(value.strip(), limit=MAX_AUDIT_DETAIL_TEXT_LENGTH)
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, bytes):
        return REDACTED_AUDIT_VALUE
    if isinstance(value, Path):
        return _truncate_text(str(value), limit=MAX_AUDIT_DETAIL_TEXT_LENGTH)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, BaseModel):
        return {
            key: _sanitize_audit_value(key, item)
            for key, item in value.model_dump(mode="json").items()
        }
    if isinstance(value, dict):
        return {
            str(item_key): _sanitize_audit_value(str(item_key), item_value)
            for item_key, item_value in value.items()
        }
    if isinstance(value, list | tuple | set):
        return [_normalize_audit_scalar(item) for item in value]
    return _truncate_text(repr(value), limit=MAX_AUDIT_DETAIL_TEXT_LENGTH)


def _truncate_text(value: str, *, limit: int) -> str:
    normalized = value.strip()
    if len(normalized) <= limit:
        return normalized
    cutoff = max(limit - len(TRUNCATED_AUDIT_VALUE_SUFFIX), 1)
    return normalized[:cutoff] + TRUNCATED_AUDIT_VALUE_SUFFIX
