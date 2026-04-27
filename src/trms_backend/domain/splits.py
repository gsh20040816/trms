from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field, model_validator


class ExpenseSplitItem(BaseModel):
    member_id: str = Field(min_length=1)
    amount_cents: int = Field(gt=0)
    note: str | None = None

    @model_validator(mode="after")
    def normalize_text(self) -> ExpenseSplitItem:
        self.member_id = self.member_id.strip()
        if self.note is not None:
            self.note = self.note.strip() or None
        return self


class ExpenseSplitReplace(BaseModel):
    actor_id: str = Field(min_length=1)
    items: list[ExpenseSplitItem] = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_and_reject_duplicate_members(self) -> ExpenseSplitReplace:
        self.actor_id = self.actor_id.strip()
        member_ids = [item.member_id for item in self.items]
        if len(member_ids) != len(set(member_ids)):
            raise ValueError("split member_id must be unique")
        return self


class ExpenseSplitRecord(BaseModel):
    id: str
    invoice_id: str
    member_id: str
    amount_cents: int
    note: str | None
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ExpenseSplitRepository(Protocol):
    def replace_for_invoice(
        self,
        invoice_id: str,
        items: list[ExpenseSplitItem],
    ) -> list[ExpenseSplitRecord]:
        raise NotImplementedError

    def list_by_invoice(self, invoice_id: str) -> list[ExpenseSplitRecord]:
        raise NotImplementedError

    def get(self, split_id: str) -> ExpenseSplitRecord | None:
        raise NotImplementedError


class ExpenseSplitActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "only the invoice submitter, split member, or task administrator can submit splits"
        )


def ensure_split_actor_allowed(
    *,
    actor_id: str,
    submitter_id: str | None,
    administrator_id: str,
    existing_member_ids: set[str],
    target_member_ids: set[str],
) -> None:
    if actor_id == administrator_id:
        return
    if submitter_id is not None and actor_id == submitter_id:
        return
    if actor_id in existing_member_ids:
        return
    if actor_id in target_member_ids:
        return
    raise ExpenseSplitActorNotAllowedError()
