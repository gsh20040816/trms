from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from trms_backend.domain.invoices import ExpenseType, InvoiceRecord
from trms_backend.domain.materials import MaterialRecord, MaterialType
from trms_backend.domain.splits import ExpenseSplitRecord
from trms_backend.domain.tasks import ReimbursementTask


class TaskSharedInvoiceActorNotAllowedError(ValueError):
    def __init__(self) -> None:
        super().__init__("actor is not allowed to view shared invoices for this task")


class SharedInvoiceSplitSummary(BaseModel):
    member_id: str
    amount_cents: int = Field(ge=0)


class SharedInvoiceSupportingMaterialSummary(BaseModel):
    material_type: MaterialType
    count: int = Field(ge=1)


class TaskSharedInvoiceItem(BaseModel):
    invoice_id: str
    invoice_number: str
    issue_date: date | None
    buyer_name: str
    seller_name: str | None
    amount_cents: int = Field(ge=0)
    expense_type: ExpenseType
    submitter_id: str | None
    supporting_materials: list[SharedInvoiceSupportingMaterialSummary] = Field(default_factory=list)
    splits: list[SharedInvoiceSplitSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TaskSharedInvoiceReport(BaseModel):
    task_id: str
    actor_id: str
    items: list[TaskSharedInvoiceItem] = Field(default_factory=list)


def build_task_shared_invoice_report(
    task: ReimbursementTask,
    *,
    actor_id: str,
    invoices: list[InvoiceRecord],
    materials_by_id: dict[str, MaterialRecord],
    supporting_materials_by_invoice_id: dict[str, list[MaterialRecord]],
    splits_by_invoice_id: dict[str, list[ExpenseSplitRecord]],
) -> TaskSharedInvoiceReport:
    normalized_actor_id = actor_id.strip()
    if normalized_actor_id != task.administrator_id and normalized_actor_id not in task.member_ids:
        raise TaskSharedInvoiceActorNotAllowedError()

    items: list[TaskSharedInvoiceItem] = []
    for invoice in sorted(invoices, key=lambda item: (item.created_at, item.id)):
        if invoice.task_id != task.id:
            continue

        submitter_id = None
        invoice_material = materials_by_id.get(invoice.material_id)
        if invoice_material is not None:
            submitter_id = invoice_material.submitter_id

        supporting_material_counts: dict[MaterialType, int] = {}
        for material in supporting_materials_by_invoice_id.get(invoice.id, []):
            supporting_material_counts[material.material_type] = (
                supporting_material_counts.get(material.material_type, 0) + 1
            )

        items.append(
            TaskSharedInvoiceItem(
                invoice_id=invoice.id,
                invoice_number=invoice.invoice_number,
                issue_date=invoice.issue_date,
                buyer_name=invoice.buyer_name,
                seller_name=invoice.seller_name,
                amount_cents=invoice.amount_cents,
                expense_type=invoice.expense_type,
                submitter_id=submitter_id,
                supporting_materials=[
                    SharedInvoiceSupportingMaterialSummary(
                        material_type=material_type,
                        count=count,
                    )
                    for material_type, count in sorted(
                        supporting_material_counts.items(),
                        key=lambda item: item[0].value,
                    )
                ],
                splits=[
                    SharedInvoiceSplitSummary(
                        member_id=split.member_id,
                        amount_cents=split.amount_cents,
                    )
                    for split in sorted(
                        splits_by_invoice_id.get(invoice.id, []),
                        key=lambda item: (item.member_id, item.created_at, item.id),
                    )
                ],
                created_at=invoice.created_at,
                updated_at=invoice.updated_at,
            )
        )

    return TaskSharedInvoiceReport(
        task_id=task.id,
        actor_id=normalized_actor_id,
        items=items,
    )
