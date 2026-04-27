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
    items: list[ExpenseSplitItem] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_members(self) -> ExpenseSplitReplace:
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
