from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from trms_backend.domain.confirmations import ConfirmationRecord, ConfirmationStatus
from trms_backend.domain.expense_details import ExpenseDetailInvoiceSnapshot
from trms_backend.domain.invoices import InvoiceRecord
from trms_backend.domain.splits import ExpenseSplitRecord
from trms_backend.domain.tasks import (
    ReimbursementTask,
    ensure_task_administrator,
    has_task_submission_deadline_passed,
)


class OverdueConfirmationActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to view overdue confirmations for this task")


class OverdueConfirmationStatus(StrEnum):
    MISSING = "missing"
    PENDING = "pending"
    DISPUTED = "disputed"


class OverdueConfirmationItem(BaseModel):
    split_id: str
    split_version: int
    member_id: str
    amount_cents: int
    note: str | None
    status: OverdueConfirmationStatus
    last_confirmation_at: datetime | None
    updated_at: datetime
    invoice: ExpenseDetailInvoiceSnapshot


class OverdueConfirmationList(BaseModel):
    task_id: str
    administrator_id: str = Field(min_length=1)
    confirmation_deadline: datetime
    is_overdue: bool
    total_overdue_members: int
    overdue_member_ids: list[str]
    items: list[OverdueConfirmationItem]


def build_overdue_confirmation_list(
    task: ReimbursementTask,
    *,
    administrator_id: str,
    invoices: list[InvoiceRecord],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    confirmations_by_split_id: dict[str, ConfirmationRecord],
    now: datetime | None = None,
) -> OverdueConfirmationList:
    normalized_administrator_id = ensure_task_administrator(
        task,
        actor_id=administrator_id,
        error_type=OverdueConfirmationActorNotAllowedError,
    )

    is_overdue = has_task_submission_deadline_passed(task, now=now)
    if not is_overdue:
        return OverdueConfirmationList(
            task_id=task.id,
            administrator_id=normalized_administrator_id,
            confirmation_deadline=task.deadline,
            is_overdue=False,
            total_overdue_members=0,
            overdue_member_ids=[],
            items=[],
        )

    items: list[OverdueConfirmationItem] = []
    overdue_member_ids: list[str] = []
    for invoice in invoices:
        for split in splits_by_invoice_id.get(invoice.id, []):
            confirmation = confirmations_by_split_id.get(split.id)
            if confirmation is None:
                status = OverdueConfirmationStatus.MISSING
                last_confirmation_at = None
                updated_at = split.updated_at
            elif confirmation.status == ConfirmationStatus.CONFIRMED:
                continue
            elif confirmation.status == ConfirmationStatus.PENDING:
                status = OverdueConfirmationStatus.PENDING
                last_confirmation_at = confirmation.confirmed_at
                updated_at = confirmation.updated_at
            else:
                status = OverdueConfirmationStatus.DISPUTED
                last_confirmation_at = confirmation.confirmed_at
                updated_at = confirmation.updated_at

            overdue_member_ids.append(split.member_id)
            items.append(
                OverdueConfirmationItem(
                    split_id=split.id,
                    split_version=split.version,
                    member_id=split.member_id,
                    amount_cents=split.amount_cents,
                    note=split.note,
                    status=status,
                    last_confirmation_at=last_confirmation_at,
                    updated_at=updated_at,
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
                )
            )

    unique_member_ids = list(dict.fromkeys(overdue_member_ids))
    return OverdueConfirmationList(
        task_id=task.id,
        administrator_id=normalized_administrator_id,
        confirmation_deadline=task.deadline,
        is_overdue=True,
        total_overdue_members=len(unique_member_ids),
        overdue_member_ids=unique_member_ids,
        items=items,
    )
