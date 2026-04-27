from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from trms_backend.domain.confirmations import ConfirmationRecord, ConfirmationStatus
from trms_backend.domain.expense_details import ExpenseDetailInvoiceSnapshot
from trms_backend.domain.invoices import InvoiceRecord
from trms_backend.domain.splits import ExpenseSplitRecord
from trms_backend.domain.tasks import ReimbursementTask


class ExpenseDisputeActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to view or resolve expense disputes for this task")


class ExpenseDisputeNotFoundError(ValueError):
    def __init__(self, split_id: str) -> None:
        super().__init__(f"disputed confirmation not found for split: {split_id}")


class ExpenseDisputeItem(BaseModel):
    split_id: str
    member_id: str
    amount_cents: int
    note: str | None
    dispute_reason: str
    disputed_at: datetime
    updated_at: datetime
    invoice: ExpenseDetailInvoiceSnapshot


class ExpenseDisputeList(BaseModel):
    task_id: str
    administrator_id: str = Field(min_length=1)
    total_count: int
    items: list[ExpenseDisputeItem]


def ensure_task_administrator(task: ReimbursementTask, *, actor_id: str) -> str:
    normalized_actor_id = actor_id.strip()
    if normalized_actor_id != task.administrator_id:
        raise ExpenseDisputeActorNotAllowedError()
    return normalized_actor_id


def build_expense_dispute_list(
    task: ReimbursementTask,
    *,
    administrator_id: str,
    invoices: list[InvoiceRecord],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
    confirmations_by_split_id: dict[str, ConfirmationRecord],
) -> ExpenseDisputeList:
    normalized_administrator_id = ensure_task_administrator(task, actor_id=administrator_id)

    items: list[ExpenseDisputeItem] = []
    for invoice in invoices:
        for split in splits_by_invoice_id.get(invoice.id, []):
            confirmation = confirmations_by_split_id.get(split.id)
            if confirmation is None or confirmation.status is not ConfirmationStatus.DISPUTED:
                continue
            if confirmation.dispute_reason is None:
                raise ExpenseDisputeNotFoundError(split.id)

            items.append(
                ExpenseDisputeItem(
                    split_id=split.id,
                    member_id=split.member_id,
                    amount_cents=split.amount_cents,
                    note=split.note,
                    dispute_reason=confirmation.dispute_reason,
                    disputed_at=confirmation.confirmed_at,
                    updated_at=confirmation.updated_at,
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

    return ExpenseDisputeList(
        task_id=task.id,
        administrator_id=normalized_administrator_id,
        total_count=len(items),
        items=items,
    )
