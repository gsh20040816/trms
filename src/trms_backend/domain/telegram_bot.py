from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from threading import RLock
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class TelegramBindingAuthorizationCreate(BaseModel):
    telegram_user_id: int = Field(gt=0)
    telegram_chat_id: int
    telegram_username: str | None = Field(default=None, max_length=64)
    token_hash: str = Field(min_length=64, max_length=64)
    expires_at: datetime

    @field_validator("telegram_username")
    @classmethod
    def normalize_telegram_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lstrip("@").lower()
        return normalized or None


class TelegramBindingAuthorizationRecord(BaseModel):
    id: str
    telegram_user_id: int
    telegram_chat_id: int
    telegram_username: str | None
    token_hash: str
    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None


class TelegramBindingAuthorizationStatus(StrEnum):
    PENDING = "pending"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class TelegramBindingAuthorizationView(BaseModel):
    telegram_user_id: int
    telegram_chat_id: int
    telegram_username: str | None
    expires_at: datetime
    consumed_at: datetime | None
    status: TelegramBindingAuthorizationStatus


class TelegramTaskContextRecord(BaseModel):
    telegram_user_id: int
    task_id: str
    updated_at: datetime


class TelegramBindingAuthorizationRepository(Protocol):
    def create(
        self,
        data: TelegramBindingAuthorizationCreate,
    ) -> TelegramBindingAuthorizationRecord:
        raise NotImplementedError

    def get_by_token_hash(self, token_hash: str) -> TelegramBindingAuthorizationRecord | None:
        raise NotImplementedError

    def mark_consumed(
        self,
        authorization_id: str,
        *,
        consumed_at: datetime,
    ) -> TelegramBindingAuthorizationRecord | None:
        raise NotImplementedError


class TelegramTaskContextRepository(Protocol):
    def get_by_telegram_user_id(self, telegram_user_id: int) -> TelegramTaskContextRecord | None:
        raise NotImplementedError

    def upsert(
        self,
        *,
        telegram_user_id: int,
        task_id: str,
    ) -> TelegramTaskContextRecord:
        raise NotImplementedError

    def delete(self, telegram_user_id: int) -> None:
        raise NotImplementedError


class InMemoryTelegramBindingAuthorizationRepository:
    def __init__(self) -> None:
        self._records_by_id: dict[str, TelegramBindingAuthorizationRecord] = {}
        self._record_id_by_token_hash: dict[str, str] = {}
        self._lock = RLock()

    def create(
        self,
        data: TelegramBindingAuthorizationCreate,
    ) -> TelegramBindingAuthorizationRecord:
        now = datetime.now(timezone.utc)
        record = TelegramBindingAuthorizationRecord(
            id=str(uuid4()),
            telegram_user_id=data.telegram_user_id,
            telegram_chat_id=data.telegram_chat_id,
            telegram_username=data.telegram_username,
            token_hash=data.token_hash,
            created_at=now,
            expires_at=data.expires_at,
            consumed_at=None,
        )
        with self._lock:
            self._records_by_id[record.id] = record
            self._record_id_by_token_hash[record.token_hash] = record.id
        return record

    def get_by_token_hash(self, token_hash: str) -> TelegramBindingAuthorizationRecord | None:
        with self._lock:
            record_id = self._record_id_by_token_hash.get(token_hash)
            if record_id is None:
                return None
            return self._records_by_id.get(record_id)

    def mark_consumed(
        self,
        authorization_id: str,
        *,
        consumed_at: datetime,
    ) -> TelegramBindingAuthorizationRecord | None:
        with self._lock:
            existing = self._records_by_id.get(authorization_id)
            if existing is None:
                return None
            updated = existing.model_copy(update={"consumed_at": consumed_at})
            self._records_by_id[authorization_id] = updated
            return updated


class InMemoryTelegramTaskContextRepository:
    def __init__(self) -> None:
        self._records: dict[int, TelegramTaskContextRecord] = {}
        self._lock = RLock()

    def get_by_telegram_user_id(self, telegram_user_id: int) -> TelegramTaskContextRecord | None:
        with self._lock:
            return self._records.get(telegram_user_id)

    def upsert(
        self,
        *,
        telegram_user_id: int,
        task_id: str,
    ) -> TelegramTaskContextRecord:
        record = TelegramTaskContextRecord(
            telegram_user_id=telegram_user_id,
            task_id=task_id,
            updated_at=datetime.now(timezone.utc),
        )
        with self._lock:
            self._records[telegram_user_id] = record
        return record

    def delete(self, telegram_user_id: int) -> None:
        with self._lock:
            self._records.pop(telegram_user_id, None)
