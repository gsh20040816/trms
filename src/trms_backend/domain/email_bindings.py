from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, field_validator


def normalize_email_address(value: str, *, field_name: str = "email") -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if " " in normalized or "\t" in normalized or "\n" in normalized or "\r" in normalized:
        raise ValueError(f"{field_name} must not contain whitespace")
    local_part, separator, domain_part = normalized.partition("@")
    if separator != "@" or not local_part or not domain_part or "@" in domain_part:
        raise ValueError(f"{field_name} must be a valid email address")
    if "." not in domain_part:
        raise ValueError(f"{field_name} must be a valid email address")
    return normalized


class EmailSubmissionIdentityStatus(StrEnum):
    BOUND = "bound"
    PENDING_ASSIGNMENT = "pending_assignment"


class EmailAccountBindingUpsert(BaseModel):
    member_id: str = Field(min_length=1)
    email: str = Field(min_length=3, max_length=320)

    @field_validator("member_id")
    @classmethod
    def normalize_member_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("member_id must not be empty")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email_address(value)


class EmailAccountBindingRecord(BaseModel):
    id: str
    member_id: str
    email: str
    created_at: datetime
    updated_at: datetime


class EmailBindingVerificationCreate(BaseModel):
    member_id: str = Field(min_length=1)
    email: str = Field(min_length=3, max_length=320)
    code_hash: str = Field(min_length=64, max_length=64)
    expires_at: datetime

    @field_validator("member_id")
    @classmethod
    def normalize_member_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("member_id must not be empty")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email_address(value)


class EmailBindingVerificationRecord(BaseModel):
    id: str
    member_id: str
    email: str
    code_hash: str
    expires_at: datetime
    consumed_at: datetime | None
    created_at: datetime


class EmailSubmissionIdentity(BaseModel):
    email: str
    status: EmailSubmissionIdentityStatus
    member_id: str | None = None


class EmailAccountBindingConflictError(ValueError):
    """Raised when an email binding would become ambiguous."""


class EmailAccountBindingRepository(Protocol):
    def upsert(self, data: EmailAccountBindingUpsert) -> EmailAccountBindingRecord:
        raise NotImplementedError

    def get_by_email(self, email: str) -> EmailAccountBindingRecord | None:
        raise NotImplementedError

    def list_by_member_id(self, member_id: str) -> list[EmailAccountBindingRecord]:
        raise NotImplementedError


class EmailBindingVerificationRepository(Protocol):
    def replace_pending(
        self,
        data: EmailBindingVerificationCreate,
    ) -> EmailBindingVerificationRecord:
        raise NotImplementedError

    def get_latest_pending(
        self,
        *,
        member_id: str,
        email: str,
    ) -> EmailBindingVerificationRecord | None:
        raise NotImplementedError

    def mark_consumed(
        self,
        verification_id: str,
        *,
        consumed_at: datetime,
    ) -> EmailBindingVerificationRecord | None:
        raise NotImplementedError


class EmailSubmissionIdentityResolver:
    def __init__(self, binding_repository: EmailAccountBindingRepository) -> None:
        self._binding_repository = binding_repository

    def resolve(self, sender_email: str) -> EmailSubmissionIdentity:
        normalized_email = normalize_email_address(sender_email, field_name="sender_email")
        binding = self._binding_repository.get_by_email(normalized_email)
        if binding is None:
            return EmailSubmissionIdentity(
                email=normalized_email,
                status=EmailSubmissionIdentityStatus.PENDING_ASSIGNMENT,
                member_id=None,
            )
        return EmailSubmissionIdentity(
            email=normalized_email,
            status=EmailSubmissionIdentityStatus.BOUND,
            member_id=binding.member_id,
        )
