from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from trms_backend.domain.confirmations import ConfirmationRecord, ConfirmationStatus
from trms_backend.domain.invoices import ExpenseType, InvoiceRecord
from trms_backend.domain.splits import ExpenseSplitRecord
from trms_backend.domain.tasks import ReimbursementTask


class ExpenseDetailScope(StrEnum):
    MEMBER = "member"
    TASK = "task"


class ExpenseDetailActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to view expense details for this task")


class ExpenseDetailInvoiceSnapshot(BaseModel):
    id: str
    material_id: str
    invoice_number: str
    issue_date: date | None
    transaction_time: datetime | None
    buyer_name: str
    seller_name: str | None
    amount_cents: int
    expense_type: ExpenseType
    created_at: datetime
    updated_at: datetime


class ExpenseDetailConfirmationSnapshot(BaseModel):
    id: str
    member_id: str
    status: ConfirmationStatus
    dispute_reason: str | None
    confirmed_at: datetime
    updated_at: datetime


class ExpenseDetailItem(BaseModel):
    split_id: str
    member_id: str
    amount_cents: int
    note: str | None
    created_at: datetime
    updated_at: datetime
    invoice: ExpenseDetailInvoiceSnapshot
    confirmation: ExpenseDetailConfirmationSnapshot | None


class ExpenseDetailList(BaseModel):
    actor_id: str = Field(min_length=1)
    scope: ExpenseDetailScope
    total_amount_cents: int
    items: list[ExpenseDetailItem]


def resolve_expense_detail_scope(
    task: ReimbursementTask,
    *,
    actor_id: str,
) -> ExpenseDetailScope:
    normalized_actor_id = actor_id.strip()
    if normalized_actor_id == task.administrator_id:
        return ExpenseDetailScope.TASK
    if normalized_actor_id in task.member_ids:
        return ExpenseDetailScope.MEMBER
    raise ExpenseDetailActorNotAllowedError()


def build_expense_detail_list(
    task: ReimbursementTask,
    *,
    actor_id: str,
    invoices: list[InvoiceRecord],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    confirmations_by_split_id: dict[str, ConfirmationRecord],
) -> ExpenseDetailList:
    normalized_actor_id = actor_id.strip()
    scope = resolve_expense_detail_scope(task, actor_id=normalized_actor_id)

    items: list[ExpenseDetailItem] = []
    for invoice in invoices:
        for split in splits_by_invoice_id.get(invoice.id, []):
            if scope is ExpenseDetailScope.MEMBER and split.member_id != normalized_actor_id:
                continue

            confirmation = confirmations_by_split_id.get(split.id)
            items.append(
                ExpenseDetailItem(
                    split_id=split.id,
                    member_id=split.member_id,
                    amount_cents=split.amount_cents,
                    note=split.note,
                    created_at=split.created_at,
                    updated_at=split.updated_at,
                    invoice=ExpenseDetailInvoiceSnapshot(
                        id=invoice.id,
                        material_id=invoice.material_id,
                        invoice_number=invoice.invoice_number,
                        issue_date=invoice.issue_date,
                        transaction_time=invoice.transaction_time,
                        buyer_name=invoice.buyer_name,
                        seller_name=invoice.seller_name,
                        amount_cents=invoice.amount_cents,
                        expense_type=invoice.expense_type,
                        created_at=invoice.created_at,
                        updated_at=invoice.updated_at,
                    ),
                    confirmation=(
                        ExpenseDetailConfirmationSnapshot(
                            id=confirmation.id,
                            member_id=confirmation.member_id,
                            status=confirmation.status,
                            dispute_reason=confirmation.dispute_reason,
                            confirmed_at=confirmation.confirmed_at,
                            updated_at=confirmation.updated_at,
                        )
                        if confirmation is not None
                        else None
                    ),
                )
            )

    return ExpenseDetailList(
        actor_id=normalized_actor_id,
        scope=scope,
        total_amount_cents=sum(item.amount_cents for item in items),
        items=items,
    )
