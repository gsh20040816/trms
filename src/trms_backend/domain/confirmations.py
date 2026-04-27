from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, model_validator


class ConfirmationStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"


class ConfirmationSubmit(BaseModel):
    member_id: str = Field(min_length=1)
    status: ConfirmationStatus
    dispute_reason: str | None = None

    @model_validator(mode="after")
    def validate_reason(self) -> ConfirmationSubmit:
        self.member_id = self.member_id.strip()
        if self.dispute_reason is not None:
            self.dispute_reason = self.dispute_reason.strip() or None
        if self.status == ConfirmationStatus.DISPUTED and not self.dispute_reason:
            raise ValueError("dispute_reason is required for disputed confirmation")
        return self


class MemberConfirmationSubmit(ConfirmationSubmit):
    @model_validator(mode="after")
    def validate_member_status(self) -> MemberConfirmationSubmit:
        if self.status == ConfirmationStatus.PENDING:
            raise ValueError("member cannot submit pending confirmation status")
        return self


class ConfirmationDisputeResolve(BaseModel):
    administrator_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_administrator_id(self) -> ConfirmationDisputeResolve:
        self.administrator_id = self.administrator_id.strip()
        return self


class ConfirmationRecord(BaseModel):
    id: str
    split_id: str
    member_id: str
    status: ConfirmationStatus
    dispute_reason: str | None
    confirmed_at: datetime
    updated_at: datetime


class ConfirmationRepository(Protocol):
    def get_by_split(self, split_id: str) -> ConfirmationRecord | None:
        raise NotImplementedError

    def upsert_for_split(
        self,
        split_id: str,
        payload: ConfirmationSubmit,
    ) -> ConfirmationRecord:
        raise NotImplementedError

    def list_by_invoice(self, invoice_id: str) -> list[ConfirmationRecord]:
        raise NotImplementedError
