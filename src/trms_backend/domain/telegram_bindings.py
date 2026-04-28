from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from threading import RLock
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class TelegramSubmissionIdentityStatus(StrEnum):
    BOUND = "bound"
    PENDING_ASSIGNMENT = "pending_assignment"


class TelegramAccountBindingUpsert(BaseModel):
    telegram_user_id: int = Field(gt=0)
    member_id: str = Field(min_length=1)
    telegram_username: str | None = Field(default=None, max_length=64)

    @field_validator("member_id")
    @classmethod
    def normalize_member_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("member_id must not be empty")
        return normalized

    @field_validator("telegram_username")
    @classmethod
    def normalize_telegram_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lstrip("@").lower()
        return normalized or None


class TelegramAccountBindingRecord(BaseModel):
    id: str
    telegram_user_id: int
    member_id: str
    telegram_username: str | None
    created_at: datetime
    updated_at: datetime


class TelegramSubmissionIdentity(BaseModel):
    telegram_user_id: int
    status: TelegramSubmissionIdentityStatus
    member_id: str | None = None


class TelegramAccountBindingConflictError(ValueError):
    """Raised when a Telegram account binding would become ambiguous."""


class TelegramAccountBindingRepository(Protocol):
    def upsert(self, data: TelegramAccountBindingUpsert) -> TelegramAccountBindingRecord:
        raise NotImplementedError

    def get_by_telegram_user_id(self, telegram_user_id: int) -> TelegramAccountBindingRecord | None:
        raise NotImplementedError

    def get_by_member_id(self, member_id: str) -> TelegramAccountBindingRecord | None:
        raise NotImplementedError


class TelegramSubmissionIdentityResolver:
    def __init__(self, binding_repository: TelegramAccountBindingRepository) -> None:
        self._binding_repository = binding_repository

    def resolve(self, telegram_user_id: int) -> TelegramSubmissionIdentity:
        binding = self._binding_repository.get_by_telegram_user_id(telegram_user_id)
        if binding is None:
            return TelegramSubmissionIdentity(
                telegram_user_id=telegram_user_id,
                status=TelegramSubmissionIdentityStatus.PENDING_ASSIGNMENT,
                member_id=None,
            )
        return TelegramSubmissionIdentity(
            telegram_user_id=telegram_user_id,
            status=TelegramSubmissionIdentityStatus.BOUND,
            member_id=binding.member_id,
        )


class InMemoryTelegramAccountBindingRepository:
    def __init__(self) -> None:
        self._bindings_by_telegram_user_id: dict[int, TelegramAccountBindingRecord] = {}
        self._telegram_user_id_by_member_id: dict[str, int] = {}
        self._lock = RLock()

    def upsert(self, data: TelegramAccountBindingUpsert) -> TelegramAccountBindingRecord:
        with self._lock:
            existing_binding = self._bindings_by_telegram_user_id.get(data.telegram_user_id)
            if existing_binding is not None:
                if existing_binding.member_id != data.member_id:
                    raise TelegramAccountBindingConflictError(
                        "telegram user is already bound to another member: "
                        f"{data.telegram_user_id}"
                    )
                updated_binding = existing_binding.model_copy(
                    update={
                        "telegram_username": data.telegram_username,
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
                self._bindings_by_telegram_user_id[data.telegram_user_id] = updated_binding
                return updated_binding

            bound_telegram_user_id = self._telegram_user_id_by_member_id.get(data.member_id)
            if bound_telegram_user_id is not None:
                raise TelegramAccountBindingConflictError(
                    "member is already bound to another telegram user: "
                    f"{data.member_id}"
                )

            now = datetime.now(timezone.utc)
            binding = TelegramAccountBindingRecord(
                id=str(uuid4()),
                telegram_user_id=data.telegram_user_id,
                member_id=data.member_id,
                telegram_username=data.telegram_username,
                created_at=now,
                updated_at=now,
            )
            self._bindings_by_telegram_user_id[data.telegram_user_id] = binding
            self._telegram_user_id_by_member_id[data.member_id] = data.telegram_user_id
            return binding

    def get_by_telegram_user_id(self, telegram_user_id: int) -> TelegramAccountBindingRecord | None:
        with self._lock:
            return self._bindings_by_telegram_user_id.get(telegram_user_id)

    def get_by_member_id(self, member_id: str) -> TelegramAccountBindingRecord | None:
        normalized_member_id = member_id.strip()
        if not normalized_member_id:
            return None

        with self._lock:
            telegram_user_id = self._telegram_user_id_by_member_id.get(normalized_member_id)
            if telegram_user_id is None:
                return None
            return self._bindings_by_telegram_user_id.get(telegram_user_id)
