from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from trms_backend.domain.invoices import ExpenseType, InvoiceRecord
from trms_backend.domain.materials import MaterialRecord, MaterialStatus, MaterialType
from trms_backend.domain.tasks import ReimbursementTask


class PendingSupportingMaterialLinkageReason(StrEnum):
    NO_CANDIDATE = "no_candidate"
    MULTIPLE_CANDIDATES = "multiple_candidates"


class PendingSupportingMaterialLinkageCandidateInvoiceSummary(BaseModel):
    invoice_id: str
    invoice_number: str
    amount_cents: int = Field(ge=0)
    expense_type: ExpenseType


class PendingSupportingMaterialLinkageItem(BaseModel):
    material_id: str
    submitter_id: str
    material_type: MaterialType
    original_filename: str
    pending_reason: PendingSupportingMaterialLinkageReason
    candidate_invoices: list[PendingSupportingMaterialLinkageCandidateInvoiceSummary] = Field(
        default_factory=list
    )
    created_at: datetime


class TaskSupportingMaterialLinkageReport(BaseModel):
    task_id: str
    actor_id: str
    items: list[PendingSupportingMaterialLinkageItem] = Field(default_factory=list)


def build_task_supporting_material_linkage_report(
    task: ReimbursementTask,
    *,
    actor_id: str,
    include_all_members: bool,
    materials: list[MaterialRecord],
    invoices: list[InvoiceRecord],
    materials_by_id: dict[str, MaterialRecord],
    linked_invoice_ids_by_material_id: dict[str, list[str]],
) -> TaskSupportingMaterialLinkageReport:
    normalized_actor_id = actor_id.strip()

    items: list[PendingSupportingMaterialLinkageItem] = []
    for material in sorted(materials, key=lambda item: (item.created_at, item.id)):
        if material.task_id != task.id:
            continue
        if material.status is not MaterialStatus.ASSIGNED:
            continue
        if material.material_type is MaterialType.INVOICE:
            continue
        if material.submitter_id is None:
            continue
        if not include_all_members and material.submitter_id != normalized_actor_id:
            continue
        if linked_invoice_ids_by_material_id.get(material.id):
            continue

        candidate_invoices = [
            invoice
            for invoice in invoices
            if _invoice_belongs_to_submitter(
                invoice=invoice,
                submitter_id=material.submitter_id,
                materials_by_id=materials_by_id,
            )
        ]
        if len(candidate_invoices) == 1:
            continue

        pending_reason = (
            PendingSupportingMaterialLinkageReason.NO_CANDIDATE
            if len(candidate_invoices) == 0
            else PendingSupportingMaterialLinkageReason.MULTIPLE_CANDIDATES
        )
        items.append(
            PendingSupportingMaterialLinkageItem(
                material_id=material.id,
                submitter_id=material.submitter_id,
                material_type=material.material_type,
                original_filename=material.original_filename,
                pending_reason=pending_reason,
                candidate_invoices=[
                    PendingSupportingMaterialLinkageCandidateInvoiceSummary(
                        invoice_id=invoice.id,
                        invoice_number=invoice.invoice_number,
                        amount_cents=invoice.amount_cents,
                        expense_type=invoice.expense_type,
                    )
                    for invoice in candidate_invoices
                ],
                created_at=material.created_at,
            )
        )

    return TaskSupportingMaterialLinkageReport(
        task_id=task.id,
        actor_id=normalized_actor_id,
        items=items,
    )


def _invoice_belongs_to_submitter(
    *,
    invoice: InvoiceRecord,
    submitter_id: str,
    materials_by_id: dict[str, MaterialRecord],
) -> bool:
    invoice_material = materials_by_id.get(invoice.material_id)
    if invoice_material is None:
        return False
    return invoice_material.submitter_id == submitter_id
